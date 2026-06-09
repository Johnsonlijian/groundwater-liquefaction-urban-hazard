"""R41 Article-specific regional hierarchy and evidence-ladder figures.

R40 showed that historical-event inventories are useful as a boundary check,
but do not justify a broad "dynamic update improves event prediction" claim.
R41 therefore strengthens the honest Article identity: a regional, evidence-
tiered screen and data product rather than a city hazard map.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
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


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def build_regional_hierarchy() -> pd.DataFrame:
    groups = pd.read_csv(DER / "regional_followup_groups_r36.csv")
    groups = groups.copy()
    groups["dominant_direction"] = np.where(
        groups["n_increase_side"] > groups["n_depletion_side"],
        "increase-side",
        np.where(groups["n_depletion_side"] > groups["n_increase_side"], "depletion-side", "mixed"),
    )
    groups["direction_coherence_fraction"] = groups[["n_increase_side", "n_depletion_side"]].max(axis=1) / groups[
        "n_point_city_units"
    ].clip(lower=1)
    groups["material_fraction_within_group"] = groups["n_material_units"] / groups["n_point_city_units"].clip(lower=1)
    groups["inference_unit"] = "300-km regional storage group"
    groups["exposure_unit"] = "city point / metropolitan marker"
    groups["safe_interpretation"] = (
        "regional follow-up group; city names are exposure locators, not independent hydrological discoveries"
    )
    out_cols = [
        "grace_scale_cluster_300km",
        "inference_unit",
        "exposure_unit",
        "n_point_city_units",
        "n_metro_clusters_50km",
        "n_countries",
        "n_increase_side",
        "n_depletion_side",
        "dominant_direction",
        "direction_coherence_fraction",
        "n_material_units",
        "material_fraction_within_group",
        "population_million_sum",
        "mean_abs_delta_p",
        "max_abs_delta_p",
        "representative_names",
        "safe_interpretation",
    ]
    result = groups[out_cols].sort_values(["n_point_city_units", "max_abs_delta_p"], ascending=[False, False])
    result.to_csv(DER / "regional_hierarchical_evidence_model_r41.csv", index=False)
    return result


def make_regional_hierarchy_figure(hierarchy: pd.DataFrame) -> None:
    configure()
    zero = json.loads((DER / "zero_aware_fdr_summary_r27.json").read_text(encoding="utf-8"))
    r31 = json.loads((DER / "static_observed_triage_tier_summary_r31.json").read_text(encoding="utf-8"))
    r33 = pd.read_csv(DER / "independence_scale_counts_r33.csv")
    row = r33[
        (r33["method"] == "BH zero-aware")
        & (r33["abs_delta_p_threshold"] == 0.005)
    ].iloc[0]

    funnel = pd.DataFrame(
        [
            ("Seismic city exposure units", 444),
            ("Zero-aware detectable units", int(zero["zero_aware_bh_significant"])),
            ("A/B follow-up point cities", int(r31["bh_ab_followup_units"])),
            ("50-km metro clusters", int(row["n_50km_metro_clusters"])),
            ("GHSL urban centres", int(row["n_ghsl_urban_centres"])),
            ("300-km regional groups", int(row["n_300km_regional_groups"])),
        ],
        columns=["stage", "count"],
    )

    fig = plt.figure(figsize=(11.2, 5.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1.35])
    ax = fig.add_subplot(gs[0, 0])
    y = np.arange(len(funnel))
    colors = ["#bdbdbd", "#9ecae1", "#74c476", "#fdae6b", "#c7b9d6", "#756bb1"]
    ax.barh(y, funnel["count"], color=colors, edgecolor="white")
    for yi, count in zip(y, funnel["count"]):
        ax.text(count + 8, yi, f"{count}", va="center", ha="left", fontsize=8, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(funnel["stage"])
    ax.invert_yaxis()
    ax.set_xlabel("Number of units")
    ax.set_title("a  From city exposure to regional inference", loc="left", fontweight="bold")
    ax.set_xlim(0, 470)

    ax = fig.add_subplot(gs[0, 1])
    top = hierarchy.head(10).copy()
    top = top.sort_values("n_point_city_units")
    yy = np.arange(len(top))
    color_map = {"increase-side": "#b24a3b", "depletion-side": "#356c9c", "mixed": "#8c6bb1"}
    colors = [color_map[d] for d in top["dominant_direction"]]
    ax.barh(yy, top["n_point_city_units"], color=colors)
    ylabels = []
    for yi, row2 in zip(yy, top.itertuples(index=False)):
        ylabels.append(f"{row2.representative_names.split(';')[0].strip()} group")
        ax.text(
            row2.n_point_city_units + 0.2,
            yi,
            f"{row2.n_point_city_units} cities, {row2.n_material_units} material",
            va="center",
            ha="left",
            fontsize=7,
        )
    ax.set_yticks(yy)
    ax.set_yticklabels(ylabels)
    ax.set_xlabel("Point-city exposure units in 300-km group")
    ax.set_title("b  Regional groups carry the storage interpretation", loc="left", fontweight="bold")
    ax.set_xlim(0, max(top["n_point_city_units"]) + 6)
    handles = [
        plt.Line2D([0], [0], marker="s", color="none", markerfacecolor=color_map[k], markersize=7)
        for k in ["increase-side", "depletion-side", "mixed"]
    ]
    ax.legend(handles, ["Increase-side", "Depletion-side", "Mixed"], frameon=False, loc="lower right")
    fig.suptitle("Hierarchical regional screen: exposure markers are nested inside GRACE-scale groups",
                 x=0.02, ha="left", fontweight="bold", fontsize=12)
    for ext in [".svg", ".pdf", ".png"]:
        fig.savefig(FIG / f"Fig3_regional_hierarchical_screen_article{ext}", dpi=600 if ext == ".png" else None, bbox_inches="tight")
    plt.close(fig)


def evidence_ladder_table() -> pd.DataFrame:
    rows = [
        ("NCP / Beijing", "Sign+", "Sign", "Sign", "Sign", "Auth boundary", "High mechanism", "Mechanism anchor"),
        ("Tokyo Bay / Yokohama", "Material", "Sign", "Sign", "Sign", "Auth boundary", "Rising wells", "Sign-supported coastal case"),
        ("Mumbai / Bhayandar", "Material", "Weak sign", "Sign", "Sign", "Auth boundary", "Contradicts recovery", "Candidate-only boundary"),
        ("Delhi", "Material", "Material", "Sign", "Sign", "Auth boundary", "Depletion", "Product-material depletion"),
        ("Lahore / Punjab", "Material", "Near/sign", "Sign", "Sign", "Auth boundary", "Borehole + InSAR", "Regional depletion review"),
    ]
    columns = ["regional_card", "CSR", "GSFC", "GFZ raw", "GFZ leakage", "JPL CRI", "Local", "Claim class"]
    ladder = pd.DataFrame(rows, columns=columns)
    ladder.to_csv(DER / "four_product_evidence_ladder_r41.csv", index=False)
    return ladder


def make_evidence_ladder_figure(ladder: pd.DataFrame) -> None:
    configure()
    cols = ["CSR", "GSFC", "GFZ raw", "GFZ leakage", "JPL CRI", "Local"]
    status_color = {
        "Material": "#2166ac",
        "Sign+": "#67a9cf",
        "Sign": "#67a9cf",
        "Near/sign": "#92c5de",
        "Weak sign": "#d9d9d9",
        "Auth boundary": "#fddbc7",
        "High mechanism": "#1b7837",
        "Rising wells": "#5aae61",
        "Contradicts recovery": "#b2182b",
        "Depletion": "#4393c3",
        "Borehole + InSAR": "#5aae61",
    }
    fig, ax = plt.subplots(figsize=(11.2, 5.5))
    ax.axis("off")
    ax.text(0.02, 0.98, "Four-product evidence ladder and local boundary", fontsize=12, fontweight="bold", va="top")
    left = 0.22
    top = 0.84
    cell_w = 0.105
    cell_h = 0.115
    for j, col in enumerate(cols):
        ax.text(left + j * cell_w + cell_w / 2, top + 0.055, col, ha="center", va="center", fontsize=8, fontweight="bold")
    for i, row in ladder.iterrows():
        y = top - i * cell_h
        ax.text(0.02, y, row["regional_card"], ha="left", va="center", fontsize=8, fontweight="bold")
        for j, col in enumerate(cols):
            val = row[col]
            color = status_color.get(val, "#eeeeee")
            rect = FancyBboxPatch(
                (left + j * cell_w, y - 0.037),
                cell_w * 0.92,
                0.074,
                boxstyle="round,pad=0.004,rounding_size=0.008",
                facecolor=color,
                edgecolor="#666666",
                linewidth=0.45,
                transform=ax.transAxes,
            )
            ax.add_patch(rect)
            text_color = "white" if val not in {"Auth boundary", "Weak sign"} else "#333333"
            ax.text(left + j * cell_w + cell_w * 0.46, y, val, ha="center", va="center", fontsize=6.6, color=text_color)
        ax.text(0.86, y, row["Claim class"], ha="left", va="center", fontsize=7.4, color="#333333")
    ax.text(0.86, top + 0.055, "Claim class", ha="left", va="center", fontsize=8, fontweight="bold")
    ax.text(
        0.02,
        0.09,
        "JPL CRI is an official PO.DAAC product but remains an authentication boundary in this run. "
        "The ladder tiers claims; it does not turn regional storage into city-scale groundwater heads.",
        fontsize=7.5,
        color="#555555",
        ha="left",
    )
    for ext in [".svg", ".pdf", ".png"]:
        fig.savefig(FIG / f"Fig4_four_product_evidence_ladder_article{ext}", dpi=600 if ext == ".png" else None, bbox_inches="tight")
    plt.close(fig)


def readiness_dashboard(hierarchy: pd.DataFrame, ladder: pd.DataFrame) -> dict:
    metrics = pd.read_csv(DER / "event_hindcast_metrics_r40.csv")
    positive_delta = int((metrics["delta_auc_dynamic_minus_static"] > 0).sum())
    neutral_or_negative_delta = int((metrics["delta_auc_dynamic_minus_static"] <= 0).sum())
    score_rows = [
        ("Article identity", 16, "Article package exists; central claim now framed as DGLS framework."),
        ("Evidence robustness", 17, "CSR/GSFC/GFZ plus JPL access ledger; JPL not numerically ingested."),
        ("Event benchmark", 10, f"{positive_delta} events improve AUC; {neutral_or_negative_delta} are neutral or worse."),
        ("Aquifer S_y module", 14, "Aquifer-context priors and phase diagram completed; local calibration remains future replacement."),
        ("Regional hierarchy", 14, "City markers nested to 50-km, GHSL and 300-km groups; table and figure completed."),
        ("Data product", 8, "Named local release exists; Zenodo DOI pending."),
        ("Figure storyline", 9, "Article-level figure set assembled; final visual polish still possible."),
    ]
    dashboard = pd.DataFrame(score_rows, columns=["module", "score", "reason"])
    dashboard["max_score"] = [20, 20, 20, 15, 15, 10, 10]
    dashboard["fraction"] = dashboard["score"] / dashboard["max_score"]
    dashboard.to_csv(DER / "article_readiness_dashboard_r41.csv", index=False)
    summary = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "article_readiness_score": int(dashboard["score"].sum()),
        "article_readiness_max": int(dashboard["max_score"].sum()),
        "n_regional_hierarchy_rows": int(len(hierarchy)),
        "n_evidence_ladder_rows": int(len(ladder)),
        "event_benchmark_interpretation": (
            "The event-inventory benchmark is neutral/negative for broad event-prediction improvement; "
            "therefore it is used as a claim boundary, not as proof of dynamic model superiority."
        ),
    }
    (DER / "article_readiness_summary_r41.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    DER.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    hierarchy = build_regional_hierarchy()
    ladder = evidence_ladder_table()
    make_regional_hierarchy_figure(hierarchy)
    make_evidence_ladder_figure(ladder)
    summary = readiness_dashboard(hierarchy, ladder)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
