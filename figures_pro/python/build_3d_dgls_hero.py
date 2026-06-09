"""Build a code-generated 3D DGLS mechanism hero figure.

This is an editable/vector-first mechanism candidate for Figure 1 or a
graphical abstract. It is generated from code, not from AI image synthesis.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "export"
SVG_DIR = OUT / "svg"
PDF_DIR = OUT / "pdf"
PNG_DIR = OUT / "png_600dpi"
for d in [SVG_DIR, PDF_DIR, PNG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

NAVY = "#081B4A"
BLUE = "#2467AE"
TEAL = "#2F9EB0"
CYAN = "#7BD1F2"
CORAL = "#C84C3A"
GREEN = "#2E7D3A"
AMBER = "#F2B84B"
BROWN = "#9B6842"
SOIL = "#C28B59"
PALE = "#F4F8FC"
GREY = "#5E6A7D"
LIGHT = "#E8EEF6"


def cuboid(origin, size):
    x, y, z = origin
    dx, dy, dz = size
    v = np.array([
        [x, y, z], [x + dx, y, z], [x + dx, y + dy, z], [x, y + dy, z],
        [x, y, z + dz], [x + dx, y, z + dz], [x + dx, y + dy, z + dz], [x, y + dy, z + dz],
    ])
    return [
        [v[j] for j in [0, 1, 2, 3]],
        [v[j] for j in [4, 5, 6, 7]],
        [v[j] for j in [0, 1, 5, 4]],
        [v[j] for j in [1, 2, 6, 5]],
        [v[j] for j in [2, 3, 7, 6]],
        [v[j] for j in [3, 0, 4, 7]],
    ]


def add_cuboid(ax, origin, size, color, edge="#5D6B7A", alpha=1.0, lw=0.7):
    faces = cuboid(origin, size)
    pc = Poly3DCollection(faces, facecolors=color, edgecolors=edge, linewidths=lw, alpha=alpha)
    ax.add_collection3d(pc)
    return pc


def add_card(ax, xy, wh, title, body, color, badge):
    x, y = xy
    w, h = wh
    box = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.018,rounding_size=0.04",
        transform=ax.transAxes, facecolor="white", edgecolor=color, linewidth=1.6,
    )
    ax.add_patch(box)
    circ = patches.Circle((x + 0.055, y + h - 0.085), 0.036, transform=ax.transAxes, facecolor=color, edgecolor="white", linewidth=1.4)
    ax.add_patch(circ)
    ax.text(x + 0.055, y + h - 0.095, badge, transform=ax.transAxes, color="white", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(x + 0.105, y + h - 0.06, title, transform=ax.transAxes, color=NAVY, ha="left", va="top", fontsize=12.5, fontweight="bold")
    ax.text(x + 0.105, y + h - 0.122, body, transform=ax.transAxes, color=GREY, ha="left", va="top", fontsize=8.8, linespacing=1.12)


def build():
    rng = np.random.default_rng(42)
    fig = plt.figure(figsize=(16, 9), facecolor=PALE)
    fig.text(0.5, 0.965, "DYNAMIC GROUNDWATER SCREEN FOR LIQUEFACTION REVIEW", ha="center", va="top", color=NAVY, fontsize=25, fontweight="bold")
    fig.text(0.5, 0.925, "3D mechanism candidate: regional storage perturbs only the water-table term; city-level use remains a review cue", ha="center", va="top", color=NAVY, fontsize=12.5, style="italic")

    ax = fig.add_axes([0.025, 0.11, 0.63, 0.80], projection="3d")
    ax.set_facecolor(PALE)
    ax.view_init(elev=24, azim=-58)
    ax.set_box_aspect((10, 6, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.45, 6)
    ax.set_zlim(0, 5.2)
    ax.set_axis_off()

    # Basin block: saturated mass, side faces, green urban surface.
    add_cuboid(ax, (0, 0, 0), (10, 6, 2.6), BROWN, "#6E482F", 0.96, 0.9)
    top = [[0, 0, 2.6], [10, 0, 2.6], [10, 6, 2.6], [0, 6, 2.6]]
    ax.add_collection3d(Poly3DCollection([top], facecolors="#789D64", edgecolors="#4F6E43", linewidths=1.1, alpha=1.0))
    front = [[0, 0, 0], [10, 0, 0], [10, 0, 2.6], [0, 0, 2.6]]
    ax.add_collection3d(Poly3DCollection([front], facecolors="#111111", edgecolors="#6E482F", linewidths=0.7, alpha=0.72))

    # Dynamic water table: old static assumption and observed regional update.
    xs = np.linspace(0.3, 9.7, 28)
    ys = np.linspace(0.25, 5.65, 18)
    X, Y = np.meshgrid(xs, ys)
    Z = 1.22 + 0.07 * X + 0.12 * np.sin(Y * 1.15)
    ax.plot_surface(X, Y, Z, rstride=1, cstride=1, color=CYAN, alpha=0.46, linewidth=0, shade=True)
    X2, Y2 = np.meshgrid(np.linspace(0.3, 9.7, 10), np.linspace(0.25, 5.65, 6))
    Z2 = np.full_like(X2, 1.65)
    ax.plot_wireframe(X2, Y2, Z2, color="#DDE8F2", linewidth=0.9, linestyle="--", alpha=0.9)

    # Make the cut face legible even after 3D occlusion.
    fx = np.linspace(0.45, 9.55, 48)
    fz = 1.05 + 0.085 * fx + 0.10 * np.sin(fx * 0.7)
    ax.plot(fx, np.full_like(fx, -0.08), fz, color="#DDF7FF", linewidth=5.0, alpha=0.92)
    ax.plot(fx, np.full_like(fx, -0.10), np.full_like(fx, 1.65), color="#DDE8F2", linewidth=2.2, linestyle="--", alpha=0.78)

    # Sediment grains and pore-pressure bubbles.
    ax.scatter(rng.uniform(0.4, 9.5, 85), rng.uniform(-0.15, 0.75, 85), rng.uniform(0.15, 1.05, 85),
               s=rng.uniform(12, 42, 85), color="#D9B28C", edgecolor="#7B5132", linewidth=0.35, alpha=0.95)
    bubble_x = np.linspace(4.2, 8.9, 18)
    bubble_y = np.full_like(bubble_x, -0.12)
    bubble_z = 0.55 + 0.16 * (bubble_x - 4.2)
    ax.scatter(bubble_x, bubble_y, bubble_z, s=np.linspace(18, 54, len(bubble_x)), color="#E9FCFF", edgecolor="#4EAFD0", linewidth=0.7, alpha=0.95)

    # City blocks.
    for i, (x, y, h, c) in enumerate([(1.5, 2.1, 1.0, "#D5E1EE"), (2.35, 2.5, 1.55, "#C3D5E8"), (3.25, 2.0, 1.25, "#B8CDE2"), (4.5, 2.9, 1.85, "#DCE6F0"), (5.5, 2.1, 1.1, "#CADBED")]):
        add_cuboid(ax, (x, y, 2.6), (0.45, 0.42, h), c, "#6C7D91", 1.0, 0.55)

    # 3D arrows: recharge and depletion.
    ax.quiver(2.2, 5.1, 4.8, 0, 0, -1.55, color=CORAL, arrow_length_ratio=0.18, linewidth=3.0)
    ax.text(1.25, 5.35, 4.9, "managed recharge\nshallower WTD\nΔP_liq ↑", color=CORAL, fontsize=10.8, fontweight="bold")
    ax.quiver(7.9, 5.1, 4.8, 0, 0, -1.45, color=BLUE, arrow_length_ratio=0.18, linewidth=3.0)
    ax.text(7.1, 5.35, 4.9, "depletion\ndeeper WTD\nΔP_liq ↓", color=BLUE, fontsize=10.8, fontweight="bold")
    ax.text(4.1, 0.05, 1.55, "observed regional water-table update", color="#0E5D8F", fontsize=11, fontweight="bold")
    ax.text(0.2, 0.10, 2.05, "static WTD assumption", color="#DDE8F2", fontsize=9.5, fontweight="bold")

    # Overlay satellite and claim boundary.
    sat = patches.Circle((0.095, 0.815), 0.058, transform=fig.transFigure, facecolor="#1F4D83", edgecolor="#D6E7FF", linewidth=1.8)
    fig.patches.append(sat)
    fig.text(0.095, 0.822, "GRACE /\nGRACE-FO", color="white", fontsize=10.5, fontweight="bold", ha="center", va="center")
    fig.text(0.139, 0.786, "300-km storage trajectory", color="white", fontsize=9.5, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.36", facecolor=TEAL, edgecolor=TEAL))
    fig.text(0.04, 0.13, "Mechanism boundary: regional driver, exposure-unit flag, not an engineering design threshold.",
             color=NAVY, fontsize=11.2, fontweight="bold")

    # Right evidence-and-use panel.
    axr = fig.add_axes([0.66, 0.12, 0.31, 0.78])
    axr.set_axis_off()
    panel = patches.FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.022,rounding_size=0.04",
                                   transform=axr.transAxes, facecolor="white", edgecolor="#A9BCD6", linewidth=1.6)
    axr.add_patch(panel)
    axr.text(0.06, 0.94, "DGLS framework", transform=axr.transAxes, color=NAVY, fontsize=17, fontweight="bold", va="top")
    axr.text(0.06, 0.895, "Dynamic Groundwater-Liquefaction Screening", transform=axr.transAxes, color=GREY, fontsize=10.5, va="top")

    add_card(axr, (0.06, 0.705), (0.88, 0.15), "Observed storage trajectory", "CSR / GSFC / GFZ / JPL-CRI products\nwith local wells where available", TEAL, "1")
    add_card(axr, (0.06, 0.515), (0.88, 0.15), "Aquifer-class conversion", "ΔWTD = storage trend / S_y\nmateriality is aquifer-conditioned", AMBER, "2")
    add_card(axr, (0.06, 0.325), (0.88, 0.15), "Published liquefaction screen", "Only the water-table term is perturbed;\nall other predictors remain fixed", CORAL, "3")
    add_card(axr, (0.06, 0.135), (0.88, 0.15), "Non-regulatory local review", "A/B/C/D classes trigger local wells,\nCPT/SPT and sediment review", GREEN, "4")

    # Guardrail strip.
    strip = patches.FancyBboxPatch((0.67, 0.025), 0.30, 0.055, boxstyle="round,pad=0.012,rounding_size=0.018",
                                   transform=fig.transFigure, facecolor="#EEF5FF", edgecolor="#B8C8DD", linewidth=1.2)
    fig.patches.append(strip)
    fig.text(0.685, 0.052, "Global null retained; regional bidirectional review cue only", color=NAVY, fontsize=10.5, fontweight="bold", va="center")

    name = "GraphicalAbstract_3D_DGLS_mechanism_hero"
    fig.savefig(SVG_DIR / f"{name}.svg", bbox_inches="tight")
    fig.savefig(PDF_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(PNG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return name


if __name__ == "__main__":
    print(build())
