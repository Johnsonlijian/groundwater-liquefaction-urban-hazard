"""R21 GHSL polygon and GSFC mascon robustness analysis.

This script closes the data-driven items that can be completed with public,
locally downloaded products:

- GHSL R2024A urban-centre polygons replace the point-only exposure diagnostic.
- NASA GSFC RL06v2.0 mascons provide an independent GRACE/GRACE-FO TWS trend.
- CSR-vs-GSFC sign agreement is evaluated for all cities and material hotspots.
- JPL CRI-filtered PO.DAAC access is recorded honestly as Earthdata-protected
  unless a local authenticated download is present.

Outputs are written to data_derived/ and figures/.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyogrio
import xarray as xr
from scipy.spatial import cKDTree
from scipy.stats import linregress, theilslopes

from zhu2017 import p_liquefaction


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
RAW = ROOT / "data_raw"
FIG = ROOT / "figures"
MATERIAL = 0.01
Q_FDR = 0.10
NYEARS_RECENT = 10
SY_DEFAULT = 0.10
R_EARTH_KM = 6371.0088

GHSL_GPKG = RAW / "ghsl" / "GLOBE_R2024A" / "GHS_UCDB_GLOBE_R2024A.gpkg"
GSFC_NC = RAW / "grace" / "gsfc" / "gsfc.glb_200204_202511_rl06v2.0_obp-ice6gd_halfdegree.nc"
JPL_LOCAL_CANDIDATES = [
    RAW / "grace" / "jpl" / "TELLUS_GRAC-GRFO_MASCON_GRID_RL06.3_V4.nc",
    RAW / "grace" / "jpl" / "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4.nc",
]


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


def lonlat_xyz(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    lonr = np.deg2rad(lon)
    latr = np.deg2rad(lat)
    return np.column_stack((np.cos(latr) * np.cos(lonr), np.cos(latr) * np.sin(lonr), np.sin(latr)))


def haversine_km(lon1: np.ndarray, lat1: np.ndarray, lon2: np.ndarray, lat2: np.ndarray) -> np.ndarray:
    lon1r, lat1r, lon2r, lat2r = map(np.deg2rad, [lon1, lat1, lon2, lat2])
    dlon = lon2r - lon1r
    dlat = lat2r - lat1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def bh_fdr(p: np.ndarray, q: float = Q_FDR) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    passed = p[order] <= q * (np.arange(1, n + 1)) / n
    k = np.where(passed)[0].max() + 1 if passed.any() else 0
    out = np.zeros(n, bool)
    out[order[:k]] = True
    return out


def load_city_data() -> pd.DataFrame:
    results = pd.read_csv(DER / "city_results_v2.csv")
    inputs = pd.read_csv(DER / "city_inputs.csv")
    keep = ["name", "country", "lat", "lon", "pga_475_g", "vs30", "precip", "dw_km"]
    out = results.merge(inputs[keep], on=["name", "country", "lat", "lon"], how="left")
    out.insert(0, "city_row_id", np.arange(len(out), dtype=int))
    out["is_material_hotspot"] = out["fdr_sig"] & (out["dP"].abs() >= MATERIAL)
    return out


def load_ghsl_polygons() -> gpd.GeoDataFrame:
    if not GHSL_GPKG.exists():
        raise FileNotFoundError(f"Missing GHSL package: {GHSL_GPKG}")
    # The GHSL GPKG stores field names with a UTF-8 BOM prefix and uses
    # Mollweide metres. Use pyogrio field pruning to avoid reading the full
    # 200+ column theme table.
    raw_cols = [
        "\ufeffID_UC_G0",
        "\ufeffGC_UCN_MAI_2025",
        "\ufeffGC_CNT_GAD_2025",
        "\ufeffGC_UCA_KM2_2025",
        "\ufeffGC_POP_TOT_2025",
    ]
    g = pyogrio.read_dataframe(
        GHSL_GPKG,
        layer="GHS_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A",
        columns=raw_cols,
    )
    g = clean_columns(g)
    cols = [
        "ID_UC_G0",
        "GC_UCN_MAI_2025",
        "GC_CNT_GAD_2025",
        "GC_UCA_KM2_2025",
        "GC_POP_TOT_2025",
        "geometry",
    ]
    g = g[cols].rename(
        columns={
            "ID_UC_G0": "ghsl_uc_id",
            "GC_UCN_MAI_2025": "ghsl_uc_name",
            "GC_CNT_GAD_2025": "ghsl_country_name",
            "GC_UCA_KM2_2025": "ghsl_area_km2",
            "GC_POP_TOT_2025": "ghsl_pop_2025",
        }
    )
    for col in ["ghsl_uc_name", "ghsl_country_name"]:
        g[col] = g[col].astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    return g.to_crs("EPSG:4326")


def build_ghsl_matches(cities: pd.DataFrame, ghsl: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    city_g = gpd.GeoDataFrame(
        cities.copy(),
        geometry=gpd.points_from_xy(cities["lon"], cities["lat"]),
        crs="EPSG:4326",
    )

    joined = gpd.sjoin(
        city_g,
        ghsl[["ghsl_uc_id", "ghsl_uc_name", "ghsl_country_name", "ghsl_area_km2", "ghsl_pop_2025", "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"], errors="ignore")
    joined["ghsl_match_method"] = np.where(joined["ghsl_uc_id"].notna(), "within_polygon", "unmatched")
    joined["distance_to_ghsl_centroid_km"] = np.where(joined["ghsl_uc_id"].notna(), 0.0, np.nan)

    unmatched_mask = joined["ghsl_uc_id"].isna()
    if unmatched_mask.any():
        reps = ghsl.geometry.representative_point()
        tree = cKDTree(lonlat_xyz(reps.x.to_numpy(float), reps.y.to_numpy(float)))
        unmatched = joined.loc[unmatched_mask]
        chord, idx = tree.query(lonlat_xyz(unmatched["lon"].to_numpy(float), unmatched["lat"].to_numpy(float)), k=1)
        nearest = ghsl.iloc[idx].reset_index(drop=True)
        dist = 2 * np.arcsin(np.clip(chord / 2, 0, 1)) * R_EARTH_KM
        use = dist <= 50.0
        target_idx = unmatched.index.to_numpy()
        fill_cols = ["ghsl_uc_id", "ghsl_uc_name", "ghsl_country_name", "ghsl_area_km2", "ghsl_pop_2025"]
        for col in fill_cols:
            joined.loc[target_idx[use], col] = nearest.loc[use, col].to_numpy()
        joined.loc[target_idx[use], "ghsl_match_method"] = "nearest_representative_point_le50km"
        joined.loc[target_idx[use], "distance_to_ghsl_centroid_km"] = dist[use]
        joined.loc[target_idx[~use], "distance_to_ghsl_centroid_km"] = dist[~use]

    matches = pd.DataFrame(joined.drop(columns="geometry"))
    matches["ghsl_matched"] = matches["ghsl_uc_id"].notna()
    matches["ghsl_uc_id"] = matches["ghsl_uc_id"].where(matches["ghsl_uc_id"].isna(), matches["ghsl_uc_id"].astype("Int64"))

    matched = matches[matches["ghsl_matched"]].copy()
    rows = []
    for gid, group in matched.groupby("ghsl_uc_id", dropna=True):
        w = group["population"].astype(float)
        hotspots = group[group["is_material_hotspot"]]
        rows.append(
            {
                "ghsl_uc_id": int(gid),
                "ghsl_uc_name": group["ghsl_uc_name"].iloc[0],
                "ghsl_country_name": group["ghsl_country_name"].iloc[0],
                "ghsl_area_km2": float(group["ghsl_area_km2"].iloc[0]),
                "ghsl_pop_2025": float(group["ghsl_pop_2025"].iloc[0]),
                "n_geonames_points": int(len(group)),
                "matched_city_names": "; ".join(group.sort_values("population", ascending=False)["name"].astype(str)),
                "geonames_population_sum": int(group["population"].sum()),
                "population_weighted_dP": float(np.average(group["dP"], weights=w)),
                "max_abs_dP": float(group["dP"].abs().max()),
                "median_dP": float(group["dP"].median()),
                "n_material_point_hotspots": int(len(hotspots)),
                "material_point_names": "; ".join(hotspots["name"].astype(str)),
            }
        )
    aggregate = pd.DataFrame(rows).sort_values(["n_material_point_hotspots", "max_abs_dP"], ascending=[False, False])

    hotspot = matches[matches["is_material_hotspot"]].copy()
    hotspot = hotspot.merge(
        aggregate[
            [
                "ghsl_uc_id",
                "n_geonames_points",
                "matched_city_names",
                "population_weighted_dP",
                "n_material_point_hotspots",
            ]
        ],
        on="ghsl_uc_id",
        how="left",
        suffixes=("", "_ghsl_uc"),
    )
    return matches, aggregate, hotspot


def trend_stats(y: np.ndarray, dates: np.ndarray, start_year: int, end_year: int = 2024) -> dict[str, float]:
    years = np.array([d.year + (d.dayofyear - 0.5) / (366 if d.is_leap_year else 365) for d in pd.to_datetime(dates)])
    mask = (years >= start_year) & (years <= end_year + 1) & np.isfinite(y)
    if mask.sum() < 6:
        return {"ols_cm_yr": np.nan, "ols_p": np.nan, "ols_se_cm_yr": np.nan, "theilsen_cm_yr": np.nan, "n_months": int(mask.sum())}
    lr = linregress(years[mask], y[mask])
    ts = theilslopes(y[mask], years[mask])
    return {
        "ols_cm_yr": float(lr.slope),
        "ols_p": float(lr.pvalue),
        "ols_se_cm_yr": float(lr.stderr),
        "theilsen_cm_yr": float(ts.slope),
        "n_months": int(mask.sum()),
    }


def compute_delta_p(cities: pd.DataFrame, trend_cm_yr: np.ndarray) -> np.ndarray:
    pgv = cities["pga_475_g"].to_numpy(float) * 100.0
    base = p_liquefaction(
        pgv,
        cities["vs30"].to_numpy(float),
        cities["precip"].to_numpy(float),
        cities["dw_km"].to_numpy(float),
        cities["wtd"].to_numpy(float),
    )
    dwtd = -(trend_cm_yr * NYEARS_RECENT / 100.0) / SY_DEFAULT
    new_wtd = np.maximum(cities["wtd"].to_numpy(float) + dwtd, 0.0)
    new = p_liquefaction(
        pgv,
        cities["vs30"].to_numpy(float),
        cities["precip"].to_numpy(float),
        cities["dw_km"].to_numpy(float),
        new_wtd,
    )
    return new - base


def sample_gsfc(cities: pd.DataFrame) -> pd.DataFrame:
    if not GSFC_NC.exists():
        raise FileNotFoundError(f"Missing GSFC package: {GSFC_NC}")
    ds = xr.open_dataset(GSFC_NC)
    lon = cities["lon"].to_numpy(float) % 360.0
    lat = cities["lat"].to_numpy(float)
    lats = np.asarray(ds["lat"].values, float)
    lons = np.asarray(ds["lon"].values, float)
    lat_idx = np.abs(lats[:, None] - lat[None, :]).argmin(axis=0)
    lon_idx = np.abs(lons[:, None] - lon[None, :]).argmin(axis=0)
    vals = np.asarray(ds["lwe_thickness"].values[:, lat_idx, lon_idx], float)
    dates = pd.to_datetime(ds["time"].values)
    rows = []
    for i, row in cities.reset_index(drop=True).iterrows():
        recent = trend_stats(vals[:, i], dates, 2015, 2024)
        full = trend_stats(vals[:, i], dates, 2003, 2024)
        rows.append(
            {
                "name": row["name"],
                "country": row["country"],
                "city_row_id": int(row["city_row_id"]),
                "lat": row["lat"],
                "lon": row["lon"],
                "csr_recent_tws_cm_yr": row["tws_cm_yr"],
                "gsfc_recent_tws_cm_yr": recent["ols_cm_yr"],
                "gsfc_recent_p": recent["ols_p"],
                "gsfc_recent_se_cm_yr": recent["ols_se_cm_yr"],
                "gsfc_recent_theilsen_cm_yr": recent["theilsen_cm_yr"],
                "gsfc_recent_n_months": recent["n_months"],
                "gsfc_full_tws_cm_yr": full["ols_cm_yr"],
                "gsfc_full_p": full["ols_p"],
                "gsfc_full_theilsen_cm_yr": full["theilsen_cm_yr"],
                "gsfc_full_n_months": full["n_months"],
            }
        )
    out = pd.DataFrame(rows)
    out["gsfc_recent_dP"] = compute_delta_p(cities.reset_index(drop=True), out["gsfc_recent_tws_cm_yr"].to_numpy(float))
    out["csr_sign"] = np.sign(out["csr_recent_tws_cm_yr"]).astype(int)
    out["gsfc_recent_sign"] = np.sign(out["gsfc_recent_tws_cm_yr"]).astype(int)
    out["gsfc_theilsen_sign"] = np.sign(out["gsfc_recent_theilsen_cm_yr"]).astype(int)
    out["csr_gsfc_recent_sign_match"] = out["csr_sign"] == out["gsfc_recent_sign"]
    out["csr_gsfc_theilsen_sign_match"] = out["csr_sign"] == out["gsfc_theilsen_sign"]
    return out


def build_multi_product(cities: pd.DataFrame, gsfc: pd.DataFrame, ghsl_matches: pd.DataFrame) -> pd.DataFrame:
    material = cities[["city_row_id", "name", "country", "is_material_hotspot", "dP", "fdr_sig"]].copy()
    out = material.merge(gsfc, on=["city_row_id", "name", "country"], how="left")
    out = out.merge(
        ghsl_matches[
            [
                "city_row_id",
                "name",
                "country",
                "ghsl_matched",
                "ghsl_match_method",
                "ghsl_uc_id",
                "ghsl_uc_name",
                "distance_to_ghsl_centroid_km",
            ]
        ],
        on=["city_row_id", "name", "country"],
        how="left",
    )
    out["hotspot_product_grade"] = np.select(
        [
            out["is_material_hotspot"] & out["csr_gsfc_recent_sign_match"] & out["csr_gsfc_theilsen_sign_match"] & out["ghsl_matched"],
            out["is_material_hotspot"] & out["csr_gsfc_recent_sign_match"] & out["ghsl_matched"],
            out["is_material_hotspot"],
        ],
        ["csr-gsfc-ghsl-robust", "csr-gsfc-ols-ghsl-probable", "hotspot-needs-followup"],
        default="not-material-hotspot",
    )
    return out


def external_status() -> pd.DataFrame:
    netrc = Path.home() / ".netrc"
    local_jpl = [p for p in JPL_LOCAL_CANDIDATES if p.exists()]
    return pd.DataFrame(
        [
            {
                "product_or_dataset": "GHSL Urban Centre Database R2024A",
                "status_in_this_project": "ingested and used",
                "official_source": "https://human-settlement.emergency.copernicus.eu/ghs_ucdb_2024.php",
                "local_action": "downloaded V1.1 GLOBE and MTUC packages; used GLOBE urban-centre polygons",
            },
            {
                "product_or_dataset": "NASA GSFC GRACE/GRACE-FO RL06v2.0 mascon",
                "status_in_this_project": "ingested and used",
                "official_source": "https://earth.gsfc.nasa.gov/geo/data/grace-mascons",
                "local_action": "downloaded OBP/ICE6G-D half-degree NetCDF and sampled city trends",
            },
            {
                "product_or_dataset": "JPL GRACE/GRACE-FO Mascon RL06.3Mv04 CRI-filtered",
                "status_in_this_project": "auth-blocked unless local Earthdata credentials are provided" if not local_jpl else "ingested and used",
                "official_source": "https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_GRID_RL06.3_V4",
                "local_action": (
                    "CMR collection verified; no local .netrc/Earthdata credential and protected virtual HTTPS returned 403"
                    if not local_jpl
                    else f"local file present: {local_jpl[0]}"
                ),
            },
        ]
    )


def make_fig7(hotspot: pd.DataFrame, multiproduct: pd.DataFrame, gsfc: pd.DataFrame, summary: dict[str, object]) -> None:
    RED = "#c7362f"
    BLUE = "#2f6fb3"
    INK = "#202020"
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.3), dpi=220, gridspec_kw={"width_ratios": [1.35, 1.45, 1.35]})
    fig.suptitle("GHSL polygon and GSFC mascon robustness", fontsize=12, weight="bold")

    hs = hotspot.sort_values("dP")
    y = np.arange(len(hs))
    colors = np.where(hs["dP"] > 0, RED, BLUE)
    labels = hs["name"] + " (" + hs["ghsl_uc_name"].fillna("unmatched") + ")"
    axes[0].barh(y, hs["dP"], color=colors, alpha=0.82)
    axes[0].set_yticks(y, labels, fontsize=7)
    axes[0].axvline(0, color=INK, lw=0.8)
    axes[0].set_xlabel("Cumulative Delta P_liq")
    axes[0].set_title("a GHSL urban-centre match", loc="left", weight="bold")

    hsm = multiproduct[multiproduct["is_material_hotspot"]].copy()
    axes[1].axhline(0, color="#999999", lw=0.8)
    axes[1].axvline(0, color="#999999", lw=0.8)
    axes[1].scatter(gsfc["csr_recent_tws_cm_yr"], gsfc["gsfc_recent_tws_cm_yr"], s=11, color="#c7c7c7", alpha=0.65)
    axes[1].scatter(
        hsm["csr_recent_tws_cm_yr"],
        hsm["gsfc_recent_tws_cm_yr"],
        s=48,
        c=np.where(hsm["dP"] > 0, RED, BLUE),
        edgecolor=INK,
        lw=0.4,
        zorder=5,
    )
    offsets = {
        "Yokohama": (0.10, 0.16),
        "Bhayandar": (0.10, -0.10),
        "Mumbai": (0.10, -0.34),
        "Delhi": (0.10, -0.16),
        "Lahore": (0.10, -0.16),
        "Ludhiana": (0.10, -0.16),
    }
    for _, r in hsm.iterrows():
        dx, dy = offsets.get(r["name"], (0.10, 0.10))
        axes[1].text(r["csr_recent_tws_cm_yr"] + dx, r["gsfc_recent_tws_cm_yr"] + dy, r["name"], fontsize=5.8, va="center")
    axes[1].set_xlabel("CSR recent TWS trend (cm yr$^{-1}$)")
    axes[1].set_ylabel("GSFC recent TWS trend (cm yr$^{-1}$)")
    axes[1].set_title("b Independent mascon sign check", loc="left", weight="bold")

    axes[2].axis("off")
    lines = [
        ("GHSL polygon matches", f"{summary['n_ghsl_matched_cities']}/{summary['n_cities']} cities"),
        ("Material point hotspots", f"{summary['n_material_point_hotspots']}"),
        ("GHSL material UCs", f"{summary['n_material_ghsl_urban_centres']}"),
        ("CSR-GSFC hotspot sign", f"{summary['n_material_hotspots_csr_gsfc_recent_sign_match']}/{summary['n_material_point_hotspots']} match"),
        ("Full robust grade", f"{summary['n_material_hotspots_csr_gsfc_ghsl_robust']}/{summary['n_material_point_hotspots']}"),
        ("JPL CRI status", "auth blocked"),
    ]
    y0 = 0.88
    axes[2].text(0.02, 0.98, "c Data-status ledger", transform=axes[2].transAxes, fontsize=9, weight="bold", va="top")
    for idx, (k, v) in enumerate(lines):
        axes[2].text(0.03, y0 - idx * 0.13, k, transform=axes[2].transAxes, fontsize=7.5, color="#555555")
        axes[2].text(0.97, y0 - idx * 0.13, v, transform=axes[2].transAxes, fontsize=7.5, ha="right", color=INK)
    axes[2].text(
        0.03,
        0.04,
        "JPL is not treated as failed science; it is a credential boundary.\n"
        "No multi-mascon claim includes JPL unless Earthdata-authenticated data are ingested.",
        transform=axes[2].transAxes,
        fontsize=6.5,
        color="#666666",
    )

    for ax in axes[:2]:
        ax.grid(True, color="#e2e2e2", lw=0.5)
        ax.set_axisbelow(True)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    for ext in ["png", "svg", "pdf"]:
        fig.savefig(FIG / f"Fig7_ghsl_gsfc_robustness.{ext}", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    cities = load_city_data()
    ghsl = load_ghsl_polygons()
    ghsl_matches, ghsl_aggregate, ghsl_hotspot = build_ghsl_matches(cities, ghsl)
    gsfc = sample_gsfc(cities)
    multiproduct = build_multi_product(cities, gsfc, ghsl_matches)
    status = external_status()

    material_multi = multiproduct[multiproduct["is_material_hotspot"]]
    material_ghsl_ids = ghsl_hotspot["ghsl_uc_id"].dropna().astype(int).nunique()
    jpl_status = status.loc[status["product_or_dataset"].str.startswith("JPL"), "status_in_this_project"].iloc[0]
    summary = {
        "n_cities": int(len(cities)),
        "n_ghsl_matched_cities": int(ghsl_matches["ghsl_matched"].sum()),
        "n_ghsl_within_polygon": int((ghsl_matches["ghsl_match_method"] == "within_polygon").sum()),
        "n_ghsl_nearest_le50km": int((ghsl_matches["ghsl_match_method"] == "nearest_representative_point_le50km").sum()),
        "n_material_point_hotspots": int(cities["is_material_hotspot"].sum()),
        "n_material_ghsl_urban_centres": int(material_ghsl_ids),
        "n_material_hotspots_csr_gsfc_recent_sign_match": int(material_multi["csr_gsfc_recent_sign_match"].sum()),
        "n_material_hotspots_csr_gsfc_theilsen_sign_match": int(material_multi["csr_gsfc_theilsen_sign_match"].sum()),
        "n_material_hotspots_csr_gsfc_ghsl_robust": int((material_multi["hotspot_product_grade"] == "csr-gsfc-ghsl-robust").sum()),
        "all_city_csr_gsfc_recent_sign_agreement_fraction": float(multiproduct["csr_gsfc_recent_sign_match"].mean()),
        "all_city_csr_gsfc_theilsen_sign_agreement_fraction": float(multiproduct["csr_gsfc_theilsen_sign_match"].mean()),
        "jpl_status": jpl_status,
    }

    ghsl_matches.to_csv(DER / "ghsl_urban_centre_matches_r21.csv", index=False, encoding="utf-8")
    ghsl_aggregate.to_csv(DER / "ghsl_urban_centre_aggregates_r21.csv", index=False, encoding="utf-8")
    ghsl_hotspot.to_csv(DER / "hotspot_ghsl_polygon_robustness_r21.csv", index=False, encoding="utf-8")
    gsfc.to_csv(DER / "gsfc_city_trends_r21.csv", index=False, encoding="utf-8")
    multiproduct.to_csv(DER / "multi_product_sign_robustness_r21.csv", index=False, encoding="utf-8")
    status.to_csv(DER / "r21_external_data_status.csv", index=False, encoding="utf-8")
    (DER / "r21_multi_product_polygon_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_fig7(ghsl_hotspot, multiproduct, gsfc, summary)

    print(json.dumps(summary, indent=2))
    print("Saved R21 GHSL/GSFC/JPL robustness tables and Fig7.")


if __name__ == "__main__":
    main()
