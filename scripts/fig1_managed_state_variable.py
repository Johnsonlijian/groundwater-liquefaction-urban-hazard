"""Generate the rebuilt Figure 1 mechanism/framework graphic.

The output intentionally uses only evidence-bounded labels. It is a
submission-facing schematic, not a data plot or proof of city-scale attribution.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures"
OUT = ROOT / "paper_figures" / "output"
for folder in [FIG, OUT / "png", OUT / "svg", OUT / "pdf"]:
    folder.mkdir(parents=True, exist_ok=True)


COLORS = {
    "red": "#C94C4C",
    "red_light": "#F7DDDA",
    "blue": "#2F6FB3",
    "blue_light": "#DCEBFA",
    "grey": "#5F6B73",
    "grey_light": "#EEF1F3",
    "dark": "#20262A",
    "gold": "#C98B19",
    "gold_light": "#FFF0CF",
    "green": "#4A9B6E",
    "green_light": "#DFF1E7",
}


def box(ax, xy, w, h, text, fc, ec, fontsize=7.0, weight="normal", radius=0.04, color=None):
    patch = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=1.05,
        edgecolor=ec,
        facecolor=fc,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=color or COLORS["dark"],
        weight=weight,
        linespacing=1.12,
        zorder=3,
    )
    return patch


def arrow(ax, start, end, color, rad=0.0, lw=1.35, text=None, text_xy=None, mutation_scale=11):
    patch = FancyArrowPatch(
        start,
        end,
        connectionstyle=f"arc3,rad={rad}",
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        lw=lw,
        color=color,
        zorder=4,
    )
    ax.add_patch(patch)
    if text:
        ax.text(
            text_xy[0],
            text_xy[1],
            text,
            ha="center",
            va="center",
            fontsize=6.2,
            color=color,
            zorder=5,
        )


def badge(ax, x, y, text, fc, ec, w=0.9, h=0.16, fontsize=5.9):
    return box(ax, (x, y), w, h, text, fc, ec, fontsize=fontsize, radius=0.03)


def draw_water_column(ax, x, y, w, h, color, label):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#F7F7F7", edgecolor="#8A8A8A", lw=0.8, zorder=1))
    ax.add_patch(Rectangle((x, y), w, h * 0.56, facecolor=color, edgecolor="none", alpha=0.30, zorder=1))
    ax.plot([x, x + w], [y + h * 0.56, y + h * 0.56], color=color, lw=1.4, zorder=3)
    ax.add_patch(
        Polygon(
            [[x + w * 0.18, y + h * 0.78], [x + w * 0.5, y + h * 0.93], [x + w * 0.82, y + h * 0.78]],
            closed=True,
            facecolor=color,
            edgecolor=color,
            alpha=0.18,
            zorder=2,
        )
    )
    ax.text(x + w / 2, y - 0.06, label, ha="center", va="top", fontsize=5.8, color=COLORS["dark"])


def main() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.linewidth": 0.8,
        }
    )

    fig, ax = plt.subplots(figsize=(7.45, 4.85))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.2)
    ax.axis("off")

    ax.text(
        0.25,
        5.88,
        "Groundwater management moves a liquefaction-screening state variable",
        fontsize=12,
        weight="bold",
        ha="left",
        va="top",
        color=COLORS["dark"],
    )
    ax.text(
        0.25,
        5.58,
        "Regional storage driver -> water-table perturbation -> modelled probability change -> non-regulatory screening flag",
        fontsize=7.4,
        ha="left",
        va="top",
        color=COLORS["grey"],
    )

    box(ax, (0.35, 4.45), 1.65, 0.62, "Managed recovery\nor recharge", COLORS["red_light"], COLORS["red"], 7.2, "bold")
    box(ax, (0.35, 3.46), 1.65, 0.62, "Depletion or\nabstraction", COLORS["blue_light"], COLORS["blue"], 7.2, "bold")

    box(
        ax,
        (2.55, 3.75),
        1.62,
        0.92,
        "GRACE/GRACE-FO\nregional storage\n~300 km driver",
        COLORS["grey_light"],
        "#9BA5AD",
        6.8,
        "bold",
    )
    badge(ax, 2.65, 3.37, "not a city well", "#FFFFFF", "#B8BFC5", w=1.42)
    badge(ax, 2.65, 3.14, "TWS, not shallow GW alone", "#FFFFFF", "#B8BFC5", w=1.42, fontsize=5.6)

    box(
        ax,
        (4.46, 3.62),
        1.22,
        0.48,
        "Water-table\nlever",
        "#FFFFFF",
        "#9BA5AD",
        6.2,
        "bold",
    )
    draw_water_column(ax, 4.92, 4.28, 0.48, 0.82, COLORS["red"], "shallower")
    draw_water_column(ax, 4.92, 2.96, 0.48, 0.82, COLORS["blue"], "deeper")
    ax.text(5.16, 2.64, "via S_y\nassumption", ha="center", va="top", fontsize=5.7, color=COLORS["grey"])

    box(
        ax,
        (6.25, 3.78),
        1.62,
        0.92,
        "Zhu et al.\nwater-table term\nonly term perturbed",
        "#FFFFFF",
        "#87919A",
        6.8,
        "bold",
    )
    ax.text(
        7.06,
        3.45,
        "All other predictors fixed:\nVs30, shaking, precipitation,\ndistance to water",
        ha="center",
        va="top",
        fontsize=5.8,
        color=COLORS["grey"],
        linespacing=1.10,
    )

    box(
        ax,
        (8.35, 4.48),
        1.52,
        0.56,
        "Delta P_liq > 0\nscreening increase",
        COLORS["red_light"],
        COLORS["red"],
        6.25,
        "bold",
    )
    box(
        ax,
        (8.35, 3.36),
        1.52,
        0.56,
        "Delta P_liq < 0\nbut subsidence risk",
        COLORS["blue_light"],
        COLORS["blue"],
        6.2,
        "bold",
    )
    box(
        ax,
        (8.25, 2.36),
        1.62,
        0.62,
        "Screening-\npriority flag",
        COLORS["green_light"],
        COLORS["green"],
        6.8,
        "bold",
    )

    arrow(ax, (2.02, 4.76), (2.52, 4.39), COLORS["red"], rad=-0.15, text="+ storage", text_xy=(2.34, 4.86))
    arrow(ax, (2.02, 3.77), (2.52, 4.02), COLORS["blue"], rad=0.15, text="- storage", text_xy=(2.33, 3.49))
    arrow(ax, (4.18, 4.20), (4.88, 4.84), COLORS["red"], rad=0.08)
    arrow(ax, (4.18, 4.03), (4.88, 3.30), COLORS["blue"], rad=-0.08)
    arrow(ax, (5.70, 4.02), (6.24, 4.23), COLORS["grey"], mutation_scale=10)
    arrow(ax, (7.88, 4.28), (8.33, 4.75), COLORS["red"], rad=0.1)
    arrow(ax, (7.88, 4.06), (8.33, 3.63), COLORS["blue"], rad=-0.1)
    arrow(ax, (9.05, 4.45), (9.05, 2.99), COLORS["red"], rad=0.0, lw=1.0, mutation_scale=9)
    arrow(ax, (9.05, 3.36), (9.05, 2.99), COLORS["blue"], rad=0.0, lw=1.0, mutation_scale=9)

    ax.text(0.35, 2.47, "Evidence ladder used in this paper", fontsize=7.7, weight="bold", color=COLORS["dark"])
    ladder = [
        ("NCP / Beijing", "well + model anchor", COLORS["red"], COLORS["red_light"]),
        ("Punjab / Delhi / Lahore", "depletion + subsidence", COLORS["blue"], COLORS["blue_light"]),
        ("Tokyo Bay / Yokohama", "official rise sign", COLORS["red"], COLORS["red_light"]),
        ("Mumbai-Bhayandar", "candidate only", COLORS["gold"], COLORS["gold_light"]),
        ("JPL CRI", "auth boundary", COLORS["gold"], COLORS["gold_light"]),
    ]
    x0 = 0.35
    for i, (region, status, ec, fc) in enumerate(ladder):
        x = x0 + i * 1.86
        box(ax, (x, 1.52), 1.63, 0.42, region, fc, ec, 5.95, "bold", radius=0.03)
        box(ax, (x, 1.05), 1.63, 0.36, status, "#FFFFFF", ec, 5.25, "normal", radius=0.025)

    box(
        ax,
        (0.35, 0.36),
        9.52,
        0.42,
        "Claim boundary: regional screening and triage, not site-specific engineering prediction or earthquake causation",
        "#FFFFFF",
        "#B8BFC5",
        6.4,
        "bold",
        radius=0.035,
    )

    for label, xy in [
        ("a", (0.22, 5.12)),
        ("b", (2.42, 4.83)),
        ("c", (4.34, 5.18)),
        ("d", (6.14, 4.86)),
        ("e", (8.12, 5.12)),
    ]:
        ax.text(xy[0], xy[1], label, fontsize=8.2, weight="bold", color=COLORS["dark"])

    for target in [
        FIG / "Fig1_mechanism",
        OUT / "png" / "Fig1_managed_state_variable",
    ]:
        fig.savefig(target.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(FIG / "Fig1_mechanism.svg", bbox_inches="tight")
    fig.savefig(FIG / "Fig1_mechanism.pdf", bbox_inches="tight")
    fig.savefig(OUT / "svg" / "Fig1_managed_state_variable.svg", bbox_inches="tight")
    fig.savefig(OUT / "pdf" / "Fig1_managed_state_variable.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
