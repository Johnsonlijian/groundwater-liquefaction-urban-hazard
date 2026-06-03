"""R20 spatial-independence, coastal-sensitivity and policy-trigger analysis.

This script implements the immediate, reproducible parts of the R20 red-team
upgrade using the data already present in the project:

- metropolitan point-city deduplication by distance;
- GRACE-scale 300 km block grouping and Simes/BH block FDR;
- coastline-distance and inland-control checks for coastal hotspots;
- available driver-sign ensemble using CSR TWS windows/methods plus CPC-corrected GWS;
- cumulative 2015-2024 Delta P definition and annualized sensitivity;
- water-table-rise trigger threshold for +0.01 modelled Delta P_liq;
- Fig. 6 trigger/policy figure.

The script does not pretend that GHSL polygons, JPL CRI-filtered mascons or GSFC
mascons have been ingested. It writes an external-product status table that
separates completed local checks from pending product-level robustness.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.lines import Line2D
from scipy.spatial import cKDTree
from scipy.stats import linregress, theilslopes

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
RAW = ROOT / "data_raw"
NE = RAW / "naturalearth"
GRACE = RAW / "grace" / "CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc"
FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))

from zhu2017 import p_liquefaction


MATERIAL = 0.01
Q_FDR = 0.10
NYEARS_RECENT = 10.0
SY_DEFAULT = 0.10
WTD_COEF = 0.0333
R_EARTH_KM = 6371.0
RED = "#c0392b"
BLUE = "#2c6fbb"
GREY = "#b9c0c7"
INK = "#222222"


def lonlat_xyz(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    lon = np.radians(np.asarray(lon, float))
    lat = np.radians(np.asarray(lat, float))
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def haversine_matrix(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    lon = np.radians(np.asarray(lon, float))
    lat = np.radians(np.asarray(lat, float))
    dlon = lon[:, None] - lon[None, :]
    dlat = lat[:, None] - lat[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.minimum(1, np.sqrt(a)))


def connected_components_from_distance(lon: np.ndarray, lat: np.ndarray, threshold_km: float) -> np.ndarray:
    dist = haversine_matrix(lon, lat)
    n = len(lon)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    rows, cols = np.where((dist <= threshold_km) & (dist > 0))
    for a, b in zip(rows, cols):
        if a < b:
            union(int(a), int(b))
    roots = [find(i) for i in range(n)]
    mapping: dict[int, int] = {}
    labels = []
    for r in roots:
        if r not in mapping:
            mapping[r] = len(mapping) + 1
        labels.append(mapping[r])
    return np.asarray(labels, int)


def bh_fdr(p: np.ndarray, q: float = Q_FDR) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    passed = p[order] <= q * (np.arange(1, n + 1)) / n
    k = np.where(passed)[0].max() + 1 if passed.any() else 0
    out = np.zeros(n, bool)
    out[order[:k]] = True
    return out


def by_fdr(p: np.ndarray, q: float = Q_FDR) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    c_m = np.sum(1.0 / np.arange(1, n + 1))
    order = np.argsort(p)
    passed = p[order] <= q * (np.arange(1, n + 1)) / (n * c_m)
    k = np.where(passed)[0].max() + 1 if passed.any() else 0
    out = np.zeros(n, bool)
    out[order[:k]] = True
    return out


def simes_p(pvals: pd.Series) -> float:
    p = np.sort(np.asarray(pvals, float))
    p = np.where(np.isfinite(p), p, 1.0)
    m = len(p)
    if m == 0:
        return 1.0
    return float(np.minimum(1.0, np.min(m * p / np.arange(1, m + 1))))


def logit(p: np.ndarray | float) -> np.ndarray | float:
    p = np.asarray(p)
    return np.log(p / (1 - p))


def load_cohort() -> pd.DataFrame:
    results = pd.read_csv(DER / "city_results_v2.csv")
    inputs = pd.read_csv(DER / "city_inputs.csv")
    gw = pd.read_csv(DER / "city_gws.csv")
    inputs = inputs.copy()
    inputs["recent_trend_cm_yr"] = gw["recent_trend_cm_yr"].values
    inputs["recent_se_cm_yr"] = gw["recent_se_cm_yr"].values
    inputs["recent_gws_cm_yr"] = gw["recent_gws_cm_yr"].values
    inputs["full_trend_cm_yr"] = gw["full_trend_cm_yr"].values
    inputs["full_gws_cm_yr"] = gw["full_gws_cm_yr"].values
    inputs["recent_sm_cm_yr"] = gw["recent_sm_cm_yr"].values
    inputs["full_sm_cm_yr"] = gw["full_sm_cm_yr"].values
    keys = ["name", "country", "lat", "lon"]
    df = results.merge(inputs, on=keys, suffixes=("", "_input"), validate="one_to_one")
    df["P0"] = p_liquefaction(
        100.0 * df["pga_475_g"],
        df["vs30"],
        df["precip"],
        df["dw_km"],
        df["wtd"],
    )
    df["is_material_hotspot"] = df["fdr_sig"] & (df["dP"].abs() >= MATERIAL)
    df["direction"] = np.select(
        [df["dP"] >= MATERIAL, df["dP"] <= -MATERIAL, df["dP"] > 0, df["dP"] < 0],
        ["material increase", "material decrease", "sub-material increase", "sub-material decrease"],
        default="near zero",
    )
    df["recent_cumulative_dTWS_cm"] = df["recent_trend_cm_yr"] * NYEARS_RECENT
    df["recent_cumulative_water_table_rise_m_sy010"] = df["recent_cumulative_dTWS_cm"] / 100.0 / SY_DEFAULT
    df["annualized_dP_per_year"] = df["dP"] / NYEARS_RECENT
    return df


def add_grace_grid_ids(df: pd.DataFrame) -> pd.DataFrame:
    ds = xr.open_dataset(GRACE)
    lat = ds["lat"].values
    lon = ds["lon"].values
    ix = np.array([int(np.abs(lon - (x % 360.0)).argmin()) for x in df["lon"].values])
    iy = np.array([int(np.abs(lat - y).argmin()) for y in df["lat"].values])
    out = df.copy()
    out["csr_grid_ix"] = ix
    out["csr_grid_iy"] = iy
    out["csr_grid_lon"] = lon[ix]
    out["csr_grid_lat"] = lat[iy]
    out["csr_grid_cell_id"] = [f"iy{a}_ix{b}" for a, b in zip(iy, ix)]
    ds.close()
    return out


def coastline_distances(df: pd.DataFrame) -> pd.DataFrame:
    coast = gpd.read_file(f"zip://{NE / 'ne_10m_coastline.zip'}")
    coords: list[tuple[float, float]] = []
    for geom in coast.geometry:
        if geom is None:
            continue
        geoms = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
        for line in geoms:
            coords.extend(list(line.coords))
    arr = np.asarray(coords, float)
    tree = cKDTree(lonlat_xyz(arr[:, 0], arr[:, 1]))
    chord, _ = tree.query(lonlat_xyz(df["lon"].values, df["lat"].values), k=1)
    dist = 2 * np.arcsin(np.clip(chord / 2, 0, 1)) * R_EARTH_KM
    out = df.copy()
    out["distance_to_coast_km"] = dist
    out["coastal_lt25km"] = dist < 25
    out["coastal_lt50km"] = dist < 50
    out["coastal_lt100km"] = dist < 100
    return out


def build_spatial_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    out = df.copy()
    out["metro_cluster_50km"] = connected_components_from_distance(out["lon"].values, out["lat"].values, 50.0)
    out["grace_scale_cluster_300km"] = connected_components_from_distance(out["lon"].values, out["lat"].values, 300.0)
    out["city_by_fdr_sig"] = by_fdr(out["p_two"].values, Q_FDR)

    metro_rows = []
    for cid, g in out.groupby("metro_cluster_50km"):
        w = g["population"].astype(float)
        material = g[g["is_material_hotspot"]]
        metro_rows.append(
            {
                "metro_cluster_50km": cid,
                "n_point_cities": len(g),
                "matched_GeoNames": "; ".join(g.sort_values("population", ascending=False)["name"].astype(str)),
                "countries": "; ".join(sorted(set(g["country"].astype(str)))),
                "population_sum": int(g["population"].sum()),
                "population_weighted_dP": float(np.average(g["dP"], weights=w)),
                "max_abs_dP": float(g["dP"].abs().max()),
                "n_material_point_hotspots": int(len(material)),
                "cluster_hotspot_flag": bool(len(material) > 0),
                "material_point_names": "; ".join(material["name"].astype(str)),
            }
        )
    metro = pd.DataFrame(metro_rows).sort_values(["cluster_hotspot_flag", "max_abs_dP"], ascending=[False, False])

    block_rows = []
    for block_type, col in [("csr_grid_cell", "csr_grid_cell_id"), ("grace_scale_300km", "grace_scale_cluster_300km")]:
        for bid, g in out.groupby(col):
            p_simes = simes_p(g["p_two"])
            weighted_dP = float(np.average(g["dP"], weights=g["population"].astype(float)))
            block_rows.append(
                {
                    "block_type": block_type,
                    "block_id": str(bid),
                    "n_cities": len(g),
                    "city_names": "; ".join(g.sort_values("population", ascending=False)["name"].astype(str)),
                    "p_simes": p_simes,
                    "population_weighted_dP": weighted_dP,
                    "median_dP": float(g["dP"].median()),
                    "n_material_hotspots": int(g["is_material_hotspot"].sum()),
                    "n_fdr_sig_cities": int(g["fdr_sig"].sum()),
                }
            )
    blocks = pd.DataFrame(block_rows)
    blocks["block_fdr_sig"] = False
    for block_type, idx in blocks.groupby("block_type").groups.items():
        blocks.loc[idx, "block_fdr_sig"] = bh_fdr(blocks.loc[idx, "p_simes"].values, Q_FDR)
    blocks = blocks.sort_values(["block_type", "block_fdr_sig", "n_material_hotspots"], ascending=[True, False, False])

    hotspot = out[out["is_material_hotspot"]].copy()
    hotspot = hotspot.merge(
        metro[
            [
                "metro_cluster_50km",
                "n_point_cities",
                "matched_GeoNames",
                "population_weighted_dP",
                "n_material_point_hotspots",
            ]
        ],
        on="metro_cluster_50km",
        how="left",
        suffixes=("", "_metro"),
    )
    grace_blocks = blocks[blocks["block_type"] == "grace_scale_300km"][
        ["block_id", "n_cities", "p_simes", "block_fdr_sig", "population_weighted_dP"]
    ].rename(
        columns={
            "block_id": "grace_scale_cluster_300km",
            "n_cities": "n_cities_in_300km_block",
            "p_simes": "simes_p_300km_block",
            "block_fdr_sig": "block_fdr_sig_300km",
            "population_weighted_dP": "block_population_weighted_dP_300km",
        }
    )
    grace_blocks["grace_scale_cluster_300km"] = grace_blocks["grace_scale_cluster_300km"].astype(int)
    hotspot = hotspot.merge(grace_blocks, on="grace_scale_cluster_300km", how="left")
    return out, metro, blocks, hotspot


def coastal_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    hotspots = df[df["is_material_hotspot"]].copy()
    dist_mat = haversine_matrix(df["lon"].values, df["lat"].values)
    df_index = {i: idx for i, idx in enumerate(df.index)}
    for i, r in hotspots.iterrows():
        pos = int(np.where(df.index.values == i)[0][0])
        candidate_pos = np.where((dist_mat[pos] >= 100) & (dist_mat[pos] <= 300))[0]
        controls = df.loc[[df_index[j] for j in candidate_pos]]
        inland_controls = controls[controls["distance_to_coast_km"] >= 50]
        median_inland = float(inland_controls["recent_trend_cm_yr"].median()) if len(inland_controls) else np.nan
        sign_agree = bool(np.sign(median_inland) == np.sign(r["recent_trend_cm_yr"])) if np.isfinite(median_inland) else False
        if r["distance_to_coast_km"] < 50:
            robustness = "coastal-sensitive; multi-product CRI/GSFC check required"
        elif r["distance_to_coast_km"] < 100:
            robustness = "near-coastal; report with caution"
        else:
            robustness = "not coastal by 100 km screen"
        if len(inland_controls) and sign_agree:
            robustness += "; inland controls share sign"
        rows.append(
            {
                "name": r["name"],
                "country": r["country"],
                "direction": r["direction"],
                "distance_to_coast_km": float(r["distance_to_coast_km"]),
                "coastal_lt25km": bool(r["coastal_lt25km"]),
                "coastal_lt50km": bool(r["coastal_lt50km"]),
                "coastal_lt100km": bool(r["coastal_lt100km"]),
                "csr_recent_tws_cm_yr": float(r["recent_trend_cm_yr"]),
                "n_inland_controls_100_300km": int(len(inland_controls)),
                "median_inland_control_tws_cm_yr": median_inland,
                "inland_control_sign_agreement": sign_agree,
                "coastal_robustness_status": robustness,
            }
        )
    return pd.DataFrame(rows)


def decode_years(ds: xr.Dataset) -> np.ndarray:
    t = ds["time"]
    units = t.attrs.get("units", "days since 2002-01-01 00:00:00")
    try:
        dt = xr.coding.times.decode_cf_datetime(t.values, units)
        return np.array(
            [
                d.astype("datetime64[D]").astype(object).year
                + (d.astype("datetime64[D]").astype(object).timetuple().tm_yday - 1) / 365.25
                for d in dt
            ]
        )
    except Exception:
        return 2002.0 + t.values / 365.25


def slope_for_window(years: np.ndarray, ts: np.ndarray, y0: float, y1: float, method: str) -> float:
    mask = (years >= y0) & (years <= y1) & np.isfinite(ts)
    if mask.sum() < 18:
        return np.nan
    x = years[mask]
    y = ts[mask]
    if method == "ols":
        return float(linregress(x, y).slope)
    if method == "theilsen":
        return float(theilslopes(y, x).slope)
    raise ValueError(method)


def driver_sign_table(df: pd.DataFrame) -> pd.DataFrame:
    ds = xr.open_dataset(GRACE)
    years = decode_years(ds)
    lwe = ds["lwe_thickness"].values
    lat = ds["lat"].values
    lon = ds["lon"].values
    windows = {
        "2014_2024": (2014.0, 2024.99),
        "2015_2024": (2015.0, 2024.99),
        "2016_2024": (2016.0, 2024.99),
        "2018_2024": (2018.0, 2024.99),
    }
    rows = []
    for _, r in df.iterrows():
        ix = int(r["csr_grid_ix"])
        iy = int(r["csr_grid_iy"])
        ts = lwe[:, iy, ix].astype(float)
        rec = {
            "name": r["name"],
            "country": r["country"],
            "baseline_csr_recent_tws_cm_yr": float(r["recent_trend_cm_yr"]),
            "baseline_sign": int(np.sign(r["recent_trend_cm_yr"])),
            "cpc_corrected_recent_gws_cm_yr": float(r["recent_gws_cm_yr"]),
            "cpc_corrected_full_gws_cm_yr": float(r["full_gws_cm_yr"]),
        }
        signs = []
        labels = []
        for tag, (y0, y1) in windows.items():
            for method in ["ols", "theilsen"]:
                slope = slope_for_window(years, ts, y0, y1, method)
                col = f"csr_tws_{method}_{tag}_cm_yr"
                rec[col] = slope
                if np.isfinite(slope) and slope != 0:
                    signs.append(int(np.sign(slope)))
                    labels.append(col)
        for col in ["cpc_corrected_recent_gws_cm_yr", "cpc_corrected_full_gws_cm_yr"]:
            val = rec[col]
            if np.isfinite(val) and val != 0:
                signs.append(int(np.sign(val)))
                labels.append(col)
        baseline = rec["baseline_sign"]
        if baseline == 0 or not signs:
            frac = np.nan
            n_agree = 0
        else:
            n_agree = int(np.sum(np.asarray(signs) == baseline))
            frac = float(n_agree / len(signs))
        rec["n_available_driver_signs"] = len(signs)
        rec["n_available_signs_matching_baseline"] = n_agree
        rec["available_sign_agreement_fraction"] = frac
        rec["available_sign_agreement_grade"] = (
            "available-robust" if np.isfinite(frac) and frac >= 0.75 else
            "available-probable" if np.isfinite(frac) and frac >= 0.60 else
            "available-sensitive"
        )
        rec["sign_drivers_used"] = "; ".join(labels)
        rows.append(rec)
    ds.close()
    out = pd.DataFrame(rows)
    return out


def trigger_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    p0 = np.clip(out["P0"].to_numpy(float), 1e-6, 1 - MATERIAL - 1e-6)
    target = np.minimum(p0 + MATERIAL, 1 - 1e-6)
    h = (logit(target) - logit(p0)) / WTD_COEF
    out["water_table_rise_trigger_m_for_plus0p01"] = h
    out["trigger_reachable_before_surface"] = h <= out["wtd"].to_numpy(float)
    rise_rate = out["recent_trend_cm_yr"].to_numpy(float) / 100.0 / SY_DEFAULT
    out["years_to_trigger_at_recent_rise_sy010"] = np.where(rise_rate > 0, h / rise_rate, np.nan)
    out["liquefaction_sensitivity_per_m_rise"] = WTD_COEF * out["P0"].to_numpy(float) * (1 - out["P0"].to_numpy(float))
    out["linearized_dP_sy010"] = out["liquefaction_sensitivity_per_m_rise"] * out["recent_cumulative_water_table_rise_m_sy010"]
    keep = [
        "name", "country", "lat", "lon", "population", "P0", "pga_475_g", "wtd", "recent_trend_cm_yr",
        "dP", "dP_lo", "dP_hi", "fdr_sig", "is_material_hotspot", "direction",
        "recent_cumulative_dTWS_cm", "recent_cumulative_water_table_rise_m_sy010", "annualized_dP_per_year",
        "liquefaction_sensitivity_per_m_rise", "water_table_rise_trigger_m_for_plus0p01",
        "trigger_reachable_before_surface", "years_to_trigger_at_recent_rise_sy010",
        "linearized_dP_sy010", "distance_to_coast_km", "metro_cluster_50km", "grace_scale_cluster_300km",
    ]
    return out[keep].sort_values("water_table_rise_trigger_m_for_plus0p01")


def attribution_matrix() -> pd.DataFrame:
    rows = [
        {
            "region_or_city": "North China Plain / Beijing",
            "groundwater_or_storage_sign": "positive recent TWS; well-supported recovery",
            "independent_groundwater_evidence": "Regional well network and Beijing urban-well liquefaction study",
            "management_or_abstraction_evidence": "South-North Water Transfer and managed aquifer recovery",
            "attribution_confidence": "high",
            "main_text_use": "management-supported recharge case",
        },
        {
            "region_or_city": "Delhi",
            "groundwater_or_storage_sign": "negative recent TWS",
            "independent_groundwater_evidence": "CGWB station analyses show increasing depth to groundwater in most of the Delhi Metropolitan Region",
            "management_or_abstraction_evidence": "abstraction/depletion context",
            "attribution_confidence": "medium-high",
            "main_text_use": "depletion-side case",
        },
        {
            "region_or_city": "Lahore",
            "groundwater_or_storage_sign": "negative recent TWS",
            "independent_groundwater_evidence": "Borehole depth-to-water, GRACE and InSAR subsidence evidence",
            "management_or_abstraction_evidence": "abstraction/depletion context",
            "attribution_confidence": "medium-high",
            "main_text_use": "depletion-side case",
        },
        {
            "region_or_city": "Ludhiana / Punjab",
            "groundwater_or_storage_sign": "negative recent TWS",
            "independent_groundwater_evidence": "NW India/Punjab depletion context from GRACE and groundwater-level syntheses",
            "management_or_abstraction_evidence": "regional abstraction/depletion context",
            "attribution_confidence": "medium",
            "main_text_use": "depletion-side hotspot, not a safety benefit",
        },
        {
            "region_or_city": "Yokohama / Tokyo Bay",
            "groundwater_or_storage_sign": "positive recent TWS",
            "independent_groundwater_evidence": "local 2015-2024 groundwater evidence not yet ingested",
            "management_or_abstraction_evidence": "long-term Tokyo-area groundwater regulation is a candidate context, not proof of the 2015-2024 GRACE sign",
            "attribution_confidence": "low-pending",
            "main_text_use": "coastal-sensitive positive hotspot pending product/local evidence",
        },
        {
            "region_or_city": "Mumbai-Bhayandar cluster",
            "groundwater_or_storage_sign": "positive recent TWS",
            "independent_groundwater_evidence": "local 2015-2024 groundwater evidence not yet ingested",
            "management_or_abstraction_evidence": "unclear",
            "attribution_confidence": "low-pending",
            "main_text_use": "metro-deduplicated coastal-sensitive positive hotspot pending product/local evidence",
        },
    ]
    return pd.DataFrame(rows)


def external_product_status() -> pd.DataFrame:
    rows = [
        {
            "product_or_dataset": "CSR GRACE/GRACE-FO RL06.3 mascon",
            "status_in_this_project": "ingested and used",
            "official_source": "https://www2.csr.utexas.edu/grace/RL06_mascons.html",
            "local_action": "current primary regional storage driver",
        },
        {
            "product_or_dataset": "JPL GRACE/GRACE-FO Mascon RL06.3Mv04 CRI-filtered",
            "status_in_this_project": "not yet ingested",
            "official_source": "https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_GRID_RL06.3_V4",
            "local_action": "required before claiming independent mascon-product sign robustness for coastal hotspots",
        },
        {
            "product_or_dataset": "NASA GSFC GRACE/GRACE-FO RL06v2.0 mascon",
            "status_in_this_project": "not yet ingested",
            "official_source": "https://earth.gsfc.nasa.gov/geo/data/grace-mascons",
            "local_action": "required before claiming three-product sign agreement",
        },
        {
            "product_or_dataset": "GHSL Urban Centre Database R2024A",
            "status_in_this_project": "not yet ingested",
            "official_source": "https://human-settlement.emergency.copernicus.eu/ghs_ucdb_2024.php",
            "local_action": "required for polygon-based urban-centre replacement of GeoNames points",
        },
    ]
    return pd.DataFrame(rows)


def make_fig6(trigger: pd.DataFrame, spatial: pd.DataFrame) -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 8,
            "axes.linewidth": 0.7,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    d = trigger.copy()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 5.4), gridspec_kw={"width_ratios": [1.25, 1.0]})
    plot = d[np.isfinite(d["water_table_rise_trigger_m_for_plus0p01"]) & (d["water_table_rise_trigger_m_for_plus0p01"] <= 20)].copy()
    sizes = 14 + 85 * np.sqrt(plot["population"] / plot["population"].max())
    sc = ax1.scatter(
        plot["P0"],
        plot["water_table_rise_trigger_m_for_plus0p01"],
        c=plot["recent_trend_cm_yr"],
        cmap="RdBu_r",
        vmin=-5,
        vmax=5,
        s=sizes,
        alpha=0.62,
        edgecolors="#555555",
        linewidths=0.25,
    )
    key_names = ["Beijing", "Tianjin", "Yokohama", "Mumbai", "Bhayandar", "Delhi", "Lahore", "Ludhiana"]
    for _, r in plot[plot["name"].isin(key_names)].iterrows():
        color = RED if r["recent_trend_cm_yr"] > 0 else BLUE
        ax1.scatter([r["P0"]], [r["water_table_rise_trigger_m_for_plus0p01"]], s=110, facecolors="none", edgecolors=color, linewidths=1.3)
        ax1.annotate(r["name"], (r["P0"], r["water_table_rise_trigger_m_for_plus0p01"]), xytext=(4, 4), textcoords="offset points", fontsize=6.8)
    ax1.set_yscale("log")
    ax1.set_xlabel("Baseline modelled liquefaction probability")
    ax1.set_ylabel("Water-table rise needed for +0.01 Delta P_liq (m)")
    ax1.set_title("a  A policy trigger for managed recovery", loc="left", fontweight="bold")
    ax1.grid(alpha=0.22, which="both")
    cb = fig.colorbar(sc, ax=ax1, shrink=0.75, pad=0.01)
    cb.set_label("Recent TWS trend (cm yr-1)", fontsize=7)

    hs = spatial[spatial["is_material_hotspot"]].copy()
    hs = hs.sort_values("dP")
    y = np.arange(len(hs))
    colors = np.where(hs["dP"] > 0, RED, BLUE)
    ax2.barh(y, hs["dP"], color=colors, alpha=0.78)
    ax2.axvline(0, color="#555555", lw=0.8)
    ax2.axvline(MATERIAL, color="#999999", lw=0.7, ls="--")
    ax2.axvline(-MATERIAL, color="#999999", lw=0.7, ls="--")
    labels = []
    for _, r in hs.iterrows():
        coastal = "coastal" if r["distance_to_coast_km"] < 50 else "inland"
        labels.append(f"{r['name']} ({coastal})")
    ax2.set_yticks(y)
    ax2.set_yticklabels(labels)
    ax2.set_xlabel("Cumulative Delta P_liq, 2015-2024")
    ax2.set_title("b  Point hotspots after spatial/coastal checks", loc="left", fontweight="bold")
    for i, (_, r) in enumerate(hs.iterrows()):
        txt = f"metro {int(r['metro_cluster_50km'])}; 300 km block {int(r['grace_scale_cluster_300km'])}"
        ax2.text(0.001 if r["dP"] < 0 else -0.001, i, txt, va="center", ha="left" if r["dP"] < 0 else "right", fontsize=6.3, color="#555555")
    handles = [
        Line2D([0], [0], color=RED, lw=5, label="increase"),
        Line2D([0], [0], color=BLUE, lw=5, label="decrease"),
    ]
    ax2.legend(handles=handles, loc="lower right", fontsize=7)
    fig.suptitle("Water-table-rise trigger and spatial robustness for policy screening", fontsize=11, fontweight="bold")
    fig.tight_layout()
    for ext, kwargs in {"png": {"dpi": 400}, "svg": {}, "pdf": {}}.items():
        fig.savefig(FIG / f"Fig6_trigger_spatial_robustness.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def main() -> None:
    df = load_cohort()
    df = add_grace_grid_ids(df)
    df = coastline_distances(df)
    spatial, metro, blocks, hotspot_spatial = build_spatial_tables(df)
    coastal = coastal_table(spatial)
    signs = driver_sign_table(spatial)
    hotspot_signs = signs.merge(spatial[["name", "country", "is_material_hotspot"]], on=["name", "country"], how="left")
    hotspot_signs = hotspot_signs[hotspot_signs["is_material_hotspot"]].drop(columns=["is_material_hotspot"])
    trigger = trigger_table(spatial)
    attr = attribution_matrix()
    external = external_product_status()

    spatial.to_csv(DER / "city_results_spatial_r20.csv", index=False, encoding="utf-8")
    metro.to_csv(DER / "metro_deduplication_r20.csv", index=False, encoding="utf-8")
    blocks.to_csv(DER / "spatial_block_fdr_r20.csv", index=False, encoding="utf-8")
    hotspot_spatial.to_csv(DER / "hotspot_spatial_robustness_r20.csv", index=False, encoding="utf-8")
    coastal.to_csv(DER / "coastal_robustness_r20.csv", index=False, encoding="utf-8")
    signs.to_csv(DER / "driver_sign_robustness_r20.csv", index=False, encoding="utf-8")
    hotspot_signs.to_csv(DER / "hotspot_driver_sign_robustness_r20.csv", index=False, encoding="utf-8")
    trigger.to_csv(DER / "water_table_trigger_r20.csv", index=False, encoding="utf-8")
    attr.to_csv(DER / "attribution_confidence_matrix_r20.csv", index=False, encoding="utf-8")
    external.to_csv(DER / "external_product_status_r20.csv", index=False, encoding="utf-8")
    make_fig6(trigger, spatial)

    material_clusters = int(spatial.loc[spatial["is_material_hotspot"], "metro_cluster_50km"].nunique())
    material_300km_blocks = int(spatial.loc[spatial["is_material_hotspot"], "grace_scale_cluster_300km"].nunique())
    positive_hotspots = spatial[spatial["is_material_hotspot"] & (spatial["dP"] > 0)]
    positive_coastal_lt50 = int((positive_hotspots["distance_to_coast_km"] < 50).sum())
    robust_available_signs = int((hotspot_signs["available_sign_agreement_grade"] == "available-robust").sum())
    probable_available_signs = int((hotspot_signs["available_sign_agreement_grade"] == "available-probable").sum())
    summary = {
        "n_cities": int(len(spatial)),
        "n_material_point_hotspots": int(spatial["is_material_hotspot"].sum()),
        "n_material_metro_clusters_50km": material_clusters,
        "n_material_300km_blocks": material_300km_blocks,
        "n_positive_material_hotspots": int(len(positive_hotspots)),
        "n_positive_material_hotspots_coastal_lt50km": positive_coastal_lt50,
        "city_bh_fdr_sig": int(spatial["fdr_sig"].sum()),
        "city_by_fdr_sig": int(spatial["city_by_fdr_sig"].sum()),
        "n_300km_blocks": int(spatial["grace_scale_cluster_300km"].nunique()),
        "n_300km_blocks_fdr_sig": int(blocks[(blocks["block_type"] == "grace_scale_300km") & (blocks["block_fdr_sig"])].shape[0]),
        "n_material_hotspots_available_sign_robust": robust_available_signs,
        "n_material_hotspots_available_sign_probable": probable_available_signs,
        "median_trigger_rise_m": float(np.nanmedian(trigger["water_table_rise_trigger_m_for_plus0p01"])),
        "beijing_trigger_rise_m": float(trigger.loc[trigger["name"] == "Beijing", "water_table_rise_trigger_m_for_plus0p01"].iloc[0]),
        "external_products_pending": ["GHSL Urban Centre Database", "JPL CRI-filtered mascon", "NASA GSFC mascon"],
    }
    (DER / "r20_spatial_trigger_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("Saved R20 spatial/coastal/trigger tables and Fig6.")


if __name__ == "__main__":
    main()
