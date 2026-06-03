"""Fig 4 — GRACE water-storage time series for signature cities, showing the
recent reversals that drive the bidirectional liquefaction signal.

Beijing & Tianjin (North China Plain): long-term decline REVERSING to recent rise
(South-North Water Transfer). Delhi & Lahore (Punjab): sustained decline.
Full-record vs recent-window linear trends annotated. Validates the dual-window choice.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
import matplotlib as mpl; mpl.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import linregress

ROOT = Path(__file__).resolve().parents[1]
GRACE = ROOT/"data_raw"/"grace"/"CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc"
FIG = ROOT/"figures"
CITIES = {"Beijing": (39.91,116.40), "Tianjin": (39.13,117.20),
          "Delhi": (28.61,77.21), "Lahore": (31.56,74.35)}
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"savefig.dpi":300})

def decode_years(ds):
    t=ds["time"]; u=t.attrs.get("units","days since 2002-01-01 00:00:00")
    try:
        dt=xr.coding.times.decode_cf_datetime(t.values,u)
        return np.array([d.astype("datetime64[D]").astype(object).year+
                         (d.astype("datetime64[D]").astype(object).timetuple().tm_yday-1)/365.25 for d in dt])
    except Exception:
        return 2002.0+t.values/365.25

def main():
    ds=xr.open_dataset(GRACE); yr=decode_years(ds)
    lwe=ds["lwe_thickness"].values; lat=ds["lat"].values; lon=ds["lon"].values
    fig,axes=plt.subplots(2,2,figsize=(11,6.4),sharex=True)
    for ax,(nm,(la,lo)) in zip(axes.ravel(),CITIES.items()):
        ix=int(np.abs(lon-(lo%360)).argmin()); iy=int(np.abs(lat-la).argmin())
        ts=lwe[:,iy,ix].astype(float); ok=np.isfinite(ts)
        ax.plot(yr[ok],ts[ok],color="#888",lw=0.8,marker="o",ms=2,label="GRACE TWS anomaly")
        # full + recent trends
        for (y0,y1,c,lab) in [(2003,2025,"#444","full 2003–24"),(2015,2025,"#c0392b","recent 2015–24")]:
            m=(yr>=y0)&(yr<=y1)&ok
            if m.sum()>10:
                lr=linregress(yr[m],ts[m]); xs=np.array([yr[m].min(),yr[m].max()])
                ax.plot(xs,lr.intercept+lr.slope*xs,c=c,lw=2.2 if "recent" in lab else 1.4,
                        ls="-" if "recent" in lab else "--",
                        label=f"{lab}: {lr.slope:+.2f} cm/yr")
        ax.axhline(0,color="#ccc",lw=0.5); ax.set_title(nm,fontweight="bold",fontsize=10)
        ax.legend(fontsize=6.6,loc="best",frameon=False); ax.grid(alpha=0.25)
        ax.set_ylabel("TWS anomaly (cm)")
    for ax in axes[1]: ax.set_xlabel("Year")
    fig.suptitle("Measured groundwater-storage trajectories: North China Plain reversal (Beijing, Tianjin) "
                 "vs Punjab decline (Delhi, Lahore)", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0,0,1,0.96])
    fig.savefig(FIG/"Fig4_timeseries.png",bbox_inches="tight"); plt.close(fig); ds.close()
    print("saved Fig4_timeseries.png")

if __name__=="__main__":
    main()
