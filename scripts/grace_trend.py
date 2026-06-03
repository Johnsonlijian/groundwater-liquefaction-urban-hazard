"""Per-city GRACE/GRACE-FO terrestrial-water-storage trend (the measured driver).

CSR RL06.3 mascon `lwe_thickness` = liquid water equivalent anomaly (cm), monthly,
0.25 deg, 0-360 lon. We fit a per-city linear trend (cm/yr) over a chosen window and
convert it to a water-table-depth change via specific yield S_y (rising storage ->
shallower water table -> wtd decreases):

    dTWS_m   = (trend_cm_yr * n_years) / 100
    d(water table elevation) = dTWS_m / S_y
    Δwtd     = - dTWS_m / S_y          # negative = water table rises = wtd shallower

Output: data_derived/city_grace.csv
  grace_trend_cm_yr, grace_se, grace_p, grace_years, dTWS_cm_total, dwtd_m_Sy010
Caveats (handled downstream): TWS includes soil moisture/snow; S_y uncertainty swept
in the P_liq analysis; sign is robust to S_y. Cross-checked vs Jasechko 2024 wells.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
from scipy.stats import linregress

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
GRACE = ROOT / "data_raw" / "grace" / "CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc"
WINDOWS = {"full": (2003.0, 2024.99), "recent": (2015.0, 2024.99)}  # full record vs recent trajectory
SY_DEFAULT = 0.10             # specific yield (unconfined); swept 0.05-0.25 downstream

def decode_years(ds):
    t = ds["time"]
    units = t.attrs.get("units", "days since 2002-01-01 00:00:00")
    try:
        dt = xr.coding.times.decode_cf_datetime(t.values, units)
        return np.array([d.astype("datetime64[D]").astype(object).year +
                         (d.astype("datetime64[D]").astype(object).timetuple().tm_yday-1)/365.25
                         for d in dt])
    except Exception:
        # fallback: assume days since 2002-01-01
        return 2002.0 + t.values / 365.25

def fit_window(years, lwe_vals, lat, lon, df, y0, y1):
    sel = (years >= y0) & (years <= y1)
    yv = years[sel]; vals = lwe_vals[sel]
    rows = []
    for _, r in df.iterrows():
        ix = int(np.abs(lon - (r["lon"] % 360.0)).argmin())
        iy = int(np.abs(lat - r["lat"]).argmin())
        ts = vals[:, iy, ix].astype(float); ok = np.isfinite(ts)
        if ok.sum() < 18:
            rows.append((np.nan, np.nan, np.nan, np.nan)); continue
        lr = linregress(yv[ok], ts[ok])
        n_yr = yv[ok].max() - yv[ok].min()
        rows.append((round(lr.slope, 4), round(lr.pvalue, 5),
                     round(lr.slope * n_yr, 2), -(lr.slope * n_yr / 100.0) / SY_DEFAULT,
                     round(lr.stderr, 4)))
    return yv, np.array(rows, float)

def main():
    ds = xr.open_dataset(GRACE)
    years = decode_years(ds)
    lwe_vals = ds["lwe_thickness"].values  # (time, lat, lon) cm
    lat = ds["lat"].values; lon = ds["lon"].values
    df = pd.read_csv(DER / "city_cohort_hazard.csv")
    g = df[["name"]].copy()
    for tag, (y0, y1) in WINDOWS.items():
        yv, arr = fit_window(years, lwe_vals, lat, lon, df, y0, y1)
        print(f"[{tag}] window {y0}-{y1}: {len(yv)} epochs ({yv.min():.2f}..{yv.max():.2f})")
        g[f"{tag}_trend_cm_yr"] = arr[:, 0]; g[f"{tag}_p"] = arr[:, 1]
        g[f"{tag}_dTWS_cm"] = arr[:, 2]; g[f"{tag}_dwtd_Sy010"] = arr[:, 3]
        g[f"{tag}_se_cm_yr"] = arr[:, 4]
    # keep legacy column names (full-record) for backward compat with analyze_core
    g["grace_trend_cm_yr"] = g["full_trend_cm_yr"]; g["grace_p"] = g["full_p"]
    g["dTWS_cm_total"] = g["full_dTWS_cm"]
    # reversal flag: full and recent trends differ in sign (e.g. Beijing post-SNWTP recovery)
    g["reversal"] = (np.sign(g["full_trend_cm_yr"]) != np.sign(g["recent_trend_cm_yr"])) \
                    & g["full_trend_cm_yr"].notna() & g["recent_trend_cm_yr"].notna()
    out = DER / "city_grace.csv"; g.to_csv(out, index=False, encoding="utf-8"); ds.close()
    print(f"Wrote {out} ({len(g)} cities); reversal cities (full vs recent sign flip): {int(g['reversal'].sum())}")
    for tag in WINDOWS:
        s = g[f"{tag}_trend_cm_yr"]
        print(f"  [{tag}] rising {int((s>0).sum())}, falling {int((s<0).sum())}")
    bj = g[g["name"] == "Beijing"]
    if len(bj):
        b = bj.iloc[0]
        print(f"\nBeijing: full={b['full_trend_cm_yr']:+.2f} cm/yr (p={b['full_p']:.3g}), "
              f"recent={b['recent_trend_cm_yr']:+.2f} cm/yr (p={b['recent_p']:.3g}), reversal={bool(b['reversal'])}")
    print("\nNotable reversal cities (full falling -> recent rising = managed-recharge recovery):")
    rev = g[g["reversal"] & (g["recent_trend_cm_yr"] > 0)].sort_values("recent_trend_cm_yr", ascending=False)
    for _, r in rev.head(10).iterrows():
        print(f"  {r['name']:<16} full {r['full_trend_cm_yr']:+.2f} -> recent {r['recent_trend_cm_yr']:+.2f} cm/yr")

if __name__ == "__main__":
    main()
