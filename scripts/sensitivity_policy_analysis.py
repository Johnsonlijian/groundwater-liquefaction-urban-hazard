"""Sensitivity, validation-ready policy triage, and Figure 5 for Nature Water.

The script adds three derived products:
  - sensitivity_grid_v2.csv: 150 deterministic parameter combinations
  - hotspot_sensitivity_envelope_v2.csv: sign/magnitude envelope for the six material hotspots
  - policy_priority_table_v2.csv: city-level screening tiers using explicit proxy flags

It also generates Fig5_policy_robustness as PNG/SVG/PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "scripts"))

from zhu2017 import p_liquefaction


MATERIAL = 0.01
NYEARS = 10.0
K_VALUES = [60, 80, 100, 120, 150]
SY_VALUES = [0.05, 0.075, 0.10, 0.15, 0.20, 0.25]
TREND_MULTIPLIERS = [0.5, 0.8, 1.0, 1.2, 1.5]


def load_cohort() -> pd.DataFrame:
    inputs = pd.read_csv(DER / "city_inputs.csv")
    gw = pd.read_csv(DER / "city_gws.csv")
    results = pd.read_csv(DER / "city_results_v2.csv")

    # city_gws is row-aligned with city_inputs in the production workflow.
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


def build_sensitivity_tables(cohort: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hotspots = pd.read_csv(DER / "hotspot_table.csv")
    hot_keys = set(zip(hotspots["name"], hotspots["country"]))
    hot_mask = cohort.apply(lambda r: (r["name"], r["country"]) in hot_keys, axis=1).to_numpy()

    combo_rows = []
    city_rows = []
    for k in K_VALUES:
        for sy in SY_VALUES:
            for mult in TREND_MULTIPLIERS:
                dP = delta_p(cohort, k, sy, mult)
                combo_rows.append(
                    {
                        "pgv_per_pga_k": k,
                        "specific_yield": sy,
                        "trend_multiplier": mult,
                        "mean_dP": float(np.mean(dP)),
                        "median_abs_dP": float(np.median(np.abs(dP))),
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
                for i, row in cohort.loc[hot_mask].reset_index(drop=False).iterrows():
                    city_rows.append(
                        {
                            "name": row["name"],
                            "country": row["country"],
                            "pgv_per_pga_k": k,
                            "specific_yield": sy,
                            "trend_multiplier": mult,
                            "dP": float(dP[row["index"]]),
                        }
                    )

    grid = pd.DataFrame(combo_rows)
    city_grid = pd.DataFrame(city_rows)
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
            np.mean(np.abs(city_grid[(city_grid["name"] == r["name"]) & (city_grid["country"] == r["country"])]["dP"]) >= MATERIAL)
        ),
        axis=1,
    )

    policy = cohort.copy()
    policy["soft_soil_proxy_vs30_le_360"] = policy["vs30"] <= 360
    policy["shallow_wtd_proxy_le_10m"] = policy["wtd"] <= 10
    policy["near_water_proxy_le_5km"] = policy["dw_km"] <= 5
    policy["high_shaking_proxy_pga_ge_0p2g"] = policy["pga_475_g"] >= 0.2
    proxy_cols = [
        "soft_soil_proxy_vs30_le_360",
        "shallow_wtd_proxy_le_10m",
        "near_water_proxy_le_5km",
        "high_shaking_proxy_pga_ge_0p2g",
    ]
    policy["susceptibility_proxy_count"] = policy[proxy_cols].sum(axis=1)

    policy["screening_tier"] = "D routine periodic update"
    policy.loc[policy["fdr_sig"] & (policy["dP"].abs() >= 0.005), "screening_tier"] = "B targeted regional monitoring"
    policy.loc[policy["fdr_sig"] & (policy["dP"].abs() >= MATERIAL), "screening_tier"] = "A material hotspot"
    policy.loc[policy["fdr_sig"] & (policy["dP"].abs() < 0.005), "screening_tier"] = "C detectable but sub-material"
    policy["policy_action"] = "Maintain periodic groundwater and hazard-map updates"
    policy.loc[policy["dP"] > 0, "policy_action"] = "Screen recharge or recovery plans for liquefaction sensitivity"
    policy.loc[policy["dP"] < 0, "policy_action"] = "Assess depletion jointly with subsidence and water-security loss"

    keep = [
        "name",
        "country",
        "lat",
        "lon",
        "population",
        "pga_475_g",
        "vs30",
        "wtd",
        "dw_km",
        "P0",
        "recent_trend_cm_yr",
        "dP",
        "dP_lo",
        "dP_hi",
        "fdr_sig",
        *proxy_cols,
        "susceptibility_proxy_count",
        "screening_tier",
        "policy_action",
    ]
    policy = policy[keep].sort_values(["screening_tier", "dP"], ascending=[True, False])
    return grid, envelope, policy


def make_fig5(cohort: pd.DataFrame, envelope: pd.DataFrame, policy: pd.DataFrame) -> None:
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
    red, blue, green, ink = "#c0392b", "#2c6fbb", "#2e8b57", "#222222"
    fig = plt.figure(figsize=(12.0, 5.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.35], wspace=0.24)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    env = envelope.sort_values("median_dP")
    y = np.arange(len(env))
    colors = [red if v > 0 else blue for v in env["dP"]]
    ax1.axvspan(-MATERIAL, MATERIAL, color="#f2f2f2", zorder=0)
    ax1.axvline(0, color="#777777", lw=0.8)
    ax1.axvline(MATERIAL, color="#999999", lw=0.7, ls="--")
    ax1.axvline(-MATERIAL, color="#999999", lw=0.7, ls="--")
    for i, (_, r) in enumerate(env.iterrows()):
        c = red if r["dP"] > 0 else blue
        ax1.hlines(i, r["min_dP"], r["max_dP"], color=c, lw=3.0, alpha=0.45)
        ax1.plot(r["median_dP"], i, "o", color=c, ms=5.0)
        ax1.plot(r["dP"], i, "D", color=ink, ms=3.4)
    ax1.set_yticks(y)
    ax1.set_yticklabels([f"{r.name}, {r.country}" for r in env.itertuples()])
    ax1.set_xlabel("Delta P_liq across 150 sensitivity combinations")
    ax1.set_title("a  Six hotspot signs do not reverse", loc="left", fontweight="bold")
    ax1.text(
        0.02,
        0.96,
        "Grey band: |Delta P_liq| < 0.01\nLine: min-max; circle: median; diamond: baseline",
        transform=ax1.transAxes,
        fontsize=7,
        va="top",
        color="#555555",
    )

    d = cohort.copy()
    sizes = 15 + 80 * np.sqrt(d["population"] / d["population"].max())
    mat = d["fdr_sig"] & (d["dP"].abs() >= MATERIAL)
    ax2.scatter(
        d.loc[~mat, "recent_trend_cm_yr"],
        d.loc[~mat, "P0"],
        s=sizes[~mat],
        c="#b7bdc3",
        alpha=0.45,
        lw=0,
        zorder=1,
    )
    inc = mat & (d["dP"] > 0)
    dec = mat & (d["dP"] < 0)
    ax2.scatter(
        d.loc[inc, "recent_trend_cm_yr"],
        d.loc[inc, "P0"],
        s=sizes[inc] * 1.4,
        c=red,
        edgecolor="black",
        lw=0.5,
        zorder=3,
    )
    ax2.scatter(
        d.loc[dec, "recent_trend_cm_yr"],
        d.loc[dec, "P0"],
        s=sizes[dec] * 1.4,
        c=blue,
        edgecolor="black",
        lw=0.5,
        zorder=3,
    )
    ax2.axvline(0, color="#777777", lw=0.8)
    ax2.axhline(0.10, color="#999999", lw=0.7, ls="--")
    ax2.set_xlabel("GRACE/GRACE-FO recent TWS trend (cm yr-1)")
    ax2.set_ylabel("Baseline modelled liquefaction probability")
    ax2.set_title("b  Screening matrix for groundwater-management decisions", loc="left", fontweight="bold")
    ax2.text(0.03, 0.93, "depletion:\nsubsidence +\nwater-security audit", color=blue, transform=ax2.transAxes, fontsize=7, va="top")
    ax2.text(0.69, 0.93, "recharge/recovery:\nliquefaction screening\nbefore/while implementing", color=red, transform=ax2.transAxes, fontsize=7, va="top")
    ax2.text(0.50, 0.12, "routine monitoring\nor local follow-up", color="#555555", transform=ax2.transAxes, fontsize=7, ha="center")
    for _, r in d.loc[mat].iterrows():
        ax2.annotate(r["name"], (r["recent_trend_cm_yr"], r["P0"]), xytext=(4, 4), textcoords="offset points", fontsize=6.8)

    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=red, markeredgecolor="black", label="material increase"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=blue, markeredgecolor="black", label="material decrease"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#b7bdc3", label="other screened cities"),
    ]
    ax2.legend(handles=handles, loc="lower right", fontsize=7)
    fig.suptitle("Robustness and policy triage for groundwater-driven liquefaction screening", y=1.02, fontsize=11, fontweight="bold")
    fig.tight_layout()
    for ext, kwargs in {
        "png": {"dpi": 400},
        "svg": {},
        "pdf": {},
    }.items():
        fig.savefig(FIG / f"Fig5_policy_robustness.{ext}", bbox_inches="tight", **kwargs)
    plt.close(fig)


def main() -> None:
    cohort = load_cohort()
    grid, envelope, policy = build_sensitivity_tables(cohort)
    grid.to_csv(DER / "sensitivity_grid_v2.csv", index=False, encoding="utf-8")
    envelope.to_csv(DER / "hotspot_sensitivity_envelope_v2.csv", index=False, encoding="utf-8")
    policy.to_csv(DER / "policy_priority_table_v2.csv", index=False, encoding="utf-8")
    make_fig5(cohort, envelope, policy)
    print("Sensitivity grid rows:", len(grid))
    print("Hotspot sign reversals across grid:", int(grid["hotspot_sign_reversals"].sum()))
    print("Policy table rows:", len(policy))
    print("Saved Fig5_policy_robustness.png/svg/pdf")


if __name__ == "__main__":
    main()
