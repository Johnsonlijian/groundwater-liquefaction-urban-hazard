"""R28 specific-yield threshold and policy-triage sensitivity.

This script turns the broad S_y uncertainty statement into a reproducible
threshold diagnostic. It does not assign new local aquifer priors. Instead, it
answers a reviewer-facing question: for each screening unit, what S_y would be
needed for the observed storage trend to cross |Delta P_liq| >= 0.01?

Outputs:
  data_derived/specific_yield_thresholds_r28.csv
  data_derived/specific_yield_scenarios_r28.csv
  data_derived/specific_yield_region_summary_r28.csv
  figures/Fig5_policy_robustness.png/svg/pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
sys.path.insert(0, str(ROOT / "scripts"))

from zhu2017 import p_liquefaction


MATERIAL = 0.01
NYEARS = 10.0
SY_GRID = np.array([0.05, 0.075, 0.10, 0.15, 0.20, 0.25])
SY_MIN, SY_MAX = 0.05, 0.25
K = 100.0


def load_cohort() -> pd.DataFrame:
    inputs = pd.read_csv(DER / "city_inputs.csv")
    gw = pd.read_csv(DER / "city_gws.csv")
    results = pd.read_csv(DER / "city_results_v2.csv")
    inputs = inputs.copy()
    inputs["recent_trend_cm_yr"] = gw["recent_trend_cm_yr"].values
    keys = ["name", "country", "lat", "lon"]
    out = results.merge(inputs, on=keys, suffixes=("", "_input"), validate="one_to_one")
    out["P0"] = p_liquefaction(
        K * out["pga_475_g"],
        out["vs30"],
        out["precip"],
        out["dw_km"],
        out["wtd"],
    )
    return out


def delta_p(row: pd.Series, sy: float) -> float:
    trend = float(row["recent_trend_cm_yr"])
    dwtd = -(trend * NYEARS / 100.0) / sy
    p0 = p_liquefaction(
        K * row["pga_475_g"],
        row["vs30"],
        row["precip"],
        row["dw_km"],
        row["wtd"],
    )
    p1 = p_liquefaction(
        K * row["pga_475_g"],
        row["vs30"],
        row["precip"],
        row["dw_km"],
        max(float(row["wtd"]) + dwtd, 0.0),
    )
    return float(p1 - p0)


def threshold_sy(row: pd.Series) -> float | None:
    """Largest S_y in [0.05, 0.25] that still crosses the material threshold."""
    vals = {sy: abs(delta_p(row, sy)) for sy in SY_GRID}
    if vals[SY_MIN] < MATERIAL:
        return None
    if vals[SY_MAX] >= MATERIAL:
        return SY_MAX

    lo, hi = SY_MIN, SY_MAX
    for _ in range(60):
        mid = (lo + hi) / 2
        if abs(delta_p(row, mid)) >= MATERIAL:
            lo = mid
        else:
            hi = mid
    return lo


def build_tables(cohort: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hotspots = pd.read_csv(DER / "hotspot_table.csv")
    trigger = pd.read_csv(DER / "water_table_trigger_r20.csv")
    keep_names = hotspots[["name", "country"]].drop_duplicates()
    context = pd.DataFrame(
        [
            {"name": "Beijing", "country": "CN"},
            {"name": "Tokyo", "country": "JP"},
            {"name": "Tianjin", "country": "CN"},
        ]
    )
    units = pd.concat([keep_names, context], ignore_index=True)
    available = cohort[["name", "country"]].drop_duplicates()
    units = units.merge(available, on=["name", "country"], how="inner").drop_duplicates()

    rows = []
    scenario_rows = []
    for _, key in units.iterrows():
        row = cohort[(cohort["name"] == key["name"]) & (cohort["country"] == key["country"])].iloc[0]
        tr = trigger[(trigger["name"] == key["name"]) & (trigger["country"] == key["country"])]
        sy_thr = threshold_sy(row)
        scenario = "screening unit"
        if key["name"] == "Beijing":
            scenario = "mechanism anchor"
        elif key["name"] in {"Tokyo", "Tianjin"}:
            scenario = "regional context"
        interpretation = (
            "mechanism-validation anchor; sub-material in global screen"
            if key["name"] == "Beijing"
            else "material only for local S_y values at or below threshold"
        )
        if key["name"] in {"Tokyo", "Tianjin"} and sy_thr is not None:
            interpretation = "regional-context screen; material only at low S_y"
        elif key["name"] in {"Tokyo", "Tianjin"}:
            interpretation = "regional-context screen; sub-material across tested S_y range"
        if sy_thr == SY_MAX:
            interpretation = "material across the tested S_y range"
        elif sy_thr is None and key["name"] != "Beijing":
            interpretation = "sub-material across the tested S_y range"
        rows.append(
            {
                "name": row["name"],
                "country": row["country"],
                "role": scenario,
                "direction": "increase" if row["dP"] > 0 else "decrease",
                "regional_setting": regional_setting(row["name"]),
                "recent_tws_cm_yr": row["recent_trend_cm_yr"],
                "baseline_dP_sy010": row["dP"],
                "dP_sy005": delta_p(row, 0.05),
                "dP_sy010": delta_p(row, 0.10),
                "dP_sy025": delta_p(row, 0.25),
                "sy_material_threshold": sy_thr,
                "water_table_rise_trigger_m_for_plus0p01": float(
                    tr["water_table_rise_trigger_m_for_plus0p01"].iloc[0]
                )
                if len(tr)
                else np.nan,
                "interpretation": interpretation,
            }
        )
        for sy in SY_GRID:
            scenario_rows.append(
                {
                    "name": row["name"],
                    "country": row["country"],
                    "role": scenario,
                    "regional_setting": regional_setting(row["name"]),
                    "direction": "increase" if row["dP"] > 0 else "decrease",
                    "specific_yield": sy,
                    "dP": delta_p(row, sy),
                    "material": abs(delta_p(row, sy)) >= MATERIAL,
                }
            )

    thresh = pd.DataFrame(rows)
    scenarios = pd.DataFrame(scenario_rows)
    region = (
        scenarios[scenarios["role"] == "screening unit"]
        .groupby(["regional_setting", "specific_yield", "direction"], dropna=False)
        .agg(n_units=("name", "count"), n_material=("material", "sum"), median_abs_dP=("dP", lambda x: float(np.median(np.abs(x)))))
        .reset_index()
    )
    return thresh, scenarios, region


def regional_setting(name: str) -> str:
    if name in {"Yokohama", "Tokyo", "Beijing", "Tianjin"}:
        return "recharge-side validation"
    if name in {"Mumbai", "Bhayandar"}:
        return "western India candidate"
    return "Punjab depletion"


def label_name(name: str) -> str:
    return {
        "Bhayandar": "Mumbai-\nBhayandar",
        "Yokohama": "Tokyo Bay/\nYokohama",
        "Ludhiana": "Ludhiana",
        "Lahore": "Lahore",
        "Delhi": "Delhi",
        "Mumbai": "Mumbai",
        "Beijing": "Beijing\n(anchor)",
        "Tokyo": "Tokyo\n(context)",
        "Tianjin": "Tianjin\n(context)",
    }.get(name, name)


def make_fig5(thresh: pd.DataFrame, scenarios: pd.DataFrame) -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
        }
    )
    red = "#c84c4c"
    blue = "#2f6fb3"
    gold = "#b77a00"
    green = "#2f8f63"
    grey = "#737b83"
    ink = "#20262b"

    fig = plt.figure(figsize=(13.4, 6.8))
    gs = fig.add_gridspec(
        2,
        3,
        width_ratios=[1.42, 0.76, 0.76],
        height_ratios=[1.0, 0.9],
        wspace=0.32,
        hspace=0.38,
    )
    ax_a = fig.add_subplot(gs[:, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[1, 1:])

    order = ["Delhi", "Lahore", "Ludhiana", "Mumbai", "Bhayandar", "Yokohama", "Beijing"]
    y = np.arange(len(order))
    ax_a.axvline(0, color="#7d858c", lw=0.8)
    ax_a.axvspan(-MATERIAL, MATERIAL, color="#f1f2f3", zorder=0)
    ax_a.axvline(-MATERIAL, color="#9da4aa", ls="--", lw=0.8)
    ax_a.axvline(MATERIAL, color="#9da4aa", ls="--", lw=0.8)
    for yi, name in zip(y, order):
        s = scenarios[scenarios["name"] == name].sort_values("specific_yield")
        c = red if float(s["dP"].median()) > 0 else blue
        if name in {"Mumbai", "Bhayandar"}:
            c = gold
        if name == "Beijing":
            c = green
        ax_a.plot(s["dP"], np.repeat(yi, len(s)), "-", color=c, lw=3.2, alpha=0.35)
        ax_a.scatter(s["dP"], np.repeat(yi, len(s)), s=28, color=c, edgecolor="white", lw=0.5, zorder=3)
        base = thresh.loc[thresh["name"] == name, "baseline_dP_sy010"].iloc[0]
        ax_a.scatter([base], [yi], marker="D", s=38, color=ink, edgecolor="white", lw=0.5, zorder=4)
    ax_a.set_yticks(y)
    ax_a.set_yticklabels([label_name(n) for n in order])
    ax_a.set_xlabel("Modelled screening increment, Delta P_liq")
    ax_a.set_title("a  Region-specific S_y scenarios: sign stable, materiality variable", loc="left", fontweight="bold")
    ax_a.text(
        0.02,
        0.98,
        "Dots: S_y = 0.05, 0.075, 0.10, 0.15, 0.20, 0.25\nDiamond: baseline S_y = 0.10; grey band: |Delta P_liq| < 0.01",
        transform=ax_a.transAxes,
        va="top",
        fontsize=7,
        color="#56616b",
    )

    th = thresh.set_index("name").loc[order].reset_index()
    vals = [v if pd.notna(v) else 0 for v in th["sy_material_threshold"]]
    colors = []
    for name in th["name"]:
        if name in {"Delhi", "Lahore", "Ludhiana"}:
            colors.append(blue)
        elif name in {"Mumbai", "Bhayandar"}:
            colors.append(gold)
        elif name == "Beijing":
            colors.append(green)
        else:
            colors.append(red)
    ax_b.barh(np.arange(len(th)), vals, color=colors, alpha=0.83)
    ax_b.axvline(0.10, color=ink, lw=0.9, ls="-", label="baseline S_y")
    ax_b.axvline(0.25, color="#9da4aa", lw=0.7, ls="--")
    ax_b.set_yticks(np.arange(len(th)))
    ax_b.set_yticklabels(
        [label_name(n).replace("\n", " ").replace("- ", "-").replace("/ ", "/") for n in th["name"]],
        fontsize=7,
    )
    ax_b.set_xlim(0, 0.27)
    ax_b.set_xlabel("Largest S_y retaining |Delta P_liq| >= 0.01")
    ax_b.set_title("b  Unit-specific S_y materiality threshold", loc="left", fontweight="bold")
    for i, (_, r) in enumerate(th.iterrows()):
        txt = "never" if pd.isna(r["sy_material_threshold"]) else f"{r['sy_material_threshold']:.2f}"
        ax_b.text(min(vals[i] + 0.006, 0.255), i, txt, va="center", fontsize=7, color="#2b2f33")

    rise_vals = th["water_table_rise_trigger_m_for_plus0p01"].fillna(0.0).to_numpy()
    ax_c.barh(np.arange(len(th)), rise_vals, color=colors, alpha=0.78)
    ax_c.set_yticks(np.arange(len(th)))
    ax_c.set_yticklabels([])
    ax_c.set_xlim(0, max(5.0, float(np.nanmax(rise_vals)) * 1.08))
    ax_c.set_xlabel("Rise needed (m)")
    ax_c.set_title("c  Water-table rise needed for +0.01 Delta P_liq", loc="left", fontweight="bold")
    for i, v in enumerate(rise_vals):
        ax_c.text(v + 0.08, i, f"{v:.1f}", va="center", fontsize=7, color="#2b2f33")

    ax_d.axis("off")
    ax_d.set_title("d  Non-regulatory water-management screen", loc="left", fontweight="bold")
    boxes = [
        (0.02, 0.58, 0.28, 0.28, "Storage rises", "local wells +\ncoastal check", red),
        (0.37, 0.58, 0.28, 0.28, "If seismic +\nsoft/shallow", "screening increment\nand S_y threshold", grey),
        (0.72, 0.58, 0.26, 0.28, "Follow-up", "geotechnical wells,\nsediment, emergency plan", green),
        (0.02, 0.12, 0.28, 0.28, "Storage falls", "subsidence +\nwater security", blue),
        (0.37, 0.12, 0.28, 0.28, "Do not count as\nsafety gain", "multi-hazard audit", grey),
        (0.72, 0.12, 0.26, 0.28, "Update screen", "regional driver,\ncity exposure unit", green),
    ]
    for x, y0, w, h, title, body, color in boxes:
        patch = FancyBboxPatch(
            (x, y0),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            transform=ax_d.transAxes,
            ec=color,
            fc=color + "18",
            lw=1.4,
        )
        ax_d.add_patch(patch)
        ax_d.text(x + w / 2, y0 + h * 0.68, title, transform=ax_d.transAxes, ha="center", va="center", fontweight="bold", color=ink)
        ax_d.text(x + w / 2, y0 + h * 0.31, body, transform=ax_d.transAxes, ha="center", va="center", fontsize=7, color="#4c555d")
    for y0 in [0.72, 0.26]:
        ax_d.annotate("", xy=(0.36, y0), xytext=(0.31, y0), xycoords=ax_d.transAxes, arrowprops=dict(arrowstyle="-|>", color="#6b737b", lw=1.1))
        ax_d.annotate("", xy=(0.71, y0), xytext=(0.66, y0), xycoords=ax_d.transAxes, arrowprops=dict(arrowstyle="-|>", color="#6b737b", lw=1.1))

    fig.suptitle(
        "Specific-yield sensitivity separates sign from materiality",
        y=1.02,
        fontsize=11,
        fontweight="bold",
    )
    for ext, kwargs in {"png": {"dpi": 400}, "svg": {}, "pdf": {}}.items():
        fig.savefig(FIG / f"Fig5_policy_robustness.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def main() -> None:
    cohort = load_cohort()
    thresh, scenarios, region = build_tables(cohort)
    thresh.to_csv(DER / "specific_yield_thresholds_r28.csv", index=False)
    scenarios.to_csv(DER / "specific_yield_scenarios_r28.csv", index=False)
    region.to_csv(DER / "specific_yield_region_summary_r28.csv", index=False)
    make_fig5(thresh, scenarios)
    print(thresh[["name", "direction", "baseline_dP_sy010", "sy_material_threshold", "interpretation"]].to_string(index=False))
    print("Saved R28 specific-yield tables and Fig5_policy_robustness.")


if __name__ == "__main__":
    main()
