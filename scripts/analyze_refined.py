"""REFINED dual-window analysis for the bidirectional groundwater-liquefaction framing.

 - Two GRACE windows: 'full' (2003-2024, long-term context) and 'recent' (2015-2024,
   current trajectory). Recent captures managed-recharge reversals (Beijing/North China
   Plain post South-North Water Transfer), validated against Wang et al. 2025.
 - De-contaminate large INLAND water bodies (Great Lakes/Victoria/Baikal via Natural Earth
   + Caspian/Aral via bbox). Ocean-coastal cities kept.
 - ΔP_liq from perturbing ONLY the measured groundwater term in Zhu-2017.
 - Sign-resolved hotspots, both-sides exposure, geographic null, Beijing validation.

Outputs: city_results_refined.csv, core_summary_refined.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"; RAW = ROOT / "data_raw"
sys.path.insert(0, str(ROOT / "scripts"))
from zhu2017 import p_liquefaction, lse_percent

SY = 0.10; MATERIAL = 0.01; RNG = np.random.default_rng(20260603); R_EARTH = 6371.0
# inland-sea bboxes not in Natural Earth lakes (lon_min, lon_max, lat_min, lat_max)
INLAND_SEAS = {"Caspian": (46, 55, 36, 47.5), "Aral": (57.5, 62.5, 43, 47.5)}

def lonlat_xyz(lon, lat):
    lon = np.radians(np.asarray(lon, float)); lat = np.radians(np.asarray(lat, float))
    return np.column_stack([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])

def dist_major_lakes_km(lons, lats):
    g = gpd.read_file(f"zip://{RAW/'naturalearth'/'ne_10m_lakes.zip'}")
    big = g[(g["scalerank"] <= 2) | g["name"].fillna("").str.contains(
        "Victoria|Superior|Huron|Michigan|Baikal|Erie|Ontario|Balkhash|Tanganyika|Malawi|Ladoga", case=False)]
    verts = []
    for geom in big.geometry:
        if geom is None: continue
        for p in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
            verts.extend(list(p.exterior.coords))
    verts = np.array(verts)[:, :2]
    tree = cKDTree(lonlat_xyz(verts[:, 0], verts[:, 1]))
    cd, _ = tree.query(lonlat_xyz(lons, lats), k=1)
    d = 2*np.arcsin(np.clip(cd/2, 0, 1))*R_EARTH
    inland = np.zeros(len(lons), bool)
    for (a, b, c, e) in INLAND_SEAS.values():
        inland |= (lons >= a) & (lons <= b) & (lats >= c) & (lats <= e)
    return d, inland

def load():
    a = pd.read_csv(DER / "city_inputs.csv"); g = pd.read_csv(DER / "city_grace.csv")
    assert (a["name"].values == g["name"].values).all()
    for c in ["full_dTWS_cm", "recent_dTWS_cm", "full_trend_cm_yr", "recent_trend_cm_yr",
              "full_p", "recent_p", "reversal"]:
        a[c] = g[c].values
    return a

def pliq(df, wtd):
    return p_liquefaction(df["pgv"].values, df["vs30"].values, df["precip"].values, df["dw_km"].values, wtd)

def dP(df, dtws_col, sy=SY):
    dwtd = -(df[dtws_col].values/100.0)/sy
    new = np.clip(df["wtd"].values + dwtd, 0.0, None)
    P0 = pliq(df, df["wtd"].values); P1 = pliq(df, new)
    return P0, P1, P1-P0, dwtd, new

def block(d, dcol):
    P0, P1, dPv, dwtd, new = dP(d, dcol)
    inc = dPv >= MATERIAL; dec = dPv <= -MATERIAL
    return dict(n=int(len(d)), mean_dP=float(np.mean(dPv)),
                n_inc=int(inc.sum()), n_dec=int(dec.sum()),
                pop_inc=int(d.loc[inc, "population"].sum()), pop_dec=int(d.loc[dec, "population"].sum()))

def null_p(d, dcol, n=1000):
    P0, P1, dPv, _, _ = dP(d, dcol); obs = float(np.mean(np.abs(dPv)))
    base = d.copy(); nm = []
    for _ in range(n):
        base[dcol] = RNG.permutation(d[dcol].values)
        _, _, dn, _, _ = dP(base, dcol); nm.append(float(np.mean(np.abs(dn))))
    return obs, float(np.mean(nm)), float((np.sum(np.array(nm) >= obs)+1)/(n+1))

def main():
    df = load()
    d_lake, inland = dist_major_lakes_km(df["lon"].values, df["lat"].values)
    df["dist_lake_km"] = d_lake
    df["gw_clean"] = (d_lake >= 30.0) & (~inland)

    seis = df[(df["pga_475_g"] >= 0.05) & df["wtd"].notna() & df["full_dTWS_cm"].notna()].copy()
    for w in ["full", "recent"]:
        P0, P1, dPv, dwtd, new = dP(seis, f"{w}_dTWS_cm")
        seis[f"P0_{w}"] = P0; seis[f"dP_{w}"] = dPv; seis[f"wtdnew_{w}"] = new
        seis[f"dLSE_{w}"] = lse_percent(P1) - lse_percent(P0)
    clean = seis[seis["gw_clean"]].copy()

    summary = {"n_seis": int(len(seis)), "n_clean": int(len(clean)),
               "n_contaminated_removed": int((~seis["gw_clean"]).sum())}
    for w in ["full", "recent"]:
        summary[f"clean_{w}"] = block(clean, f"{w}_dTWS_cm")
        o, nmean, p = null_p(clean, f"{w}_dTWS_cm")
        summary[f"null_{w}"] = {"obs_mean_abs_dP": o, "null_mean": nmean, "p": p}
    bj = seis[seis["name"] == "Beijing"]
    if len(bj):
        r = bj.iloc[0]
        summary["beijing"] = {"recent_trend": float(r["recent_trend_cm_yr"]), "dP_recent": float(r["dP_recent"]),
                              "P0_recent": float(r["P0_recent"]), "matches_wang2025": bool(r["recent_trend_cm_yr"] > 0 and r["dP_recent"] > 0)}
    # North China Plain reversal cluster exposure (recent rising + full falling)
    ncp = clean[(clean["reversal"]) & (clean["recent_trend_cm_yr"] > 0) & (clean["dP_recent"] >= MATERIAL)]
    summary["reversal_increase_cluster"] = {"n": int(len(ncp)), "pop": int(ncp["population"].sum())}

    seis.sort_values("dP_recent", ascending=False).to_csv(DER / "city_results_refined.csv", index=False, encoding="utf-8")
    (DER / "core_summary_refined.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Seismic {summary['n_seis']} | clean {summary['n_clean']} (removed {summary['n_contaminated_removed']} inland-water-contaminated)")
    for w in ["full", "recent"]:
        b = summary[f"clean_{w}"]; nt = summary[f"null_{w}"]
        print(f"[{w:6}] mean dP={b['mean_dP']:+.4f} | INC {b['n_inc']} cities/{b['pop_inc']/1e6:.0f}M | "
              f"DEC {b['n_dec']} cities/{b['pop_dec']/1e6:.0f}M | null p={nt['p']:.3f} (obs {nt['obs_mean_abs_dP']:.4f} vs {nt['null_mean']:.4f})")
    if "beijing" in summary:
        b = summary["beijing"]; print(f"Beijing recent: {b['recent_trend']:+.2f} cm/yr, dP={b['dP_recent']:+.4f}, matches Wang2025={b['matches_wang2025']}")
    print(f"Reversal-driven INCREASE cluster (managed recharge): {summary['reversal_increase_cluster']['n']} cities, "
          f"{summary['reversal_increase_cluster']['pop']/1e6:.0f}M ppl")
    print("\nRECENT-window top-15 INCREASES (clean):")
    for _, r in clean.sort_values("dP_recent", ascending=False).head(15).iterrows():
        flag = "REV" if r["reversal"] else "   "
        print(f"  {flag} {r['name']:<14}{r['country']:<3} dP={r['dP_recent']:+.3f} P:{r['P0_recent']:.2f}->{r['P0_recent']+r['dP_recent']:.2f} "
              f"wtd:{r['wtd']:.1f}->{r['wtdnew_recent']:.1f} PGA={r['pga_475_g']:.2f} pop={r['population']/1e6:.1f}M")
    print("\nRECENT-window top-8 DECREASES (clean; depletion):")
    for _, r in clean.sort_values("dP_recent").head(8).iterrows():
        print(f"      {r['name']:<14}{r['country']:<3} dP={r['dP_recent']:+.3f} wtd:{r['wtd']:.1f}->{r['wtdnew_recent']:.1f} PGA={r['pga_475_g']:.2f} pop={r['population']/1e6:.1f}M")

if __name__ == "__main__":
    main()
