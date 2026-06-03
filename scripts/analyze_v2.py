"""v2 per-city analysis — well-validated GRACE-TWS driver, uncertainty-aware, FDR-controlled.

Primary driver = GRACE total-water-storage trend (recent window, 2015-2024), used as a
REGIONAL groundwater proxy validated against in-situ wells (Wang 2025; Rodell 2009;
Jasechko 2024). The soil-moisture-subtracted GWS driver is reported only as a sensitivity
(it fails at city scale; see groundwater_isolation.py / Beijing flip).

Per-city ΔP_liq bootstrap CIs propagate (a) GRACE trend SE and (b) S_y ~ U(0.05,0.25).
A hotspot is reported only if its 90% CI excludes 0; Benjamini-Hochberg FDR (q=0.10)
controls multiplicity across the cohort.

Outputs: city_results_v2.csv, core_summary_v2.json, hotspot_table.csv
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"; RAW = ROOT / "data_raw"
sys.path.insert(0, str(ROOT / "scripts"))
from zhu2017 import p_liquefaction

MATERIAL = 0.01; B = 4000; RNG = np.random.default_rng(20260603); R_EARTH = 6371.0
SY_LO, SY_HI = 0.05, 0.25; NY = 10.0
DRIVER, DRIVER_SE = "recent_trend_cm_yr", "recent_se_cm_yr"   # TWS primary
INLAND_SEAS = {"Caspian": (46, 55, 36, 47.5), "Aral": (57.5, 62.5, 43, 47.5)}

def lonlat_xyz(lon, lat):
    lon = np.radians(np.asarray(lon, float)); lat = np.radians(np.asarray(lat, float))
    return np.column_stack([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])

def gw_clean_flags(lons, lats):
    g = gpd.read_file(f"zip://{RAW/'naturalearth'/'ne_10m_lakes.zip'}")
    big = g[(g["scalerank"] <= 2) | g["name"].fillna("").str.contains(
        "Victoria|Superior|Huron|Michigan|Baikal|Erie|Ontario|Balkhash|Tanganyika|Malawi|Ladoga", case=False)]
    verts = []
    for geom in big.geometry:
        if geom is None: continue
        for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            verts.extend(list(p.exterior.coords))
    tree = cKDTree(lonlat_xyz(np.array(verts)[:, 0], np.array(verts)[:, 1]))
    cd, _ = tree.query(lonlat_xyz(lons, lats), k=1)
    d = 2*np.arcsin(np.clip(cd/2, 0, 1))*R_EARTH
    inland = np.zeros(len(lons), bool)
    for (a, b, c, e) in INLAND_SEAS.values():
        inland |= (lons >= a) & (lons <= b) & (lats >= c) & (lats <= e)
    return (d >= 30.0) & (~inland)

def load():
    a = pd.read_csv(DER / "city_inputs.csv"); gw = pd.read_csv(DER / "city_gws.csv")
    assert (a["name"].values == gw["name"].values).all(), "row misalignment"
    for c in [DRIVER, DRIVER_SE, "recent_gws_cm_yr", "reversal"]:
        a[c] = gw[c].values
    return a

def pliq(r, wtd):
    return float(p_liquefaction(r["pgv"], r["vs30"], r["precip"], r["dw_km"], wtd))

def bh_fdr(p, q=0.10):
    p = np.asarray(p, float); n = len(p); order = np.argsort(p)
    passed = p[order] <= q*(np.arange(1, n+1))/n
    k = np.where(passed)[0].max()+1 if passed.any() else 0
    out = np.zeros(n, bool); out[order[:k]] = True
    return out

def dP_for(r, trend, sy):
    dwtd = -(trend*NY/100.0)/sy
    return pliq(r, max(r["wtd"]+dwtd, 0.0)) - pliq(r, r["wtd"])

def main():
    a = load()
    a["gw_clean"] = gw_clean_flags(a["lon"].values, a["lat"].values)
    seis = a[(a["pga_475_g"] >= 0.05) & a["wtd"].notna() & a[DRIVER].notna() & a["gw_clean"]].copy()
    print(f"v2 cohort (clean seismic): {len(seis)}; driver={DRIVER}")

    recs = []
    for _, r in seis.iterrows():
        tr = r[DRIVER]; se = max(float(r[DRIVER_SE]) if pd.notna(r[DRIVER_SE]) else 0.1, 1e-3)
        dP0 = dP_for(r, tr, 0.10)
        trs = RNG.normal(tr, se, B); sys_ = RNG.uniform(SY_LO, SY_HI, B)
        dwtd = -(trs*NY/100.0)/sys_
        dPs = np.array([pliq(r, max(r["wtd"]+d, 0.0)) for d in dwtd]) - pliq(r, r["wtd"])
        lo, hi = np.percentile(dPs, [5, 95]); fp = float(np.mean(dPs > 0))
        recs.append(dict(name=r["name"], country=r["country"], lat=r["lat"], lon=r["lon"],
                         population=int(r["population"]), pga=r["pga_475_g"], wtd=r["wtd"],
                         tws_cm_yr=tr, reversal=bool(r["reversal"]), dP=dP0, dP_lo=lo, dP_hi=hi,
                         p_two=2*min(fp, 1-fp), ci_excl0=bool(lo > 0 or hi < 0)))
    res = pd.DataFrame(recs)
    res["fdr_sig"] = bh_fdr(res["p_two"].values, 0.10)
    res = res.sort_values("dP", ascending=False)
    res.to_csv(DER / "city_results_v2.csv", index=False, encoding="utf-8")

    sig = res[res["fdr_sig"] & (res["dP"].abs() >= MATERIAL)].copy()
    inc = sig[sig["dP"] > 0]; dec = sig[sig["dP"] < 0]
    sig["direction"] = np.where(sig["dP"] > 0, "increase", "decrease")
    sig.sort_values("dP", ascending=False).to_csv(DER / "hotspot_table.csv", index=False, encoding="utf-8")
    # GWS sensitivity (SM-subtracted) for comparison count
    gsig = 0
    for _, r in seis.iterrows():
        if pd.notna(r["recent_gws_cm_yr"]) and dP_for(r, r["recent_gws_cm_yr"], 0.10) >= MATERIAL:
            gsig += 1
    summary = dict(n=len(res), n_ci_excl0=int(res["ci_excl0"].sum()), n_fdr_sig=int(res["fdr_sig"].sum()),
                   n_material_inc=int(len(inc)), n_material_dec=int(len(dec)),
                   pop_inc=int(inc["population"].sum()), pop_dec=int(dec["population"].sum()),
                   mean_dP=float(res["dP"].mean()), gws_sensitivity_n_material_inc=gsig)
    bj = res[res["name"] == "Beijing"]
    if len(bj):
        b = bj.iloc[0]; summary["beijing"] = dict(dP=float(b["dP"]), ci=[float(b["dP_lo"]), float(b["dP_hi"])],
                                                   tws=float(b["tws_cm_yr"]), fdr_sig=bool(b["fdr_sig"]))
    (DER / "core_summary_v2.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"CI excludes 0: {summary['n_ci_excl0']}; FDR-sig: {summary['n_fdr_sig']}")
    print(f"Material+FDR-sig: INCREASE {len(inc)} ({summary['pop_inc']/1e6:.0f}M), DECREASE {len(dec)} ({summary['pop_dec']/1e6:.0f}M)")
    print(f"(GWS-subtracted sensitivity material increases: {gsig})")
    if "beijing" in summary:
        b = summary["beijing"]; print(f"Beijing dP={b['dP']:+.4f} CI[{b['ci'][0]:+.4f},{b['ci'][1]:+.4f}] TWS={b['tws']:+.2f} FDRsig={b['fdr_sig']}")
    print("\nHOTSPOTS — increase, FDR-significant & material (the defensible list):")
    for _, r in inc.head(15).iterrows():
        print(f"  {'REV' if r['reversal'] else '   '} {r['name']:<13}{r['country']:<3} dP={r['dP']:+.3f} CI[{r['dP_lo']:+.3f},{r['dP_hi']:+.3f}] TWS={r['tws_cm_yr']:+.2f} PGA={r['pga']:.2f} pop={r['population']/1e6:.1f}M")
    print("\nDecrease, FDR-significant & material (depletion):")
    for _, r in dec.sort_values("dP").head(10).iterrows():
        print(f"      {r['name']:<13}{r['country']:<3} dP={r['dP']:+.3f} CI[{r['dP_lo']:+.3f},{r['dP_hi']:+.3f}] TWS={r['tws_cm_yr']:+.2f} pop={r['population']/1e6:.1f}M")

if __name__ == "__main__":
    main()
