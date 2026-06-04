"""R19 Nature Water figure and supplementary-table upgrade.

This script regenerates Figures 1-5 with policy-facing annotations and writes
extra derived products requested by the Nature Water adversarial uplift:

- hotspot_sensitivity_city_grid_v2.csv
- sensitivity_parameter_effects_v2.csv
- policy_exposure_summary_v2.csv

The script does not ingest new private or unavailable well records. Independent
well/borehole/InSAR evidence is shown as validation anchors and kept separate
from the GRACE-derived city values.
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
import xarray as xr
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from pyproj import Transformer
from scipy.stats import linregress


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
NE = ROOT / "data_raw" / "naturalearth"
GRACE = ROOT / "data_raw" / "grace" / "CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc"
FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))

from zhu2017 import p_liquefaction


MATERIAL = 0.01
NYEARS = 10.0
K_VALUES = [60, 80, 100, 120, 150]
SY_VALUES = [0.05, 0.075, 0.10, 0.15, 0.20, 0.25]
TREND_MULTIPLIERS = [0.5, 0.8, 1.0, 1.2, 1.5]

RED = "#c0392b"
BLUE = "#2c6fbb"
GREEN = "#2e8b57"
INK = "#222222"
GREY = "#b9c0c7"
SAND = "#e9dcc3"
WATER = "#9ec9e8"


def set_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "font.size": 8,
            "axes.linewidth": 0.7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "savefig.dpi": 400,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )


def save_figure(fig: mpl.figure.Figure, stem: str) -> None:
    for ext, kwargs in {"png": {"dpi": 400}, "svg": {}, "pdf": {}}.items():
        fig.savefig(FIG / f"{stem}.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def load_cohort() -> pd.DataFrame:
    inputs = pd.read_csv(DER / "city_inputs.csv")
    gw = pd.read_csv(DER / "city_gws.csv")
    results = pd.read_csv(DER / "city_results_v2.csv")

    inputs = inputs.copy()
    inputs["recent_trend_cm_yr"] = gw["recent_trend_cm_yr"].values
    inputs["recent_se_cm_yr"] = gw["recent_se_cm_yr"].values
    inputs["recent_gws_cm_yr"] = gw["recent_gws_cm_yr"].values
    inputs["reversal_driver"] = gw["reversal"].values

    keys = ["name", "country", "lat", "lon"]
    cohort = results.merge(inputs, on=keys, suffixes=("", "_input"), validate="one_to_one")
    cohort["P0"] = p_liquefaction(
        100.0 * cohort["pga_475_g"],
        cohort["vs30"],
        cohort["precip"],
        cohort["dw_km"],
        cohort["wtd"],
    )
    cohort["population_million"] = cohort["population"] / 1e6
    cohort["population_weighted_abs_dP"] = cohort["population_million"] * cohort["dP"].abs()
    return cohort


def delta_p(cohort: pd.DataFrame, k: float, sy: float, trend_multiplier: float) -> np.ndarray:
    trend = cohort["recent_trend_cm_yr"].to_numpy(float) * trend_multiplier
    dwtd = -(trend * NYEARS / 100.0) / sy
    p0 = p_liquefaction(
        k * cohort["pga_475_g"],
        cohort["vs30"],
        cohort["precip"],
        cohort["dw_km"],
        cohort["wtd"],
    )
    p1 = p_liquefaction(
        k * cohort["pga_475_g"],
        cohort["vs30"],
        cohort["precip"],
        cohort["dw_km"],
        np.maximum(cohort["wtd"].to_numpy(float) + dwtd, 0.0),
    )
    return np.asarray(p1 - p0, float)


def build_supplementary_tables(cohort: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hotspots = pd.read_csv(DER / "hotspot_table.csv")
    hot_keys = set(zip(hotspots["name"], hotspots["country"]))
    hot_mask = cohort.apply(lambda r: (r["name"], r["country"]) in hot_keys, axis=1).to_numpy()

    combo_rows = []
    city_rows = []
    for k in K_VALUES:
        for sy in SY_VALUES:
            for mult in TREND_MULTIPLIERS:
                dP = delta_p(cohort, k, sy, mult)
                hot_abs = np.abs(dP[hot_mask])
                combo_rows.append(
                    {
                        "pgv_per_pga_k": k,
                        "specific_yield": sy,
                        "trend_multiplier": mult,
                        "mean_dP": float(np.mean(dP)),
                        "median_abs_dP": float(np.median(np.abs(dP))),
                        "mean_hotspot_abs_dP": float(np.mean(hot_abs)),
                        "n_material_increase": int((dP >= MATERIAL).sum()),
                        "n_material_decrease": int((dP <= -MATERIAL).sum()),
                        "n_material_any_direction": int((np.abs(dP) >= MATERIAL).sum()),
                        "n_positive": int((dP > 0).sum()),
                        "n_negative": int((dP < 0).sum()),
                        "hotspot_sign_reversals": int(
                            np.sum(np.sign(dP[hot_mask]) != np.sign(cohort.loc[hot_mask, "dP"].to_numpy(float)))
                        ),
                    }
                )
                for idx, row in cohort.loc[hot_mask].iterrows():
                    city_rows.append(
                        {
                            "name": row["name"],
                            "country": row["country"],
                            "pgv_per_pga_k": k,
                            "specific_yield": sy,
                            "trend_multiplier": mult,
                            "dP": float(dP[idx]),
                            "is_material": bool(abs(dP[idx]) >= MATERIAL),
                            "sign_reversed_from_baseline": bool(np.sign(dP[idx]) != np.sign(row["dP"])),
                        }
                    )

    grid = pd.DataFrame(combo_rows)
    city_grid = pd.DataFrame(city_rows)
    grid.to_csv(DER / "sensitivity_grid_v2.csv", index=False, encoding="utf-8")
    city_grid.to_csv(DER / "hotspot_sensitivity_city_grid_v2.csv", index=False, encoding="utf-8")

    envelope = (
        city_grid.groupby(["name", "country"])["dP"]
        .agg(min_dP="min", median_dP="median", max_dP="max")
        .reset_index()
    )
    base = hotspots[["name", "country", "dP", "dP_lo", "dP_hi", "population", "tws_cm_yr", "direction"]]
    envelope = envelope.merge(base, on=["name", "country"], validate="one_to_one")
    envelope["sign_consistent_across_grid"] = np.sign(envelope["min_dP"]) == np.sign(envelope["max_dP"])
    envelope["material_fraction_across_grid"] = envelope.apply(
        lambda r: float(
            np.mean(
                np.abs(
                    city_grid[(city_grid["name"] == r["name"]) & (city_grid["country"] == r["country"])]["dP"]
                )
                >= MATERIAL
            )
        ),
        axis=1,
    )
    envelope.to_csv(DER / "hotspot_sensitivity_envelope_v2.csv", index=False, encoding="utf-8")

    effects = []
    for factor, label in [
        ("pgv_per_pga_k", "PGA-to-PGV conversion"),
        ("specific_yield", "Specific yield"),
        ("trend_multiplier", "GRACE trend magnitude"),
    ]:
        grouped = grid.groupby(factor).agg(
            n_material_any_direction=("n_material_any_direction", "mean"),
            median_abs_dP=("median_abs_dP", "mean"),
            mean_hotspot_abs_dP=("mean_hotspot_abs_dP", "mean"),
        )
        effects.append(
            {
                "parameter": label,
                "range_n_material_any_direction": float(
                    grouped["n_material_any_direction"].max() - grouped["n_material_any_direction"].min()
                ),
                "range_median_abs_dP": float(grouped["median_abs_dP"].max() - grouped["median_abs_dP"].min()),
                "range_mean_hotspot_abs_dP": float(
                    grouped["mean_hotspot_abs_dP"].max() - grouped["mean_hotspot_abs_dP"].min()
                ),
            }
        )
    effects_df = pd.DataFrame(effects).sort_values("range_mean_hotspot_abs_dP", ascending=False)
    effects_df.to_csv(DER / "sensitivity_parameter_effects_v2.csv", index=False, encoding="utf-8")

    policy = pd.read_csv(DER / "policy_priority_table_v2.csv")
    policy["direction"] = np.select(
        [policy["dP"] >= MATERIAL, policy["dP"] <= -MATERIAL, policy["dP"] > 0, policy["dP"] < 0],
        ["material increase", "material decrease", "sub-material increase", "sub-material decrease"],
        default="near zero",
    )
    policy["population_million"] = policy["population"] / 1e6
    policy["population_weighted_abs_dP"] = policy["population_million"] * policy["dP"].abs()
    exposure = (
        policy.groupby(["screening_tier", "direction"], dropna=False)
        .agg(
            n_cities=("name", "count"),
            population_million=("population_million", "sum"),
            population_weighted_abs_dP=("population_weighted_abs_dP", "sum"),
        )
        .reset_index()
        .sort_values(["screening_tier", "direction"])
    )
    exposure.to_csv(DER / "policy_exposure_summary_v2.csv", index=False, encoding="utf-8")
    policy.to_csv(DER / "policy_priority_table_v2.csv", index=False, encoding="utf-8")
    return grid, city_grid, envelope, effects_df


def fig1_mechanism() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.2))
    fig.suptitle("Groundwater management changes the water-table term in liquefaction screening", fontsize=11.5, fontweight="bold")

    specs = [
        {
            "title": "Recharge or aquifer recovery",
            "case": "North China Plain / Beijing",
            "color": RED,
            "new_wt_shift": 1.55,
            "risk": "P_liq increases",
            "action": "Liquefaction monitoring",
            "steps": [
                "water table rises",
                "pore pressure u increases",
                "effective stress decreases",
                "liquefaction resistance decreases",
                "modelled P_liq increases",
            ],
        },
        {
            "title": "Depletion or over-abstraction",
            "case": "Punjab / Delhi-Lahore-Ludhiana",
            "color": BLUE,
            "new_wt_shift": -1.55,
            "risk": "P_liq decreases, but subsidence risk rises",
            "action": "Subsidence + water-security audit",
            "steps": [
                "water table deepens",
                "pore pressure u decreases",
                "effective stress increases",
                "modelled P_liq decreases",
                "subsidence and scarcity remain",
            ],
        },
    ]

    for ax, spec in zip(axes, specs):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_axis_off()
        ax.set_title(spec["title"], fontsize=10, fontweight="bold", loc="left")
        ax.text(0.02, 0.91, spec["case"], transform=ax.transAxes, color=spec["color"], fontsize=8, fontstyle="italic")

        ax.add_patch(Rectangle((0.9, 1.0), 4.6, 7.0, facecolor=SAND, edgecolor=INK, lw=0.8))
        ax.add_patch(Rectangle((0.9, 1.0), 4.6, 2.1, facecolor="#c8b89d", edgecolor="#6f6f6f", lw=0.4))
        wt0 = 5.15
        wt1 = wt0 + spec["new_wt_shift"]
        ax.add_patch(Rectangle((0.9, 1.0), 4.6, max(wt1 - 1.0, 0.1), facecolor=WATER, edgecolor="none", alpha=0.45))
        ax.plot([0.9, 5.5], [wt0, wt0], color="#5c8fd6", lw=1.3, ls="--")
        ax.text(5.7, wt0, "baseline\nwater table", color="#2b6fc1", fontsize=7, va="center")
        ax.plot([0.9, 5.5], [wt1, wt1], color=spec["color"], lw=2.2)
        ax.add_patch(
            FancyArrowPatch(
                (3.2, wt0),
                (3.2, wt1),
                arrowstyle="-|>",
                mutation_scale=16,
                color=spec["color"],
                lw=2.2,
            )
        )

        y = 0.74
        for step in spec["steps"]:
            ax.text(0.62, y, step, transform=ax.transAxes, fontsize=7.8, color=INK, va="top")
            if y > 0.43:
                ax.add_patch(
                    FancyArrowPatch(
                        (0.80, y - 0.028),
                        (0.80, y - 0.075),
                        transform=ax.transAxes,
                        arrowstyle="-|>",
                        mutation_scale=7,
                        color="#777777",
                        lw=0.8,
                    )
                )
            y -= 0.09

        ax.add_patch(
            FancyBboxPatch(
                (0.60, 0.24),
                0.36,
                0.105,
                transform=ax.transAxes,
                boxstyle="round,pad=0.02",
                facecolor=spec["color"],
                alpha=0.12,
                edgecolor=spec["color"],
                lw=1.0,
            )
        )
        ax.text(0.78, 0.292, spec["risk"], transform=ax.transAxes, ha="center", va="center", fontsize=8.1, color=spec["color"], fontweight="bold")

        ax.add_patch(
            FancyBboxPatch(
                (0.58, 0.04),
                0.39,
                0.13,
                transform=ax.transAxes,
                boxstyle="round,pad=0.02",
                facecolor="#f7f7f7",
                edgecolor=spec["color"],
                lw=1.2,
            )
        )
        ax.text(0.775, 0.118, "Water-agency trigger", transform=ax.transAxes, ha="center", fontsize=7.0, color="#555555")
        ax.text(0.775, 0.072, spec["action"], transform=ax.transAxes, ha="center", fontsize=8.2, color=spec["color"], fontweight="bold")

    fig.text(
        0.5,
        0.01,
        "The mechanism changes liquefaction susceptibility if shaking occurs; it does not imply that groundwater causes earthquakes.",
        ha="center",
        fontsize=7.6,
        color="#555555",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    save_figure(fig, "Fig1_mechanism")


def fig2_global_map(cohort: pd.DataFrame) -> None:
    world = gpd.read_file(f"zip://{NE / 'ne_110m_admin_0_countries.zip'}").to_crs("ESRI:54030")
    tr = Transformer.from_crs("EPSG:4326", "ESRI:54030", always_xy=True)
    d = cohort.copy()
    d["X"], d["Y"] = tr.transform(d["lon"].values, d["lat"].values)
    material = d["fdr_sig"] & (d["dP"].abs() >= MATERIAL)

    fig, ax = plt.subplots(figsize=(7.4, 4.25))
    world.plot(ax=ax, color="#eef0f2", edgecolor="#cfd4d8", linewidth=0.3, zorder=1)
    sizes = 10 + 95 * np.sqrt(d["population"].values / d["population"].max())
    order = d["dP"].abs().sort_values().index
    plot = d.loc[order]
    sc = ax.scatter(
        plot["X"],
        plot["Y"],
        c=plot["dP"],
        cmap="RdBu_r",
        vmin=-0.03,
        vmax=0.03,
        s=sizes[order],
        edgecolors="#555555",
        linewidths=0.25,
        alpha=0.9,
        zorder=3,
    )

    mh = d[material].copy()
    ax.scatter(mh["X"], mh["Y"], s=260, facecolors="none", edgecolors="black", linewidths=1.4, zorder=4)
    ax.scatter(mh["X"], mh["Y"], s=60, c=np.where(mh["dP"] > 0, RED, BLUE), edgecolors="black", linewidths=0.5, zorder=5)
    for _, r in mh.iterrows():
        if r["name"] != "Yokohama":
            continue
        ax.annotate(
            r["name"],
            (r["X"], r["Y"]),
            xytext=(16, 12),
            textcoords="offset points",
            fontsize=7.4,
            arrowprops=dict(arrowstyle="-", color="#333333", lw=0.6),
            path_effects=[pe.withStroke(linewidth=2.4, foreground="white")],
            zorder=6,
        )

    inset = ax.inset_axes([0.485, 0.10, 0.35, 0.40])
    inset.set_facecolor("white")
    inset.patch.set_alpha(0.96)
    world.plot(ax=inset, color="#f5f6f7", edgecolor="#cfd4d8", linewidth=0.25, zorder=1)
    x0i, y0i = tr.transform(54.0, 9.0)
    x1i, y1i = tr.transform(90.0, 37.0)
    inset.set_xlim(min(x0i, x1i), max(x0i, x1i))
    inset.set_ylim(min(y0i, y1i), max(y0i, y1i))
    south = d[(d["lon"] >= 66.0) & (d["lon"] <= 82.5) & (d["lat"] >= 16.0) & (d["lat"] <= 34.5)]
    inset.scatter(
        south["X"],
        south["Y"],
        c=south["dP"],
        cmap="RdBu_r",
        vmin=-0.03,
        vmax=0.03,
        s=18 + 55 * np.sqrt(south["population"].values / d["population"].max()),
        edgecolors="#555555",
        linewidths=0.25,
        alpha=0.9,
        zorder=3,
    )
    south_m = mh[mh["name"].isin(["Ludhiana", "Lahore", "Delhi", "Bhayandar", "Mumbai"])]
    inset.scatter(south_m["X"], south_m["Y"], s=95, facecolors="none", edgecolors="#111111", linewidths=1.2, zorder=4)
    inset.scatter(
        south_m["X"],
        south_m["Y"],
        s=32,
        c=np.where(south_m["dP"] > 0, RED, BLUE),
        edgecolors="#111111",
        linewidths=0.35,
        zorder=5,
    )
    inset_offsets = {
        "Ludhiana": (-9, 9, "right", "center"),
        "Lahore": (5, -11, "left", "center"),
        "Delhi": (-9, -11, "right", "center"),
        "Bhayandar": (-9, -12, "right", "center"),
    }
    for _, r in south_m.iterrows():
        if r["name"] == "Mumbai":
            continue
        label = "Mumbai-\nBhayandar" if r["name"] == "Bhayandar" else r["name"]
        dx, dy, ha, va = inset_offsets.get(r["name"], (4, 4, "left", "center"))
        inset.annotate(
            label,
            (r["X"], r["Y"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=5.2,
            ha=ha,
            va=va,
            bbox=dict(boxstyle="round,pad=0.08", fc="white", ec="none", alpha=0.78),
            path_effects=[pe.withStroke(linewidth=1.6, foreground="white")],
            clip_on=True,
            zorder=6,
        )
    inset.set_title("South Asia detail", fontsize=6.5, fontweight="bold", pad=4)
    inset.set_xticks([])
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#555555")
        spine.set_linewidth(0.55)

    cb = fig.colorbar(sc, ax=ax, shrink=0.62, pad=0.01, extend="both")
    cb.set_label("Delta screening index\nfrom storage-derived change", fontsize=8.5)
    for p, lab in [(1e6, "1M"), (5e6, "5M"), (15e6, "15M")]:
        ax.scatter([], [], s=10 + 95 * np.sqrt(p / d["population"].max()), c="#9aa0a6", edgecolors="k", linewidths=0.25, label=lab)
    ax.legend(title="City population", loc="lower left", fontsize=7.2, title_fontsize=7.4, labelspacing=1.0)
    ax.set_title(
        "Global screen shows regional, bidirectional shifts rather than a diffuse worldwide increase",
        fontsize=9.8,
        fontweight="bold",
    )
    ax.text(
        0.5,
        -0.04,
        "Six material and FDR-significant screening units are ringed; South Asia units are labelled in the inset. GRACE/GRACE-FO is a regional driver; cities are exposure units.",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.8,
        color="#555555",
    )
    ax.set_axis_off()
    fig.tight_layout()
    save_figure(fig, "Fig2_global_signresolved")


def fig3_regional(cohort: pd.DataFrame) -> None:
    world = gpd.read_file(f"zip://{NE / 'ne_50m_admin_0_countries.zip'}")
    rivers = gpd.read_file(f"zip://{NE / 'ne_50m_rivers_lake_centerlines.zip'}")
    regions = [
        ("A  North China Plain", "Recharge-sensitive screening zone", RED, (112.5, 122.5, 33.5, 41.5), ["Beijing", "Tianjin", "Tangshan", "Baoding", "Zhengzhou"]),
        ("B  Punjab / NW India-Pakistan", "Depletion-subsidence audit zone", BLUE, (72, 80.5, 26, 33.5), ["Delhi", "Lahore", "Ludhiana", "Amritsar", "Chandigarh", "Meerut"]),
        ("C  Japan", "High-shaking recharge-side screening belt", RED, (133, 142.5, 33, 40.5), ["Yokohama", "Tokyo", "Nagoya", "Osaka", "Sendai"]),
    ]
    label_offsets = {
        "Beijing": (8, 8),
        "Tianjin": (9, -9),
        "Tangshan": (9, 6),
        "Baoding": (-34, 6),
        "Zhengzhou": (-16, -12),
        "Delhi": (10, -12),
        "Lahore": (-8, 12),
        "Ludhiana": (9, 10),
        "Amritsar": (10, 16),
        "Chandigarh": (10, -10),
        "Meerut": (10, 8),
        "Yokohama": (11, -12),
        "Tokyo": (11, 8),
        "Nagoya": (9, 8),
        "Osaka": (-16, -12),
        "Sendai": (9, 8),
    }
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.7), constrained_layout=True)
    sc = None
    for ax, (title, zone, color, (x0, x1, y0, y1), labels) in zip(axes, regions):
        world.plot(ax=ax, color="#f2efe9", edgecolor="#b9bdc2", linewidth=0.5, zorder=1)
        rivers.plot(ax=ax, color="#9ec9e8", linewidth=0.6, zorder=2)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=color, alpha=0.055, edgecolor=color, lw=1.0, zorder=2.5))
        d = cohort[(cohort.lon >= x0) & (cohort.lon <= x1) & (cohort.lat >= y0) & (cohort.lat <= y1)]
        sizes = 32 + 145 * np.sqrt(d["population"].values / 1.5e7)
        sc = ax.scatter(d.lon, d.lat, c=d["dP"], cmap="RdBu_r", vmin=-0.015, vmax=0.015, s=sizes, edgecolors="#333333", linewidths=0.35, zorder=4)
        material = d["fdr_sig"] & (d["dP"].abs() >= MATERIAL)
        fs = d[d["fdr_sig"]]
        ax.scatter(fs.lon, fs.lat, s=32 + 145 * np.sqrt(fs["population"].values / 1.5e7) + 70, facecolors="none", edgecolors="#111111", linewidths=1.15, zorder=5)
        mh = d[material]
        ax.scatter(mh.lon, mh.lat, s=285, facecolors="none", edgecolors=color, linewidths=2.0, zorder=6)
        for nm in labels:
            r = d[d["name"] == nm]
            if len(r):
                r = r.iloc[0]
                dx, dy = label_offsets.get(nm, (4, 3))
                ax.annotate(nm, (r.lon, r.lat), xytext=(dx, dy), textcoords="offset points", fontsize=7.7, zorder=7, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        ax.text(0.02, 0.96, zone, transform=ax.transAxes, fontsize=8.4, fontweight="bold", color=color, va="top", path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect(1.0 / np.cos(np.radians((y0 + y1) / 2)))
        ax.set_title(title, fontsize=9.9, fontweight="bold", loc="left")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_edgecolor("#888888")
    cb = fig.colorbar(sc, ax=axes, shrink=0.55, pad=0.01, extend="both", location="right")
    cb.set_label("Delta screening index (2015-2024)", fontsize=8.8)
    fig.suptitle("Regional transferability of the groundwater-liquefaction trade-off", fontsize=11.0, fontweight="bold")
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="white",
            markeredgecolor="#222222",
            markeredgewidth=1.1,
            markersize=7.0,
            label="FDR sign-detectable",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="white",
            markeredgecolor=RED,
            markeredgewidth=2.0,
            markersize=8.0,
            label="CSR-material + FDR",
        ),
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0), fontsize=7.4)
    save_figure(fig, "Fig3_regional")


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


def trend_band(x: np.ndarray, y: np.ndarray, xs: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    lr = linregress(x, y)
    yhat = lr.intercept + lr.slope * xs
    resid = y - (lr.intercept + lr.slope * x)
    n = len(x)
    s2 = float(np.sum(resid**2) / max(n - 2, 1))
    sxx = float(np.sum((x - np.mean(x)) ** 2))
    se_mean = np.sqrt(s2 * (1 / n + (xs - np.mean(x)) ** 2 / max(sxx, 1e-9)))
    band = 1.64 * se_mean
    return yhat, yhat - band, yhat + band, float(lr.slope), float(lr.stderr)


def fig4_timeseries() -> None:
    cities = {
        "Beijing": (39.91, 116.40, "Well anchor: Beijing recovery about 1 m/yr in 2016-2024"),
        "Tianjin": (39.13, 117.20, "NCP well network: regional recovery about 0.7 m/yr in 2020-2024"),
        "Delhi": (28.61, 77.21, "CGWB stations: widespread depth-to-water increase"),
        "Lahore": (31.56, 74.35, "Boreholes + GRACE + InSAR: depletion and subsidence"),
    }
    ds = xr.open_dataset(GRACE)
    years = decode_years(ds)
    lwe = ds["lwe_thickness"].values
    lat = ds["lat"].values
    lon = ds["lon"].values
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 6.8), sharex=True)
    for ax, (name, (la, lo, anchor)) in zip(axes.ravel(), cities.items()):
        ix = int(np.abs(lon - (lo % 360)).argmin())
        iy = int(np.abs(lat - la).argmin())
        ts = lwe[:, iy, ix].astype(float)
        ok = np.isfinite(ts)
        ax.plot(years[ok], ts[ok], color="#8d8d8d", lw=0.8, marker="o", ms=2.2, label="GRACE/GRACE-FO TWS anomaly")
        for y0, y1, color, label in [(2003, 2025, "#444444", "full 2003-2024"), (2015, 2025, RED, "recent 2015-2024")]:
            mask = (years >= y0) & (years <= y1) & ok
            if mask.sum() > 10:
                xs = np.linspace(years[mask].min(), years[mask].max(), 80)
                yhat, lo_band, hi_band, slope, stderr = trend_band(years[mask], ts[mask], xs)
                ax.plot(xs, yhat, color=color, lw=2.3 if color == RED else 1.4, ls="-" if color == RED else "--", label=f"{label}: {slope:+.2f} +/- {stderr:.2f} cm/yr")
                if color == RED:
                    ax.fill_between(xs, lo_band, hi_band, color=color, alpha=0.13, lw=0, label="recent 90% trend-fit band")
        ax.axhline(0, color="#cccccc", lw=0.6)
        ax.grid(alpha=0.23)
        ax.set_title(name, fontsize=10, fontweight="bold")
        ax.set_ylabel("TWS anomaly (cm)")
        ax.text(0.02, 0.04, anchor, transform=ax.transAxes, fontsize=7.0, color="#555555", va="bottom")
        ax.legend(fontsize=6.3, loc="best")
    for ax in axes[1]:
        ax.set_xlabel("Year")
    fig.suptitle("GRACE/GRACE-FO trajectories with trend uncertainty and independent evidence anchors", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save_figure(fig, "Fig4_timeseries")
    ds.close()


def fig5_policy_robustness(cohort: pd.DataFrame, grid: pd.DataFrame, envelope: pd.DataFrame, effects: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(14.6, 5.9))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 0.9, 1.45], wspace=0.28)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])

    env = envelope.sort_values("median_dP")
    y = np.arange(len(env))
    ax1.axvspan(-MATERIAL, MATERIAL, color="#f2f2f2", zorder=0)
    ax1.axvline(0, color="#777777", lw=0.8)
    ax1.axvline(MATERIAL, color="#999999", lw=0.7, ls="--")
    ax1.axvline(-MATERIAL, color="#999999", lw=0.7, ls="--")
    for i, (_, r) in enumerate(env.iterrows()):
        color = RED if r["dP"] > 0 else BLUE
        ax1.hlines(i, r["min_dP"], r["max_dP"], color=color, lw=3.0, alpha=0.45)
        ax1.plot(r["median_dP"], i, "o", color=color, ms=4.8)
        ax1.plot(r["dP"], i, "D", color=INK, ms=3.2)
    ax1.set_yticks(y)
    ax1.set_yticklabels([f"{r.name}, {r.country}" for r in env.itertuples()])
    ax1.set_xlabel("Delta P_liq")
    ax1.set_title("a  Screening-unit signs stay stable", loc="left", fontweight="bold")
    ax1.text(0.02, 0.96, "Line: min-max\nCircle: median\nDiamond: baseline", transform=ax1.transAxes, fontsize=7, va="top", color="#555555")

    heat = grid.groupby(["specific_yield", "trend_multiplier"])["n_material_any_direction"].mean().unstack()
    im = ax2.imshow(heat.values, origin="lower", aspect="auto", cmap="YlGnBu")
    ax2.set_xticks(np.arange(len(heat.columns)))
    ax2.set_xticklabels([str(c) for c in heat.columns], rotation=0)
    ax2.set_yticks(np.arange(len(heat.index)))
    ax2.set_yticklabels([str(i) for i in heat.index])
    ax2.set_xlabel("Trend multiplier")
    ax2.set_ylabel("Specific yield")
    ax2.set_title("b  Material count is magnitude-sensitive", loc="left", fontweight="bold")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax2.text(j, i, f"{heat.values[i, j]:.0f}", ha="center", va="center", fontsize=6.5, color=INK)
    cb = fig.colorbar(im, ax=ax2, shrink=0.72, pad=0.02)
    cb.set_label("Mean material cities\n(across k values)", fontsize=7)

    dominant = effects.sort_values("range_mean_hotspot_abs_dP", ascending=False).iloc[0]["parameter"]
    ax2.text(
        0.04,
        0.05,
        f"Largest screening-unit magnitude effect:\n{dominant}",
        transform=ax2.transAxes,
        fontsize=6.8,
        color="#333333",
        bbox=dict(facecolor="white", edgecolor="#dddddd", alpha=0.82, boxstyle="round,pad=0.2"),
    )

    d = cohort.copy()
    sizes = 15 + 80 * np.sqrt(d["population"] / d["population"].max())
    material = d["fdr_sig"] & (d["dP"].abs() >= MATERIAL)
    ax3.scatter(d.loc[~material, "recent_trend_cm_yr"], d.loc[~material, "P0"], s=sizes[~material], c=GREY, alpha=0.42, lw=0, zorder=1)
    inc = material & (d["dP"] > 0)
    dec = material & (d["dP"] < 0)
    ax3.scatter(d.loc[inc, "recent_trend_cm_yr"], d.loc[inc, "P0"], s=sizes[inc] * 1.45, c=RED, edgecolor="black", lw=0.5, zorder=3)
    ax3.scatter(d.loc[dec, "recent_trend_cm_yr"], d.loc[dec, "P0"], s=sizes[dec] * 1.45, c=BLUE, edgecolor="black", lw=0.5, zorder=3)
    ax3.axvline(0, color="#777777", lw=0.8)
    ax3.axhline(0.10, color="#999999", lw=0.7, ls="--")
    ax3.set_xlabel("GRACE/GRACE-FO recent TWS trend (cm yr-1)")
    ax3.set_ylabel("Baseline liquefaction-screening index")
    ax3.set_title("c  Non-regulatory policy triage", loc="left", fontweight="bold")
    ax3.text(0.03, 0.93, "Depletion-side:\nSubsidence +\nwater security audit", color=BLUE, transform=ax3.transAxes, fontsize=7.2, va="top")
    ax3.text(0.66, 0.93, "Recharge-side:\nLiquefaction\nmonitoring", color=RED, transform=ax3.transAxes, fontsize=7.2, va="top")
    ax3.text(0.50, 0.13, "Routine monitoring\nor local follow-up", color="#555555", transform=ax3.transAxes, fontsize=7, ha="center")
    for _, r in d.loc[material].iterrows():
        ax3.annotate(r["name"], (r["recent_trend_cm_yr"], r["P0"]), xytext=(4, 4), textcoords="offset points", fontsize=6.8)
    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=RED, markeredgecolor="black", label="material increase"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE, markeredgecolor="black", label="material decrease"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GREY, label="other screened cities"),
    ]
    ax3.legend(handles=handles, loc="lower right", fontsize=7)
    fig.suptitle("Robustness and policy triage for groundwater-driven liquefaction screening", y=1.02, fontsize=11, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, "Fig5_policy_robustness")


def main() -> None:
    set_style()
    cohort = load_cohort()
    grid, city_grid, envelope, effects = build_supplementary_tables(cohort)
    fig1_mechanism()
    fig2_global_map(cohort)
    fig3_regional(cohort)
    fig4_timeseries()
    fig5_policy_robustness(cohort, grid, envelope, effects)
    print("R19 figure upgrade complete.")
    print("Sensitivity combinations:", len(grid))
    print("Hotspot city-grid rows:", len(city_grid))
    print("Hotspot sign reversals:", int(grid["hotspot_sign_reversals"].sum()))


if __name__ == "__main__":
    main()
