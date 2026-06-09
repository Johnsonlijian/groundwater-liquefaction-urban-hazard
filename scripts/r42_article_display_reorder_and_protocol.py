"""R42 Nature Water Article display-order and protocol products.

This round fixes an Article-storyline problem: the historical-event benchmark
is useful as a boundary test, but placing a neutral/negative benchmark as
Figure 2 makes the manuscript read defensive. R42 therefore builds:

1. Figure 2: global null plus regional review payload.
2. Figure 3 alias: regional evidence cards.
3. Figure 6: engineering-context enrichment plus event-scale boundary.
4. Box/Table 1: non-regulatory groundwater-liquefaction review protocol.

The script does not create new scientific claims. It rearranges verified R27,
R31, R33, R37, R40 and R41 products into an Article-facing display sequence.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd
from pyproj import Transformer

try:
    import geopandas as gpd
except Exception:  # pragma: no cover - fallback keeps the script runnable.
    gpd = None


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
NE = ROOT / "data_raw" / "naturalearth"
MATERIAL = 0.01


COLORS = {
    "increase": "#c43b3b",
    "depletion": "#2d69b3",
    "neutral": "#6f7782",
    "gold": "#c9972b",
    "ink": "#1f2933",
    "muted": "#69717a",
    "pale_blue": "#edf4fb",
    "pale_red": "#fbefef",
    "pale_gold": "#fbf4dd",
    "pale_grey": "#f4f6f8",
}


def save_all(fig: plt.Figure, stem: str) -> None:
    out = FIG / stem
    for ext in [".svg", ".pdf", ".png"]:
        fig.savefig(out.with_suffix(ext), dpi=600 if ext == ".png" else None, bbox_inches="tight")
    plt.close(fig)


def load_payload_counts() -> dict[str, int | float | str]:
    refined = json.loads((DER / "core_summary_refined.json").read_text(encoding="utf-8"))
    fdr = json.loads((DER / "zero_aware_fdr_summary_r27.json").read_text(encoding="utf-8"))
    tiers = json.loads((DER / "static_observed_triage_tier_summary_r31.json").read_text(encoding="utf-8"))
    counts = pd.read_csv(DER / "independence_scale_counts_r33.csv")
    row = counts[(counts["method"] == "BH zero-aware") & (counts["abs_delta_p_threshold"] == 0.005)].iloc[0]
    return {
        "n_cities": int(refined["n_clean"]),
        "mean_dp": float(refined["clean_recent"]["mean_dP"]),
        "null_p": float(refined["null_recent"]["p"]),
        "detectable": int(fdr["zero_aware_bh_significant"]),
        "ab": int(tiers["bh_ab_followup_units"]),
        "material": int(tiers["bh_a_material_units"]),
        "targeted": int(tiers["bh_b_targeted_units"]),
        "metro": int(row["n_50km_metro_clusters"]),
        "ghsl": int(row["n_ghsl_urban_centres"]),
        "regional": int(row["n_300km_regional_groups"]),
        "largest_group": int(row["largest_300km_group_n_point_cities"]),
        "increase_ab": int(tiers["bh_ab_increase_side"]),
        "depletion_ab": int(tiers["bh_ab_depletion_side"]),
        "ab_pop": float(tiers["bh_ab_population_million"]),
    }


def draw_funnel(ax: plt.Axes, counts: dict[str, int | float | str]) -> None:
    stages = [
        ("Seismic urban\nexposure units", counts["n_cities"], "#dce8f5"),
        ("Directionally\ndetectable", counts["detectable"], "#e9edf5"),
        ("A/B follow-up\npoint units", counts["ab"], "#f8e5df"),
        ("50-km metro\nclusters", counts["metro"], "#f9efdc"),
        ("GHSL urban\ncentres", counts["ghsl"], "#eef5e8"),
        ("300-km regional\ngroups", counts["regional"], "#e5edf8"),
    ]
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    y = 0.89
    widths = np.linspace(0.92, 0.46, len(stages))
    for i, ((label, value, color), width) in enumerate(zip(stages, widths)):
        x0 = 0.5 - width / 2
        box = FancyBboxPatch(
            (x0, y - 0.05),
            width,
            0.10,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            fc=color,
            ec="#8a929b",
            lw=0.8,
        )
        ax.add_patch(box)
        ax.text(x0 + 0.025, y, label, ha="left", va="center", fontsize=7.5, color=COLORS["ink"], linespacing=0.9)
        ax.text(x0 + width - 0.025, y, f"{int(value)}", ha="right", va="center", fontsize=14, fontweight="bold", color=COLORS["ink"])
        if i < len(stages) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (0.5, y - 0.058),
                    (0.5, y - 0.113),
                    arrowstyle="-|>",
                    mutation_scale=9,
                    lw=0.9,
                    color="#89919b",
                )
            )
        y -= 0.137
    ax.text(
        0.05,
        0.018,
        "Interpretation scale contracts from city exposure markers to GRACE-scale regional groups.",
        fontsize=7.2,
        color=COLORS["muted"],
        ha="left",
    )


def make_global_payload_figure() -> None:
    counts = load_payload_counts()
    fig = plt.figure(figsize=(11.3, 6.9), constrained_layout=False)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.45, 1.0], height_ratios=[0.82, 1.08], wspace=0.11, hspace=0.14)

    ax_map = fig.add_subplot(gs[:, 0])
    ax_map.set_axis_off()
    if draw_vector_global_map(ax_map):
        pass
    elif (img_path := FIG / "Fig2_global_signresolved.png").exists():
        img = plt.imread(img_path)
        ax_map.imshow(img)
        ax_map.set_title("a  Global sign-resolved screen", loc="left", fontsize=11, fontweight="bold", pad=8)
    else:
        frame = pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv")
        ax_map.scatter(frame["lon"], frame["lat"], s=18, c="#9099a3", alpha=0.65, lw=0)
        ax_map.set_xlim(-180, 180)
        ax_map.set_ylim(-60, 80)
        ax_map.set_xlabel("Longitude")
        ax_map.set_ylabel("Latitude")
        ax_map.set_title("a  Global sign-resolved screen", loc="left", fontsize=11, fontweight="bold", pad=8)

    ax_null = fig.add_subplot(gs[0, 1])
    ax_null.set_axis_off()
    ax_null.set_xlim(0, 1)
    ax_null.set_ylim(0, 1)
    ax_null.set_title("b  Global null, regional payload", loc="left", fontsize=11, fontweight="bold", pad=8)
    cards = [
        ("Global mean Delta P_liq", f"{counts['mean_dp']:+.5f}", COLORS["pale_grey"], COLORS["neutral"]),
        ("Geographic null", f"p = {counts['null_p']:.2f}", COLORS["pale_grey"], COLORS["neutral"]),
        ("A/B follow-up population", f"{counts['ab_pop']:.1f}M", COLORS["pale_gold"], COLORS["gold"]),
    ]
    for i, (label, value, fill, color) in enumerate(cards):
        y = 0.78 - i * 0.22
        box = FancyBboxPatch((0.04, y - 0.075), 0.92, 0.15, boxstyle="round,pad=0.014,rounding_size=0.018", fc=fill, ec="#a2aab2", lw=0.8)
        ax_null.add_patch(box)
        ax_null.text(0.08, y + 0.025, label, fontsize=8.5, color=COLORS["muted"], ha="left", va="center")
        ax_null.text(0.92, y - 0.005, value, fontsize=16, fontweight="bold", color=color, ha="right", va="center")
    ax_null.text(
        0.04,
        0.12,
        "No diffuse global-amplification narrative is supported;\nreview need emerges after regional grouping.",
        fontsize=8.3,
        color=COLORS["ink"],
        ha="left",
        va="bottom",
    )

    ax_funnel = fig.add_subplot(gs[1, 1])
    ax_funnel.set_title("c  Evidence contraction", loc="left", fontsize=11, fontweight="bold", pad=4)
    draw_funnel(ax_funnel, counts)

    fig.suptitle("Global cancellation hides a regional groundwater-liquefaction review payload", x=0.03, y=0.99, ha="left", fontsize=14, fontweight="bold")
    save_all(fig, "Fig2_global_payload_article")


def draw_vector_global_map(ax: plt.Axes) -> bool:
    """Draw a vector global map panel; return False if required assets are absent."""
    if gpd is None:
        return False
    world_path = NE / "ne_110m_admin_0_countries.zip"
    if not world_path.exists():
        return False
    try:
        world = gpd.read_file(f"zip://{world_path}").to_crs("ESRI:54030")
    except Exception:
        return False

    cohort = pd.read_csv(DER / "city_results_v2.csv")
    zero = pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv")[
        ["name", "country", "material_bh_zero_aware", "fdr_bh_zero_aware"]
    ]
    d = cohort.merge(zero, on=["name", "country"], how="left")
    tr = Transformer.from_crs("EPSG:4326", "ESRI:54030", always_xy=True)
    d["X"], d["Y"] = tr.transform(d["lon"].values, d["lat"].values)
    material = d["material_bh_zero_aware"].fillna(False).astype(bool)

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
    ax.scatter(mh["X"], mh["Y"], s=260, facecolors="none", edgecolors="black", linewidths=1.35, zorder=4)
    ax.scatter(
        mh["X"],
        mh["Y"],
        s=58,
        c=np.where(mh["dP"] > 0, COLORS["increase"], COLORS["depletion"]),
        edgecolors="black",
        linewidths=0.45,
        zorder=5,
    )
    for _, r in mh.iterrows():
        if r["name"] != "Yokohama":
            continue
        ax.annotate(
            r["name"],
            (r["X"], r["Y"]),
            xytext=(16, 12),
            textcoords="offset points",
            fontsize=7.2,
            arrowprops=dict(arrowstyle="-", color="#333333", lw=0.6),
            path_effects=[pe.withStroke(linewidth=2.4, foreground="white")],
            zorder=6,
        )

    inset = ax.inset_axes([0.49, 0.10, 0.35, 0.40])
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
    inset.scatter(south_m["X"], south_m["Y"], s=95, facecolors="none", edgecolors="#111111", linewidths=1.15, zorder=4)
    inset.scatter(
        south_m["X"],
        south_m["Y"],
        s=32,
        c=np.where(south_m["dP"] > 0, COLORS["increase"], COLORS["depletion"]),
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
    inset.set_title("South Asia detail", fontsize=6.3, fontweight="bold", pad=4)
    inset.set_xticks([])
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor("#555555")
        spine.set_linewidth(0.55)

    cb = ax.figure.colorbar(sc, ax=ax, shrink=0.62, pad=0.01, extend="both")
    cb.set_label("Delta screening index\nfrom storage-derived WTD correction, 2015-2024", fontsize=8.0)
    for p, lab in [(1e6, "1M"), (5e6, "5M"), (15e6, "15M")]:
        ax.scatter([], [], s=10 + 95 * np.sqrt(p / d["population"].max()), c="#9aa0a6", edgecolors="k", linewidths=0.25, label=lab)
    ax.legend(title="City population", loc="lower left", fontsize=7.0, title_fontsize=7.2, labelspacing=0.9)
    ax.set_title("a  Global sign-resolved screen", loc="left", fontsize=11, fontweight="bold", pad=8)
    ax.text(
        0.5,
        -0.035,
        "Mean |Delta P_liq| = 0.00124; null p = 1.00.\nRinged cities are exposure locators; inference is regional.",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.2,
        color="#555555",
    )
    ax.set_axis_off()
    return True


def make_regional_cards_alias() -> None:
    for ext in [".svg", ".pdf", ".png"]:
        src = FIG / f"Fig4_evidence_tier_cards_article{ext}"
        dst = FIG / f"Fig3_regional_evidence_cards_article{ext}"
        if src.exists():
            shutil.copy2(src, dst)


def make_engineering_event_boundary_figure() -> None:
    enrich = pd.read_csv(DER / "engineering_susceptibility_enrichment_r37.csv")
    metrics = pd.read_csv(DER / "event_hindcast_metrics_r40.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.1), gridspec_kw={"width_ratios": [1.05, 1.0]})
    ax = axes[0]
    proxy_order = [
        "soft_soil_proxy_vs30_le_360",
        "near_water_proxy_le_5km",
        "susceptibility_proxy_count_ge_2",
        "susceptibility_proxy_count_ge_3",
        "shallow_wtd_proxy_le_10m",
        "high_shaking_proxy_pga_ge_0p2g",
    ]
    label_map = {
        "soft_soil_proxy_vs30_le_360": "Low Vs30",
        "near_water_proxy_le_5km": "Near water",
        "susceptibility_proxy_count_ge_2": ">=2 proxies",
        "susceptibility_proxy_count_ge_3": ">=3 proxies",
        "shallow_wtd_proxy_le_10m": "Shallow WTD",
        "high_shaking_proxy_pga_ge_0p2g": "High PGA",
    }
    keep = enrich[enrich["proxy"].isin(proxy_order)].copy()
    keep["order"] = keep["proxy"].map({p: i for i, p in enumerate(proxy_order)})
    keep = keep.sort_values("order")
    keep["short"] = keep["proxy"].map(label_map)
    x = np.arange(len(keep))
    width = 0.36
    ax.bar(x - width / 2, keep["followup_fraction_with_proxy"], width=width, color="#466f9f", label="A/B follow-up")
    ax.bar(x + width / 2, keep["cohort_fraction_with_proxy"], width=width, color="#c8d3df", label="Full cohort")
    for i, p in enumerate(keep["fisher_greater_p"]):
        if p < 0.001:
            star = "***"
        elif p < 0.01:
            star = "**"
        elif p < 0.05:
            star = "*"
        else:
            star = "n.s."
        ax.text(i, max(keep.iloc[i]["followup_fraction_with_proxy"], keep.iloc[i]["cohort_fraction_with_proxy"]) + 0.04, star, ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, 1.15)
    ax.set_xticks(x)
    ax.set_xticklabels(keep["short"], rotation=32, ha="right", fontsize=8)
    ax.set_ylabel("Fraction of units with proxy")
    ax.set_title("a  Follow-up units concentrate in susceptible settings", loc="left", fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(axis="y", color="#e3e8ef", lw=0.7)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    metrics = metrics.copy()
    order = ["tohoku_2011", "wenchuan_2008", "nepal_2015", "puerto_rico_2020"]
    metrics["order"] = metrics["event_key"].map({k: i for i, k in enumerate(order)})
    metrics = metrics.sort_values("order")
    labels = ["Tohoku\n2011", "Wenchuan\n2008", "Nepal\n2015", "Puerto Rico\n2020"]
    dx = metrics["delta_auc_dynamic_minus_static"].astype(float).to_numpy()
    db = metrics["delta_brier_dynamic_minus_static"].astype(float).to_numpy()
    x = np.arange(len(metrics))
    ax.axhline(0, color="#5f6670", lw=0.8)
    ax.bar(x - 0.17, dx * 1000, width=0.34, color="#3f6fa3", label="Delta AUC x 1000")
    ax.bar(x + 0.17, -db * 1000, width=0.34, color="#d0a94e", alpha=0.85, label="-Delta Brier x 1000")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Scaled change; positive is better")
    ax.set_title("b  Event inventories delimit prediction claims", loc="left", fontsize=10.5, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(axis="y", color="#e3e8ef", lw=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(
        0.02,
        0.03,
        "Boundary result: regional storage anomalies do not substitute for local\npre-event groundwater, sediment and event shaking inputs.",
        transform=ax.transAxes,
        fontsize=8,
        color=COLORS["ink"],
        ha="left",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", fc="#f6f7f9", ec="#ccd3da", lw=0.6),
    )

    fig.suptitle("Engineering context supports review flags; event benchmark protects the claim boundary", x=0.02, y=1.02, ha="left", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    save_all(fig, "Fig6_engineering_event_boundary_article")


def build_protocol_table() -> pd.DataFrame:
    rows = [
        {
            "step": 1,
            "review_step": "Eligibility screen",
            "required_evidence": "Seismic urban basin, susceptible ground proxy, water-management action or observed storage change.",
            "decision_output": "Routine update or enter dynamic groundwater review.",
        },
        {
            "step": 2,
            "review_step": "Storage-direction check",
            "required_evidence": "Regional GRACE/GRACE-FO sign and, where available, local well or InSAR sign.",
            "decision_output": "Recharge-side, depletion-side, mixed or contradicted evidence class.",
        },
        {
            "step": 3,
            "review_step": "Screening-magnitude phase",
            "required_evidence": "Delta P_liq tier, uncertainty, FDR status and aquifer-context S_y prior.",
            "decision_output": "A material, B targeted, C detectable or D routine follow-up class.",
        },
        {
            "step": 4,
            "review_step": "Coastal and leakage guardrail",
            "required_evidence": "Independent mascon products, leakage diagnostics, coastline/reclamation context and JPL CRI status if authenticated.",
            "decision_output": "Product-material, sign-supported, candidate-only or contradicted guardrail.",
        },
        {
            "step": 5,
            "review_step": "Local hydrogeology replacement",
            "required_evidence": "Observation wells, aquifer class, confined/unconfined setting, pumping/recharge records and local S_y estimate.",
            "decision_output": "Replace regional storage prior or keep as screening-only cue.",
        },
        {
            "step": 6,
            "review_step": "Geotechnical translation",
            "required_evidence": "CPT/SPT, boreholes, young alluvium, reclaimed/fill ground, distance to water and historical liquefaction evidence.",
            "decision_output": "Local liquefaction assessment need; no engineering design value is inferred from DGLS alone.",
        },
        {
            "step": 7,
            "review_step": "Governance action",
            "required_evidence": "Water-security objective, subsidence risk, seismic exposure and local-data readiness.",
            "decision_output": "Monitoring, targeted data collection, local geotechnical review or multi-hazard audit.",
        },
    ]
    df = pd.DataFrame(rows)
    df.to_csv(DER / "review_protocol_box1_r42.csv", index=False)
    md_lines = [
        "| Step | Review step | Required evidence | Decision output |",
        "|---:|---|---|---|",
    ]
    for r in rows:
        md_lines.append(f"| {r['step']} | {r['review_step']} | {r['required_evidence']} | {r['decision_output']} |")
    (DER / "review_protocol_box1_r42.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return df


def write_summary(protocol: pd.DataFrame) -> None:
    counts = load_payload_counts()
    summary = {
        "round": "R42",
        "purpose": "Nature Water Article display-order repair and protocol foregrounding",
        "new_or_updated_figures": [
            "figures/Fig2_global_payload_article.{svg,pdf,png}",
            "figures/Fig3_regional_evidence_cards_article.{svg,pdf,png}",
            "figures/Fig6_engineering_event_boundary_article.{svg,pdf,png}",
        ],
        "new_protocol_table": "data_derived/review_protocol_box1_r42.csv",
        "display_sequence": [
            "Figure 1 dynamic groundwater review screen",
            "Figure 2 global null plus regional review payload",
            "Figure 3 regional evidence cards",
            "Figure 4 four-product evidence ladder",
            "Figure 5 aquifer-context S_y phase diagram",
            "Figure 6 engineering context plus event-scale boundary",
            "Table/Box 1 non-regulatory review protocol",
        ],
        "global_payload_counts": counts,
        "protocol_steps": int(len(protocol)),
        "claim_boundary": "Historical-event benchmark remains neutral-to-negative and is used to delimit, not validate, event prediction.",
        "remaining_human_or_auth_boundaries": [
            "Zenodo DOI publication",
            "GitHub release/archive DOI publication",
            "Earthdata-authenticated JPL CRI NetCDF ingestion",
            "funding, CRediT and competing-interest statements",
            "external collaborator decisions",
        ],
    }
    (DER / "article_display_reorder_summary_r42.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main() -> None:
    FIG.mkdir(exist_ok=True)
    DER.mkdir(exist_ok=True)
    make_global_payload_figure()
    make_regional_cards_alias()
    make_engineering_event_boundary_figure()
    protocol = build_protocol_table()
    write_summary(protocol)


if __name__ == "__main__":
    main()
