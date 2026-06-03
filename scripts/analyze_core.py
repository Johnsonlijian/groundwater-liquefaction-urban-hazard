"""CORE ANALYSIS — how observed (2003-2024) groundwater change has shifted urban
seismic liquefaction probability, with real data only.

Pipeline (non-circular): baseline Zhu-2017 P_liq from real inputs; then perturb ONLY
the measured groundwater term (GRACE -> Δwtd) and recompute. ΔP_liq is the earned signal.

Outputs (data_derived/):
  city_results.csv         per-city baseline/new P_liq, ΔP_liq, exposure
  core_summary.json        cohort headline numbers + S_y sensitivity + null test
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
sys.path.insert(0, str(ROOT / "scripts"))
from zhu2017 import p_liquefaction, lse_percent, B_WTD

SY_GRID = [0.05, 0.10, 0.15, 0.25]
MATERIAL = 0.01   # |ΔP_liq| >= 1 percentage point counts as "material"
RNG = np.random.default_rng(20260603)

def load():
    a = pd.read_csv(DER / "city_inputs.csv")
    g = pd.read_csv(DER / "city_grace.csv")
    assert len(a) == len(g) and (a["name"].values == g["name"].values).all(), "row misalignment"
    for c in ["grace_trend_cm_yr", "grace_se", "grace_p", "dTWS_cm_total"]:
        a[c] = g[c].values
    return a

def dwtd_from_tws(dtws_cm_total, sy):
    return -(dtws_cm_total / 100.0) / sy   # rising storage -> wtd shallower (negative)

def p_at(df, wtd):
    return p_liquefaction(df["pgv"].values, df["vs30"].values, df["precip"].values,
                          df["dw_km"].values, wtd)

def compute(df, sy):
    base_wtd = df["wtd"].values
    dwtd = dwtd_from_tws(df["dTWS_cm_total"].values, sy)
    new_wtd = np.clip(base_wtd + dwtd, 0.0, None)
    P0 = p_at(df, base_wtd); P1 = p_at(df, new_wtd)
    return P0, P1, (P1 - P0), dwtd, new_wtd

def main():
    df = load()
    seis = df[(df["pga_475_g"] >= 0.05) & df["wtd"].notna() & df["dTWS_cm_total"].notna()].copy()
    print(f"Analysis cohort: {len(seis)} seismic cities with full real inputs")

    P0, P1, dP, dwtd, new_wtd = compute(seis, 0.10)
    seis["P_liq_base"] = P0; seis["P_liq_new"] = P1; seis["dP_liq"] = dP
    seis["dwtd_m"] = dwtd; seis["wtd_new"] = new_wtd
    seis["LSE_base"] = lse_percent(P0); seis["LSE_new"] = lse_percent(P1)
    seis["pop_x_dP"] = seis["population"].values * dP   # person-probability exposure delta

    inc = seis["dP_liq"] >= MATERIAL; dec = seis["dP_liq"] <= -MATERIAL
    pop_inc = int(seis.loc[inc, "population"].sum()); pop_dec = int(seis.loc[dec, "population"].sum())

    summary = {
        "n_cities": int(len(seis)),
        "dP_liq_mean": float(np.mean(dP)), "dP_liq_median": float(np.median(dP)),
        "n_material_increase": int(inc.sum()), "n_material_decrease": int(dec.sum()),
        "pop_material_increase": pop_inc, "pop_material_decrease": pop_dec,
        "net_pop_x_dP": float(seis["pop_x_dP"].sum()),
        "mean_LSE_change_pct": float(np.mean(seis["LSE_new"] - seis["LSE_base"])),
    }

    # ---- S_y sensitivity (sign robust; magnitude scales) ----
    sens = {}
    for sy in SY_GRID:
        _, _, dPsy, _, _ = compute(seis, sy)
        sens[f"Sy_{sy}"] = {"n_material_increase": int((dPsy >= MATERIAL).sum()),
                            "mean_dP": float(np.mean(dPsy))}
    summary["Sy_sensitivity"] = sens

    # ---- geographic null: shuffle GRACE trend across cities, recompute ----
    null_inc, null_meanabs = [], []
    base_other = seis.drop(columns=["dTWS_cm_total"]).copy()
    for _ in range(1000):
        perm = RNG.permutation(seis["dTWS_cm_total"].values)
        tmp = base_other.copy(); tmp["dTWS_cm_total"] = perm
        _, _, dPn, _, _ = compute(tmp, 0.10)
        null_inc.append(int((dPn >= MATERIAL).sum())); null_meanabs.append(float(np.mean(np.abs(dPn))))
    obs_meanabs = float(np.mean(np.abs(dP)))
    p_null = (np.sum(np.array(null_meanabs) >= obs_meanabs) + 1) / (len(null_meanabs) + 1)
    summary["null_test"] = {
        "obs_mean_abs_dP": obs_meanabs,
        "null_mean_abs_dP_mean": float(np.mean(null_meanabs)),
        "null_mean_abs_dP_p95": float(np.percentile(null_meanabs, 95)),
        "p_value_geographic_null": float(p_null),
        "obs_n_material_increase": int(inc.sum()),
        "null_n_material_increase_mean": float(np.mean(null_inc)),
    }

    seis.sort_values("dP_liq", ascending=False).to_csv(DER / "city_results.csv", index=False, encoding="utf-8")
    (DER / "core_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n================ HEADLINE (S_y=0.10) ================")
    print(f"Material risk INCREASE: {summary['n_material_increase']} cities, "
          f"{pop_inc/1e6:.0f}M people")
    print(f"Material risk DECREASE: {summary['n_material_decrease']} cities, "
          f"{pop_dec/1e6:.0f}M people")
    print(f"Mean ΔP_liq = {summary['dP_liq_mean']:+.4f}; mean ΔLSE = {summary['mean_LSE_change_pct']:+.2f}%")
    print(f"Geographic null test p = {summary['null_test']['p_value_geographic_null']:.4f} "
          f"(obs mean|ΔP|={obs_meanabs:.4f} vs null {summary['null_test']['null_mean_abs_dP_mean']:.4f})")
    print("\nTop 12 INCREASES (rising water table + shallow + seismic):")
    for _, r in seis.sort_values("dP_liq", ascending=False).head(12).iterrows():
        print(f"  {r['name']:<15}{r['country']:<3} ΔP={r['dP_liq']:+.3f}  P:{r['P_liq_base']:.2f}->{r['P_liq_new']:.2f}  "
              f"wtd:{r['wtd']:.1f}->{r['wtd_new']:.1f}m  PGA={r['pga_475_g']:.2f}  pop={int(r['population'])/1e6:.1f}M")
    print("\nTop 8 DECREASES (depletion):")
    for _, r in seis.sort_values("dP_liq").head(8).iterrows():
        print(f"  {r['name']:<15}{r['country']:<3} ΔP={r['dP_liq']:+.3f}  wtd:{r['wtd']:.1f}->{r['wtd_new']:.1f}m  PGA={r['pga_475_g']:.2f}")

if __name__ == "__main__":
    main()
