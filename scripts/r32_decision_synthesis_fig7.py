"""R32 decision-synthesis figure for the Nature Water submission.

This script keeps the R23 product-consensus evidence boundary visible, but
turns Fig. 7 into a closing decision figure rather than a pure robustness
ledger. It uses only already-derived tables.

Outputs:
- figures/Fig7_ghsl_gsfc_robustness.{png,svg,pdf}
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
MATERIAL = 0.01


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7.5,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def card(ax, xy, wh, title, body, face, edge="#d0d0d0", title_color="#202020") -> None:
    x, y = xy
    w, h = wh
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.02",
        linewidth=0.8,
        facecolor=face,
        edgecolor=edge,
        transform=ax.transAxes,
    )
    ax.add_patch(box)
    wrapped = "\n\n".join(textwrap.fill(part, width=46) for part in body.split("\n\n"))
    ax.text(x + 0.025, y + h - 0.055, title, transform=ax.transAxes, fontsize=8.0, weight="bold", color=title_color, va="top")
    ax.text(x + 0.025, y + h - 0.13, wrapped, transform=ax.transAxes, fontsize=6.3, color="#3a3a3a", va="top", linespacing=1.08)


def make_figure() -> None:
    configure()
    red = "#c7362f"
    blue = "#2f6fb3"
    gold = "#d89c24"
    gray = "#d9d9d9"
    ink = "#202020"

    consensus = pd.read_csv(DER / "product_consensus_hotspots_r23.csv")
    r31 = json.loads((DER / "static_observed_triage_tier_summary_r31.json").read_text(encoding="utf-8"))
    r33 = json.loads((DER / "statistical_object_audit_summary_r33.json").read_text(encoding="utf-8"))
    counts = pd.read_csv(DER / "static_observed_triage_tier_counts_r31.csv")

    fig = plt.figure(figsize=(7.25, 9.1), dpi=240)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.35, 1.1, 2.1], hspace=0.34)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])
    ax2 = fig.add_subplot(gs[2])
    fig.suptitle("Evidence boundary and decision endpoint for static-screen correction", fontsize=12.5, weight="bold", y=0.985)

    # Panel a: keep the independent-product guardrail, but compact it.
    ordered = consensus.sort_values("csr_dP").reset_index(drop=True)
    y = np.arange(len(ordered))
    colors = np.where(ordered["csr_dP"] > 0, red, blue)
    ax0.barh(y, ordered["csr_dP"], color=colors, alpha=0.86, height=0.62, label="CSR screen")
    ax0.scatter(
        ordered["gsfc_recent_dP"],
        y,
        marker="D",
        s=34,
        color="white",
        edgecolor=ink,
        lw=0.85,
        zorder=5,
        label="GSFC check",
    )
    ax0.axvline(0, color=ink, lw=0.8)
    ax0.axvline(MATERIAL, color="#777777", lw=0.7, ls="--")
    ax0.axvline(-MATERIAL, color="#777777", lw=0.7, ls="--")
    labels = []
    for _, row in ordered.iterrows():
        if row["name"] == "Yokohama":
            labels.append("Tokyo Bay/Yokohama")
        elif row["name"] in {"Mumbai", "Bhayandar"}:
            labels.append(row["name"])
        elif row["name"] == "Delhi":
            labels.append("Delhi")
        elif row["name"] == "Lahore":
            labels.append("Lahore")
        else:
            labels.append("Ludhiana")
    ax0.set_yticks(y, labels)
    ax0.set_xlabel("Cumulative Delta screening index")
    ax0.set_title("a Independent-product guardrail: sign is supported, materiality is bounded", loc="left", weight="bold")
    ax0.legend(loc="lower right", fontsize=7)
    ax0.grid(True, axis="x", color="#e6e6e6", lw=0.5)
    ax0.set_axisbelow(True)
    ax0.text(
        0.01,
        -0.27,
        "CSR defines the primary screen; GSFC retains all six signs, four at p < 0.05; only Delhi remains GSFC-material.",
        transform=ax0.transAxes,
        fontsize=7,
        color="#555555",
    )

    # Panel b: static-counterfactual payload.
    ax1.axis("off")
    ax1.set_title("b Static-counterfactual payload: most detectable updates remain small", loc="left", weight="bold", pad=4)
    bh = counts[counts["method"] == "BH zero-aware"].set_index("tier")
    d_count = int(bh.loc["D static-routine baseline", "n_point_city_units"])
    c_count = int(bh.loc["C detectable sub-material update", "n_point_city_units"])
    b_count = int(bh.loc["B targeted follow-up", "n_point_city_units"])
    a_count = int(bh.loc["A material adjustment", "n_point_city_units"])
    total = a_count + b_count + c_count + d_count
    parts = [
        ("D routine", d_count, "#efefef"),
        ("C detectable", c_count, "#b7d3e8"),
        ("B targeted", b_count, gold),
        ("A material", a_count, "#9f2f2b"),
    ]
    x0 = 0.03
    y0 = 0.58
    width = 0.94
    left = x0
    for label, value, color in parts:
        w = width * value / total
        ax1.add_patch(FancyBboxPatch((left, y0), w, 0.18, boxstyle="round,pad=0.004,rounding_size=0.012", facecolor=color, edgecolor="white", transform=ax1.transAxes))
        if w > 0.08:
            ax1.text(left + w / 2, y0 + 0.09, f"{label}\n{value}", transform=ax1.transAxes, ha="center", va="center", fontsize=7, color=ink)
        else:
            tag = "B=22" if label.startswith("B") else "A=6"
            x_mid = left + w / 2
            x_label = x_mid - 0.015 if label.startswith("B") else x_mid + 0.014
            ax1.text(x_label, y0 - 0.055, tag, transform=ax1.transAxes, ha="center", va="top", fontsize=6.4, color=ink)
            ax1.plot([x_mid, x_label], [y0 - 0.01, y0 - 0.045], transform=ax1.transAxes, color="#777777", lw=0.45)
        left += w
    ax1.text(0.03, 0.36, f"A/B follow-up units: {r31['bh_ab_followup_units']} under BH ({r31['bh_a_material_units']} material, {r31['bh_b_targeted_units']} targeted)", transform=ax1.transAxes, fontsize=8.4, weight="bold", color=ink)
    groups = r33["ab_followup_bh_threshold_0p005"]
    ax1.text(
        0.03,
        0.22,
        f"Direction split: {r31['bh_ab_increase_side']} increase-side and {r31['bh_ab_depletion_side']} depletion-side; "
        f"{groups['n_50km_metro_clusters']} metro clusters, {groups['n_ghsl_urban_centres']} GHSL centres, "
        f"{groups['n_300km_regional_groups']} regional groups.",
        transform=ax1.transAxes,
        fontsize=7.5,
        color="#555555",
    )
    ax1.text(0.03, 0.08, f"BY sensitivity retains {r31['by_ab_followup_units']} A/B units. Tiers are follow-up flags, not engineering hazard classes.", transform=ax1.transAxes, fontsize=7.2, color="#555555")

    # Panel c: decision endpoint.
    ax2.axis("off")
    ax2.set_title("c Water-management decision endpoint", loc="left", weight="bold", pad=4)
    card(
        ax2,
        (0.03, 0.54),
        (0.43, 0.34),
        "Recharge-side correction",
        "Recovery, transfer or managed recharge can shoal the water table and raise the screening increment.\n\nFollow-up: local wells, susceptible sediments and liquefaction response.",
        "#f8e3df",
        edge="#d9aaa4",
        title_color=red,
    )
    card(
        ax2,
        (0.54, 0.54),
        (0.43, 0.34),
        "Depletion-side paradox",
        "Falling storage can lower the metric while worsening subsidence and water-security risk.\n\nFollow-up: audit subsidence, lifelines and water supply.",
        "#dfeaf7",
        edge="#9fb9d9",
        title_color=blue,
    )
    card(
        ax2,
        (0.16, 0.12),
        (0.68, 0.22),
        "Common endpoint",
        "Use GRACE/GRACE-FO as a regional trigger. Replace the static water-table assumption with local hydrogeology before engineering design.",
        "#f3f3f3",
        edge="#cfcfcf",
        title_color=ink,
    )
    ax2.annotate("", xy=(0.49, 0.42), xytext=(0.30, 0.53), xycoords=ax2.transAxes, textcoords=ax2.transAxes, arrowprops=dict(arrowstyle="->", lw=1.1, color="#777777"))
    ax2.annotate("", xy=(0.51, 0.42), xytext=(0.70, 0.53), xycoords=ax2.transAxes, textcoords=ax2.transAxes, arrowprops=dict(arrowstyle="->", lw=1.1, color="#777777"))

    for ext in ["png", "svg", "pdf"]:
        fig.savefig(FIG / f"Fig7_ghsl_gsfc_robustness.{ext}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    make_figure()
    print("Saved R32 decision-synthesis Fig7.")
