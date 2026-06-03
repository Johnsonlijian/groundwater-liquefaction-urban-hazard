"""Isolate GROUNDWATER storage change from GRACE total water storage (defeats R1).

GWS_trend = TWS_trend (GRACE) - SM_trend (CPC soil moisture)   [both cm water/yr]

GRACE TWS trends reused from city_grace.csv. Soil-moisture from open NOAA CPC monthly
soil moisture (Fan & van den Dool 2004; PSL), single-bucket water-balance soil water (mm).
Loads each window into memory and vectorizes (fast). Snow/surface-water residual minor for
the de-contaminated mid-latitude seismic cohort (noted as limitation).

Output: data_derived/city_gws.csv
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from scipy.stats import linregress

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
SOILW = ROOT / "data_raw" / "soilm" / "soilw.mon.mean.v2.nc"
WINDOWS = {"full": ("2003-01-01", "2024-12-31", 22.0), "recent": ("2015-01-01", "2024-12-31", 10.0)}

def main():
    g = pd.read_csv(DER / "city_grace.csv")
    coh = pd.read_csv(DER / "city_cohort_hazard.csv")  # row-aligned to city_grace
    assert len(g) == len(coh) and (g["name"].values == coh["name"].values).all(), "row misalignment"
    g["lat"] = coh["lat"].values; g["lon"] = coh["lon"].values  # positional, avoids dup-name fan-out
    ds = xr.open_dataset(SOILW, decode_times=True)
    var = "soilw" if "soilw" in ds.data_vars else list(ds.data_vars)[0]
    lonv = ds["lon"].values; latv = ds["lat"].values
    print(f"CPC var={var}; lon {lonv.min():.1f}..{lonv.max():.1f}; lat {latv.min():.1f}..{latv.max():.1f}; n_time={ds.sizes['time']}")
    # city -> nearest grid indices (CPC lon is 0..360)
    clon = g["lon"].values % 360.0 if lonv.max() > 180 else g["lon"].values
    ix = np.array([int(np.abs(lonv - x).argmin()) for x in clon])
    iy = np.array([int(np.abs(latv - y).argmin()) for y in g["lat"].values])

    for w, (t0, t1, nyr) in WINDOWS.items():
        sub = ds[var].sel(time=slice(t0, t1))
        tv = sub["time"].values
        yrs = (tv - tv[0]) / np.timedelta64(365, "D")
        arr = sub.values  # (nt, nlat, nlon) mm  -- load window into memory
        sm = np.full(len(g), np.nan)
        for k in range(len(g)):
            ts = arr[:, iy[k], ix[k]].astype(float); ok = np.isfinite(ts)
            if ok.sum() >= 18:
                sm[k] = linregress(yrs[ok], ts[ok]).slope / 10.0   # mm/yr -> cm/yr
        g[f"{w}_sm_cm_yr"] = np.round(sm, 4)
        tws = g[f"{w}_trend_cm_yr"].values
        gws = tws - sm
        g[f"{w}_gws_cm_yr"] = np.round(gws, 4)
        g[f"{w}_gws_dcm"] = np.round(gws * nyr, 2)
        del arr
    ds.close()
    g["sm_frac_full"] = np.round(np.abs(g["full_sm_cm_yr"]) /
                                 np.abs(g["full_trend_cm_yr"]).replace(0, np.nan), 3)
    out = DER / "city_gws.csv"
    g.to_csv(out, index=False, encoding="utf-8")
    print(f"Wrote {out} ({len(g)} cities)")
    for w in WINDOWS:
        tws = g[f"{w}_trend_cm_yr"]; gws = g[f"{w}_gws_cm_yr"]; sm = g[f"{w}_sm_cm_yr"]
        flip = ((np.sign(tws) != np.sign(gws)) & tws.notna() & gws.notna()).sum()
        print(f"[{w}] med|SM|={np.nanmedian(np.abs(sm)):.3f} med|TWS|={np.nanmedian(np.abs(tws)):.3f} "
              f"med|GWS|={np.nanmedian(np.abs(gws)):.3f} cm/yr | sign flips TWS->GWS {int(flip)} | "
              f"GWS rising {int((gws>0).sum())} falling {int((gws<0).sum())}")
    print("\nKey cities (recent TWS / SM / GWS cm/yr):")
    for nm in ["Beijing", "Tianjin", "Shijiazhuang", "Delhi", "Lahore", "Tokyo", "Mumbai", "Jakarta", "Manila"]:
        r = g[g["name"] == nm]
        if len(r):
            r = r.iloc[0]
            print(f"  {nm:<13} TWS={r['recent_trend_cm_yr']:+.2f}  SM={r['recent_sm_cm_yr']:+.2f}  -> GWS={r['recent_gws_cm_yr']:+.2f}")

if __name__ == "__main__":
    main()
