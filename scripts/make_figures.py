"""Publication figures for the groundwater-liquefaction manuscript (real data).

Fig 1  Mechanism schematic: groundwater change -> effective stress -> liquefaction FS,
        bidirectional (recharge raises risk; depletion lowers it but drives subsidence).
Fig 2  Sign-resolved global map (Robinson): cities colored by ΔP_liq from measured
        2015-2024 groundwater change, sized by population. The visual thesis.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"; FIG = ROOT / "figures"; NE = ROOT / "data_raw" / "naturalearth"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.linewidth": 0.6,
                     "savefig.dpi": 300, "figure.dpi": 120})
RED, BLUE, INK = "#c0392b", "#2c6fbb", "#222222"

def fig2_global_map():
    df = pd.read_csv(DER / "city_results_refined.csv")
    d = df[df["gw_clean"]].copy()
    world = gpd.read_file(f"zip://{NE/'ne_110m_admin_0_countries.zip'}").to_crs("ESRI:54030")
    tr = Transformer.from_crs("EPSG:4326", "ESRI:54030", always_xy=True)
    d["X"], d["Y"] = tr.transform(d["lon"].values, d["lat"].values)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    world.plot(ax=ax, color="#eef0f2", edgecolor="#cfd4d8", linewidth=0.3, zorder=1)
    V = 0.03
    order = d["dP_recent"].abs().sort_values().index  # plot biggest on top
    d = d.loc[order]
    sizes = 10 + 95 * np.sqrt(d["population"].values / d["population"].max())
    sc = ax.scatter(d["X"], d["Y"], c=d["dP_recent"], cmap="RdBu_r", vmin=-V, vmax=V,
                    s=sizes, edgecolors="k", linewidths=0.25, alpha=0.92, zorder=3)
    # annotate signature cities
    labels = {"Beijing": "Beijing ↑ (SNWT recharge)", "Tokyo": "Tokyo", "Yokohama": "",
              "Mumbai": "Mumbai ↑", "Tianjin": "Tianjin ↑", "Delhi": "Delhi ↓ (depletion)",
              "Lahore": "Lahore ↓", "Jakarta": "Jakarta", "Manila": "Manila", "Christchurch": "Christchurch"}
    for nm, lab in labels.items():
        r = d[d["name"] == nm]
        if len(r) and lab:
            r = r.iloc[0]
            ax.annotate(lab, (r["X"], r["Y"]), xytext=(6, 6), textcoords="offset points",
                        fontsize=7.0, color=INK,
                        path_effects=[__import__("matplotlib.patheffects", fromlist=["withStroke"]).withStroke(linewidth=2, foreground="white")])
    cb = fig.colorbar(sc, ax=ax, shrink=0.62, pad=0.01, extend="both")
    cb.set_label("Δ liquefaction probability\n(2015–2024 measured groundwater change)", fontsize=8)
    # size legend
    for p, lab in [(1e6, "1M"), (5e6, "5M"), (15e6, "15M")]:
        ax.scatter([], [], s=10 + 95*np.sqrt(p/d["population"].max()), c="#999",
                   edgecolors="k", linewidths=0.25, label=lab)
    leg = ax.legend(title="City population", loc="lower left", frameon=False, fontsize=7, title_fontsize=7,
                    labelspacing=1.1, borderpad=0.8)
    ninc = int((d["dP_recent"] >= 0.01).sum()); ndec = int((d["dP_recent"] <= -0.01).sum())
    ax.set_title(f"Measured groundwater change is reshaping urban seismic-liquefaction risk in both directions\n"
                 f"{len(d)} seismically-exposed cities (PGA$_{{475}}$≥0.05 g); "
                 f"{ninc} with material increase, {ndec} with material decrease",
                 fontsize=10.5, fontweight="bold")
    ax.set_axis_off()
    ax.text(0.5, -0.04, "Liquefaction model: Zhu et al. (2017) with USGS Vs30, WorldClim precipitation, Fan et al. (2013) baseline water table; "
            "groundwater change: CSR GRACE/GRACE-FO mascon. Effect is local & bidirectional, not a diffuse global trend.",
            transform=ax.transAxes, ha="center", va="top", fontsize=6.2, color="#666")
    fig.tight_layout()
    fig.savefig(FIG / "Fig2_global_signresolved.png", bbox_inches="tight")
    plt.close(fig)
    print("saved Fig2_global_signresolved.png", f"({len(d)} cities)")

def fig1_mechanism():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    fig.suptitle("How 21st-century groundwater change moves the seismic-liquefaction threshold",
                 fontsize=11.5, fontweight="bold", y=1.0)
    for ax, (title, rising) in zip(axes, [("RECHARGE  (managed recharge, sea-level, restoration)", True),
                                          ("DEPLETION  (over-abstraction)", False)]):
        ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.set_axis_off()
        # soil column
        ax.add_patch(Rectangle((1, 1), 5, 7, facecolor="#e9dcc3", edgecolor="k", lw=0.8))
        ax.add_patch(Rectangle((1, 1), 5, 2.0, facecolor="#cdb892", edgecolor="k", lw=0.5))  # dense base
        # baseline water table
        wt0 = 5.2
        ax.plot([1, 6], [wt0, wt0], color=BLUE, lw=1.2, ls="--")
        ax.text(6.15, wt0, "baseline\nwater table", color=BLUE, fontsize=7, va="center")
        # new water table
        wt1 = wt0 + (1.6 if rising else -1.7)
        ax.plot([1, 6], [wt1, wt1], color=(RED if rising else "#2e8b57"), lw=2.0)
        # saturated zone shading
        ax.add_patch(Rectangle((1, 1), 5, wt1-1, facecolor="#9ec9e8", edgecolor="none", alpha=0.5))
        arr = FancyArrowPatch((3.5, wt0), (3.5, wt1), arrowstyle="-|>", mutation_scale=14,
                              color=(RED if rising else "#2e8b57"), lw=2)
        ax.add_patch(arr)
        ax.set_title(title, fontsize=9, fontweight="bold")
        # mechanism text: compact vertical chain placed beside the column, contained in panel
        if rising:
            steps = [r"water table $\uparrow$", r"pore pressure $u\,\uparrow$",
                     r"effective stress $\sigma'_v=\sigma_v-u\;\downarrow$",
                     r"resistance CRR $\downarrow$", r"FS$_L=$CRR/CSR $\downarrow$",
                     r"$P_{liq}\;\uparrow$"]
            box = "LIQUEFACTION\nRISK  ↑"; bc = RED
        else:
            steps = [r"water table $\downarrow$", r"pore pressure $u\,\downarrow$",
                     r"effective stress $\sigma'_v=\sigma_v-u\;\uparrow$",
                     r"resistance CRR $\uparrow$", r"FS$_L\;\uparrow$",
                     r"$P_{liq}\;\downarrow$  (but subsidence $\uparrow$)"]
            box = "LIQUEFACTION\nRISK  ↓\n+ subsidence"; bc = "#2e8b57"
        y = 0.50
        for s in steps:
            ax.text(0.64, y, s, fontsize=7.4, color=INK, transform=ax.transAxes, ha="left", va="top")
            y -= 0.066
        ax.add_patch(FancyBboxPatch((0.64, 0.02), 0.33, 0.13, boxstyle="round,pad=0.02",
                     transform=ax.transAxes, facecolor=bc, alpha=0.13, edgecolor=bc, lw=1.3))
        ax.text(0.805, 0.085, box, fontsize=8.2, fontweight="bold", color=bc,
                ha="center", va="center", transform=ax.transAxes)
    axes[0].text(0.02, 0.97, "Beijing / North China Plain (SNWT)", transform=axes[0].transAxes, fontsize=7, style="italic", color=RED)
    axes[1].text(0.02, 0.97, "Punjab (Delhi, Lahore, Ludhiana)", transform=axes[1].transAxes, fontsize=7, style="italic", color="#2e8b57")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(FIG / "Fig1_mechanism.png", bbox_inches="tight")
    plt.close(fig)
    print("saved Fig1_mechanism.png")

if __name__ == "__main__":
    fig1_mechanism()
    fig2_global_map()
