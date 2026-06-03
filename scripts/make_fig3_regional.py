"""Fig 3 — regional zooms of the bidirectional signal (real per-city ΔP_liq with CIs).

Panel A: North China Plain  (managed recharge / South-North Water Transfer -> risk UP)
Panel B: NW India & Pakistan (aquifer depletion -> risk DOWN + subsidence)
Panel C: Japan               (rising shallow tables + very high seismic hazard -> risk UP)
Cities colored by recent-window ΔP_liq, sized by population; FDR-significant cities ringed.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib as mpl; mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"; FIG = ROOT / "figures"; NE = ROOT / "data_raw" / "naturalearth"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "savefig.dpi": 300})

REGIONS = [
    ("A  North China Plain", "↑ managed recharge (South–North Water Transfer)", "#c0392b", (112.5, 122.5, 33.5, 41.5),
     ["Beijing", "Tianjin", "Shijiazhuang", "Xingtai", "Handan", "Jinan", "Zhengzhou", "Tangshan", "Baoding"]),
    ("B  NW India & Pakistan", "↓ aquifer depletion (+ subsidence)", "#2e8b57", (72, 80.5, 26, 33.5),
     ["Delhi", "Lahore", "Ludhiana", "Faridabad", "Amritsar", "Chandigarh", "Meerut", "Jaipur", "Kanpur"]),
    ("C  Japan", "↑ rising tables + extreme hazard", "#c0392b", (133, 142.5, 33, 40.5),
     ["Tokyo", "Yokohama", "Kawasaki", "Nagoya", "Osaka", "Chiba", "Sendai", "Hamamatsu"]),
]

def main():
    df = pd.read_csv(DER / "city_results_v2.csv")
    world = gpd.read_file(f"zip://{NE/'ne_50m_admin_0_countries.zip'}")
    rivers = gpd.read_file(f"zip://{NE/'ne_50m_rivers_lake_centerlines.zip'}")
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.0), constrained_layout=True)
    V = 0.015; sc = None
    for ax, (title, sub, subc, (x0, x1, y0, y1), labels) in zip(axes, REGIONS):
        world.plot(ax=ax, color="#f2efe9", edgecolor="#b9bdc2", linewidth=0.5, zorder=1)
        rivers.plot(ax=ax, color="#9ec9e8", linewidth=0.6, zorder=2)
        d = df[(df.lon >= x0) & (df.lon <= x1) & (df.lat >= y0) & (df.lat <= y1)]
        sizes = 35 + 150 * np.sqrt(d["population"].values / 1.5e7)
        sc = ax.scatter(d.lon, d.lat, c=d["dP"], cmap="RdBu_r", vmin=-V, vmax=V, s=sizes,
                        edgecolors="k", linewidths=0.4, zorder=4)
        fs = d[d["fdr_sig"]] if "fdr_sig" in d else d.iloc[0:0]
        ax.scatter(fs.lon, fs.lat, s=35 + 150*np.sqrt(fs["population"].values/1.5e7) + 70,
                   facecolors="none", edgecolors="#111", linewidths=1.2, zorder=5)
        for nm in labels:
            r = d[d["name"] == nm]
            if len(r):
                r = r.iloc[0]
                ax.annotate(nm, (r.lon, r.lat), xytext=(4, 3), textcoords="offset points",
                            fontsize=7, zorder=6, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        ax.set_aspect(1.0/np.cos(np.radians((y0+y1)/2)))  # true geographic proportions
        ax.set_title(title, fontsize=9.5, fontweight="bold", loc="left")
        ax.text(0.02, 0.97, sub, transform=ax.transAxes, fontsize=7.6, fontweight="bold",
                color=subc, va="top", path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values(): s.set_edgecolor("#888")
    cb = fig.colorbar(sc, ax=axes, shrink=0.55, pad=0.01, extend="both", location="right")
    cb.set_label("Δ liquefaction probability (2015–2024)", fontsize=8)
    fig.suptitle("Regional structure of the bidirectional signal (black rings = FDR-significant cities)",
                 fontsize=10.5, fontweight="bold")
    fig.savefig(FIG / "Fig3_regional.png", bbox_inches="tight")
    plt.close(fig)
    print("saved Fig3_regional.png")

if __name__ == "__main__":
    main()
