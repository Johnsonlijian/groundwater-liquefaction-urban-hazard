"""R33 statistical-object audit for the Nature Water submission.

This script converts the main red-team statistical concerns into derived tables:

1. zero-aware downstream counts for city and block FDR;
2. materiality uncertainty for the baseline CSR-material units;
3. independence-scale counts for the static-counterfactual A/B follow-up units;
4. independent-product support classes for CSR-material units;
5. local sign-test summaries for Tokyo Bay/Yokohama evidence.

The script does not change model outputs. It only records how the same outputs
should be interpreted under finite-Monte-Carlo, spatial and product-support
guardrails.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
sys.path.insert(0, str(ROOT / "scripts"))

from zhu2017 import p_liquefaction
import analyze_v2


B = 4000
Q_FDR = 0.10
MATERIAL = 0.01
SY_LO = 0.05
SY_HI = 0.25
NYEARS = 10.0
RNG_SEED = 20260603
HOTSPOT_NAMES = {"Yokohama", "Bhayandar", "Mumbai", "Delhi", "Lahore", "Ludhiana"}


def rounded_key(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["dP", "dP_lo", "dP_hi"]:
        out[f"{col}_key"] = out[col].round(12)
    return out


def fdr_bool(pvals: np.ndarray, q: float = Q_FDR, method: str = "bh") -> np.ndarray:
    p = np.asarray(pvals, float)
    p = np.where(np.isfinite(p), p, 1.0)
    n = len(p)
    if n == 0:
        return np.array([], dtype=bool)
    factor = 1.0
    if method.lower() == "by":
        factor = float(np.sum(1.0 / np.arange(1, n + 1)))
    order = np.argsort(p)
    passed = p[order] <= q * (np.arange(1, n + 1)) / (n * factor)
    k = np.where(passed)[0].max() + 1 if passed.any() else 0
    out = np.zeros(n, dtype=bool)
    out[order[:k]] = True
    return out


def fdr_adjust(pvals: np.ndarray, method: str = "bh") -> np.ndarray:
    p = np.asarray(pvals, float)
    p = np.where(np.isfinite(p), p, 1.0)
    n = len(p)
    if n == 0:
        return np.array([], dtype=float)
    factor = 1.0
    if method.lower() == "by":
        factor = float(np.sum(1.0 / np.arange(1, n + 1)))
    order = np.argsort(p)
    ranked = p[order] * n * factor / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    ranked = np.minimum(ranked, 1.0)
    out = np.empty(n, dtype=float)
    out[order] = ranked
    return out


def simes_p(values: pd.Series) -> float:
    p = np.sort(np.asarray(values, float))
    p = np.where(np.isfinite(p), p, 1.0)
    m = len(p)
    if m == 0:
        return 1.0
    return float(np.minimum(1.0, np.min(m * p / np.arange(1, m + 1))))


def dP_draws_for_row(r: pd.Series, trend_draws: np.ndarray, sy_draws: np.ndarray) -> np.ndarray:
    dwtd = -(trend_draws * NYEARS / 100.0) / sy_draws
    new_wtd = np.maximum(float(r["wtd"]) + dwtd, 0.0)
    p0 = p_liquefaction(
        float(r["pgv"]),
        float(r["vs30"]),
        float(r["precip"]),
        float(r["dw_km"]),
        float(r["wtd"]),
    )
    p1 = p_liquefaction(
        float(r["pgv"]),
        float(r["vs30"]),
        float(r["precip"]),
        float(r["dw_km"]),
        new_wtd,
    )
    return np.asarray(p1 - p0, float)


def monte_carlo_material_probability() -> pd.DataFrame:
    """Replay the original Monte Carlo stream and retain material probabilities."""

    a = analyze_v2.load()
    clean = analyze_v2.gw_clean_flags(a["lon"].values, a["lat"].values)
    seis = a[
        (a["pga_475_g"] >= 0.05)
        & a["wtd"].notna()
        & a[analyze_v2.DRIVER].notna()
        & clean
    ].copy()
    rng = np.random.default_rng(RNG_SEED)
    records = []
    for _, r in seis.iterrows():
        tr = float(r[analyze_v2.DRIVER])
        se = max(float(r[analyze_v2.DRIVER_SE]) if pd.notna(r[analyze_v2.DRIVER_SE]) else 0.1, 1e-3)
        trs = rng.normal(tr, se, B)
        sys = rng.uniform(SY_LO, SY_HI, B)
        dps = dP_draws_for_row(r, trs, sys)
        if str(r["name"]) in HOTSPOT_NAMES:
            records.append(
                {
                    "name": r["name"],
                    "country": r["country"],
                    "mc_pr_abs_delta_p_ge_0p01": float(np.mean(np.abs(dps) >= MATERIAL)),
                    "mc_pr_delta_p_positive": float(np.mean(dps > 0)),
                    "mc_delta_p_05": float(np.percentile(dps, 5)),
                    "mc_delta_p_50": float(np.percentile(dps, 50)),
                    "mc_delta_p_95": float(np.percentile(dps, 95)),
                    "finite_monte_carlo_draws": B,
                    "rng_seed": RNG_SEED,
                    "specific_yield_prior": "Uniform(0.05,0.25)",
                }
            )
    return pd.DataFrame(records)


def build_zero_aware_block_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    spatial = rounded_key(pd.read_csv(DER / "city_results_spatial_r20.csv"))
    zero = rounded_key(pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv"))
    zcols = [
        "name",
        "country",
        "dP_key",
        "dP_lo_key",
        "dP_hi_key",
        "p_two_zero_aware",
        "fdr_bh_zero_aware",
        "fdr_by_zero_aware",
        "material_bh_zero_aware",
        "material_by_zero_aware",
    ]
    merged = spatial.merge(
        zero[zcols],
        on=["name", "country", "dP_key", "dP_lo_key", "dP_hi_key"],
        how="left",
        validate="one_to_one",
    )
    if merged["p_two_zero_aware"].isna().any():
        missing = merged.loc[merged["p_two_zero_aware"].isna(), ["name", "country", "dP"]]
        raise RuntimeError(f"Unmatched zero-aware rows:\n{missing.to_string(index=False)}")

    block_rows = []
    for block_type, col in [
        ("csr_grid_cell", "csr_grid_cell_id"),
        ("grace_scale_300km", "grace_scale_cluster_300km"),
    ]:
        for bid, g in merged.groupby(col):
            material = g[g["material_bh_zero_aware"]]
            block_rows.append(
                {
                    "block_type": block_type,
                    "block_id": str(bid),
                    "n_cities": int(len(g)),
                    "city_names": "; ".join(g.sort_values("population", ascending=False)["name"].astype(str)),
                    "p_simes_zero_aware": simes_p(g["p_two_zero_aware"]),
                    "population_weighted_delta_p": float(np.average(g["dP"], weights=g["population"].astype(float))),
                    "median_delta_p": float(g["dP"].median()),
                    "n_material_hotspots_zero_aware": int(len(material)),
                    "material_point_names_zero_aware": "; ".join(material["name"].astype(str)),
                    "n_fdr_sig_cities_zero_aware": int(g["fdr_bh_zero_aware"].sum()),
                }
            )
    blocks = pd.DataFrame(block_rows)
    blocks["block_fdr_bh_zero_aware"] = False
    blocks["block_fdr_by_zero_aware"] = False
    blocks["block_q_bh_zero_aware"] = np.nan
    blocks["block_q_by_zero_aware"] = np.nan
    for block_type, idx in blocks.groupby("block_type").groups.items():
        p = blocks.loc[idx, "p_simes_zero_aware"].values
        blocks.loc[idx, "block_fdr_bh_zero_aware"] = fdr_bool(p, Q_FDR, "bh")
        blocks.loc[idx, "block_fdr_by_zero_aware"] = fdr_bool(p, Q_FDR, "by")
        blocks.loc[idx, "block_q_bh_zero_aware"] = fdr_adjust(p, "bh")
        blocks.loc[idx, "block_q_by_zero_aware"] = fdr_adjust(p, "by")
    blocks = blocks.sort_values(
        ["block_type", "block_fdr_bh_zero_aware", "n_material_hotspots_zero_aware"],
        ascending=[True, False, False],
    )
    return merged, blocks


def build_downstream_audit(merged: pd.DataFrame, blocks: pd.DataFrame) -> pd.DataFrame:
    old_blocks = pd.read_csv(DER / "spatial_block_fdr_r20.csv")
    r31 = pd.read_csv(DER / "static_observed_triage_tier_change_r31.csv")
    rows = []
    rows.append(
        {
            "diagnostic": "city_fdr_detectable",
            "old_field": "fdr_sig",
            "old_count": int(merged["fdr_sig"].sum()),
            "zero_aware_field": "fdr_bh_zero_aware",
            "zero_aware_count": int(merged["fdr_bh_zero_aware"].sum()),
            "interpretation": "finite Monte Carlo exact-zero rows assigned p=1 and zero counts add-one corrected",
        }
    )
    rows.append(
        {
            "diagnostic": "city_material_bh",
            "old_field": "fdr_sig & |Delta P|>=0.01",
            "old_count": int((merged["fdr_sig"] & (merged["dP"].abs() >= MATERIAL)).sum()),
            "zero_aware_field": "material_bh_zero_aware",
            "zero_aware_count": int(merged["material_bh_zero_aware"].sum()),
            "interpretation": "baseline material count after zero-aware p-value handling",
        }
    )
    rows.append(
        {
            "diagnostic": "city_material_by",
            "old_field": "not reported as primary",
            "old_count": np.nan,
            "zero_aware_field": "material_by_zero_aware",
            "zero_aware_count": int(merged["material_by_zero_aware"].sum()),
            "interpretation": "dependency-aware sensitivity retained as stricter guardrail",
        }
    )
    for btype in ["csr_grid_cell", "grace_scale_300km"]:
        old_count = int(old_blocks.loc[old_blocks["block_type"] == btype, "block_fdr_sig"].sum())
        zero_count = int(blocks.loc[blocks["block_type"] == btype, "block_fdr_bh_zero_aware"].sum())
        rows.append(
            {
                "diagnostic": f"{btype}_block_fdr",
                "old_field": "R20 Simes/BH using raw p_two",
                "old_count": old_count,
                "zero_aware_field": "R33 Simes/BH using p_two_zero_aware",
                "zero_aware_count": zero_count,
                "interpretation": "spatial block FDR should use the same zero-aware city p-values as downstream city diagnostics",
            }
        )
    rows.append(
        {
            "diagnostic": "static_counterfactual_A_B_followup",
            "old_field": "not applicable in static counterfactual",
            "old_count": 0,
            "zero_aware_field": "R31 observed_tier_bh A/B",
            "zero_aware_count": int(r31["ab_followup_bh"].sum()),
            "interpretation": "non-regulatory operational payload; not a hazard-class transition",
        }
    )
    return pd.DataFrame(rows)


def build_materiality_table(mc: pd.DataFrame) -> pd.DataFrame:
    sy = pd.read_csv(DER / "specific_yield_thresholds_r28.csv")
    prod = pd.read_csv(DER / "product_consensus_hotspots_r23.csv")
    ghsl = pd.read_csv(DER / "hotspot_ghsl_polygon_robustness_r21.csv")
    spatial = (
        pd.read_csv(DER / "city_results_spatial_r20.csv")
        .loc[lambda d: d["name"].isin(HOTSPOT_NAMES)]
        .drop_duplicates(["name", "country"])
    )

    base = (
        sy[sy["name"].isin(HOTSPOT_NAMES)]
        .merge(
            prod[
                [
                    "name",
                    "country",
                    "gsfc_recent_dP",
                    "gsfc_recent_p",
                    "gsfc_recent_material",
                    "gsfc_recent_near_material",
                    "csr_gsfc_recent_sign_match",
                    "csr_gsfc_theilsen_sign_match",
                ]
            ],
            on=["name", "country"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            ghsl[["name", "country", "ghsl_uc_id", "ghsl_uc_name", "n_material_point_hotspots"]],
            on=["name", "country"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            spatial[["name", "country", "metro_cluster_50km", "grace_scale_cluster_300km", "dP_lo", "dP_hi"]],
            on=["name", "country"],
            how="left",
            validate="one_to_one",
        )
        .merge(mc, on=["name", "country"], how="left", validate="one_to_one")
    )
    base["gsfc_statistical_sign_support_p05"] = (
        base["csr_gsfc_recent_sign_match"].astype(bool) & (base["gsfc_recent_p"].astype(float) < 0.05)
    )
    base["baseline_materiality_wording"] = "baseline S_y=0.10 CSR material; MC prior materiality probability reported separately"
    out_cols = [
        "name",
        "country",
        "direction",
        "regional_setting",
        "baseline_dP_sy010",
        "dP_lo",
        "dP_hi",
        "sy_material_threshold",
        "mc_pr_abs_delta_p_ge_0p01",
        "mc_delta_p_05",
        "mc_delta_p_50",
        "mc_delta_p_95",
        "gsfc_recent_dP",
        "gsfc_recent_p",
        "gsfc_statistical_sign_support_p05",
        "gsfc_recent_material",
        "gsfc_recent_near_material",
        "ghsl_uc_name",
        "n_material_point_hotspots",
        "metro_cluster_50km",
        "grace_scale_cluster_300km",
        "baseline_materiality_wording",
    ]
    return base[out_cols].sort_values("baseline_dP_sy010", ascending=False)


def build_independence_counts() -> pd.DataFrame:
    r31 = pd.read_csv(DER / "static_observed_triage_tier_change_r31.csv")
    spatial = pd.read_csv(DER / "city_results_spatial_r20.csv")
    ghsl = pd.read_csv(DER / "ghsl_urban_centre_matches_r21.csv")
    df = r31.merge(
        spatial[["name", "country", "lat", "lon", "metro_cluster_50km", "grace_scale_cluster_300km"]],
        on=["name", "country", "lat", "lon"],
        how="left",
        validate="one_to_one",
    ).merge(
        ghsl[["name", "country", "lat", "lon", "ghsl_uc_id", "ghsl_uc_name", "ghsl_matched"]],
        on=["name", "country", "lat", "lon"],
        how="left",
        validate="one_to_one",
    )
    rows = []
    for method, fdr_col in [
        ("BH zero-aware", "fdr_bh_zero_aware"),
        ("BY zero-aware", "fdr_by_zero_aware"),
    ]:
        for threshold in [0.005, 0.0075, 0.01]:
            mask = df[fdr_col].astype(bool) & (df["dP"].abs() >= threshold)
            g = df[mask].copy()
            if len(g):
                group_counts = g.groupby("grace_scale_cluster_300km").size()
                largest_300km_n = int(group_counts.max())
                largest_300km_id = str(group_counts.idxmax())
            else:
                largest_300km_n = 0
                largest_300km_id = ""
            rows.append(
                {
                    "method": method,
                    "abs_delta_p_threshold": threshold,
                    "n_point_city_units": int(len(g)),
                    "n_50km_metro_clusters": int(g["metro_cluster_50km"].nunique()),
                    "n_ghsl_urban_centres": int(g["ghsl_uc_id"].nunique()),
                    "n_300km_regional_groups": int(g["grace_scale_cluster_300km"].nunique()),
                    "n_increase_side": int((g["dP"] > 0).sum()),
                    "n_depletion_side": int((g["dP"] < 0).sum()),
                    "largest_300km_group_id": largest_300km_id,
                    "largest_300km_group_n_point_cities": largest_300km_n,
                    "point_city_names": "; ".join(g.sort_values("dP", ascending=False)["name"].astype(str)),
                }
            )
    return pd.DataFrame(rows)


def build_product_support_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    prod = pd.read_csv(DER / "product_consensus_hotspots_r23.csv")
    local_status = {
        "Yokohama": "local sign support: Yokohama 20/23 rising; Tokyo Bay official summaries rising",
        "Bhayandar": "local contradiction/guardrail: Mumbai station evidence supports depletion",
        "Mumbai": "local contradiction/guardrail: Mumbai station evidence supports depletion",
        "Delhi": "local sign support: Delhi station literature supports depletion",
        "Lahore": "local sign support: GRACE/borehole/InSAR literature supports depletion",
        "Ludhiana": "regional sign support: Punjab/NW India depletion context",
    }
    out = prod.copy()
    out["gsfc_direction_match"] = out["csr_gsfc_recent_sign_match"].astype(bool) & out[
        "csr_gsfc_theilsen_sign_match"
    ].astype(bool)
    out["gsfc_statistical_sign_support_p05"] = out["gsfc_direction_match"] & (
        out["gsfc_recent_p"].astype(float) < 0.05
    )
    out["gsfc_material_support"] = out["gsfc_recent_material"].astype(bool)
    out["gsfc_near_material_support"] = out["gsfc_recent_near_material"].astype(bool)
    out["local_evidence_status"] = out["name"].map(local_status)
    out["safe_claim_class"] = np.select(
        [
            out["gsfc_material_support"],
            out["gsfc_statistical_sign_support_p05"],
            out["gsfc_direction_match"],
        ],
        [
            "independent product-material support",
            "independent product statistical sign support only",
            "independent product direction match only",
        ],
        default="CSR-only candidate",
    )
    cols = [
        "name",
        "country",
        "direction",
        "csr_dP",
        "csr_material",
        "gsfc_recent_dP",
        "gsfc_recent_p",
        "gsfc_direction_match",
        "gsfc_statistical_sign_support_p05",
        "gsfc_material_support",
        "gsfc_near_material_support",
        "distance_to_coast_km",
        "coastal_lt50km",
        "local_evidence_status",
        "safe_claim_class",
        "manuscript_interpretation",
    ]
    table = out[cols].sort_values("csr_dP", ascending=False)
    summary_rows = [
        {
            "metric": "CSR-material baseline units",
            "count": int(len(out)),
            "denominator": int(len(out)),
            "interpretation": "primary product baseline at S_y=0.10",
        },
        {
            "metric": "GSFC direction match",
            "count": int(out["gsfc_direction_match"].sum()),
            "denominator": int(len(out)),
            "interpretation": "OLS and Theil-Sen signs match CSR baseline",
        },
        {
            "metric": "GSFC statistical sign support p<0.05",
            "count": int(out["gsfc_statistical_sign_support_p05"].sum()),
            "denominator": int(len(out)),
            "interpretation": "direction match plus GSFC OLS trend p<0.05",
        },
        {
            "metric": "GSFC material support",
            "count": int(out["gsfc_material_support"].sum()),
            "denominator": int(len(out)),
            "interpretation": "independent-product magnitude crosses |Delta P|>=0.01",
        },
        {
            "metric": "positive coastal GSFC material support",
            "count": int((out["direction"].str.contains("increase") & out["gsfc_material_support"]).sum()),
            "denominator": int(out["direction"].str.contains("increase").sum()),
            "interpretation": "positive coastal screens remain sign-supported/candidate, not independent material discoveries",
        },
    ]
    return table, pd.DataFrame(summary_rows)


def build_local_sign_tests() -> pd.DataFrame:
    yok = json.loads((DER / "yokohama_groundwater_summary_r24.json").read_text(encoding="utf-8"))
    tokyo = pd.read_csv(DER / "tokyo_bay_groundwater_evidence_summary_r25.csv")
    rows = []

    def add_row(layer: str, n_positive: int, n_total: int, window: str, source: str, interpretation: str) -> None:
        one = binomtest(n_positive, n_total, 0.5, alternative="greater")
        two = binomtest(n_positive, n_total, 0.5, alternative="two-sided")
        rows.append(
            {
                "evidence_layer": layer,
                "n_positive_or_rising": int(n_positive),
                "n_total_units": int(n_total),
                "positive_fraction": float(n_positive / n_total) if n_total else np.nan,
                "binomial_p_one_sided_positive": float(one.pvalue),
                "binomial_p_two_sided": float(two.pvalue),
                "window": window,
                "source": source,
                "safe_interpretation": interpretation,
            }
        )

    add_row(
        "Yokohama municipal trend-qualified wells",
        int(yok["n_positive_slope"]),
        int(yok["n_stations_trend"]),
        str(yok["window"]),
        str(yok["source"]),
        "supports local positive groundwater sign around Yokohama; not a magnitude or management-attribution calibration",
    )
    for _, r in tokyo.iterrows():
        n_total = int(r["n_units"])
        n_pos = int(r["n_positive"])
        add_row(
            str(r["evidence_layer"]),
            n_pos,
            n_total,
            str(r["window"]),
            str(r["source_url"]),
            str(r["safe_interpretation"]) + "; descriptive sign test only",
        )
    return pd.DataFrame(rows)


def main() -> None:
    mc = monte_carlo_material_probability()
    merged, blocks = build_zero_aware_block_tables()
    downstream = build_downstream_audit(merged, blocks)
    materiality = build_materiality_table(mc)
    independence = build_independence_counts()
    product, product_summary = build_product_support_table()
    local = build_local_sign_tests()

    blocks.to_csv(DER / "spatial_block_fdr_zero_aware_r33.csv", index=False)
    downstream.to_csv(DER / "zero_aware_downstream_audit_r33.csv", index=False)
    materiality.to_csv(DER / "materiality_uncertainty_table_r33.csv", index=False)
    independence.to_csv(DER / "independence_scale_counts_r33.csv", index=False)
    product.to_csv(DER / "product_support_table_r33.csv", index=False)
    product_summary.to_csv(DER / "product_support_summary_r33.csv", index=False)
    local.to_csv(DER / "local_evidence_sign_tests_r33.csv", index=False)

    bh_005 = independence[
        (independence["method"] == "BH zero-aware") & (independence["abs_delta_p_threshold"] == 0.005)
    ].iloc[0]
    summary = {
        "finite_monte_carlo_draws": B,
        "rng_seed": RNG_SEED,
        "zero_aware_city_fdr_count": int(merged["fdr_bh_zero_aware"].sum()),
        "zero_aware_city_material_bh_count": int(merged["material_bh_zero_aware"].sum()),
        "zero_aware_city_material_by_count": int(merged["material_by_zero_aware"].sum()),
        "zero_aware_block_fdr_counts": {
            btype: int(g["block_fdr_bh_zero_aware"].sum())
            for btype, g in blocks.groupby("block_type")
        },
        "ab_followup_bh_threshold_0p005": {
            "n_point_city_units": int(bh_005["n_point_city_units"]),
            "n_50km_metro_clusters": int(bh_005["n_50km_metro_clusters"]),
            "n_ghsl_urban_centres": int(bh_005["n_ghsl_urban_centres"]),
            "n_300km_regional_groups": int(bh_005["n_300km_regional_groups"]),
            "n_increase_side": int(bh_005["n_increase_side"]),
            "n_depletion_side": int(bh_005["n_depletion_side"]),
            "largest_300km_group_n_point_cities": int(bh_005["largest_300km_group_n_point_cities"]),
        },
        "product_support_counts": {
            row["metric"]: {
                "count": int(row["count"]),
                "denominator": int(row["denominator"]),
            }
            for _, row in product_summary.iterrows()
        },
        "hotspot_materiality_probability_range": {
            "min": float(materiality["mc_pr_abs_delta_p_ge_0p01"].min()),
            "max": float(materiality["mc_pr_abs_delta_p_ge_0p01"].max()),
        },
        "outputs": [
            "spatial_block_fdr_zero_aware_r33.csv",
            "zero_aware_downstream_audit_r33.csv",
            "materiality_uncertainty_table_r33.csv",
            "independence_scale_counts_r33.csv",
            "product_support_table_r33.csv",
            "product_support_summary_r33.csv",
            "local_evidence_sign_tests_r33.csv",
        ],
    }
    (DER / "statistical_object_audit_summary_r33.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Saved R33 statistical-object audit tables.")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
