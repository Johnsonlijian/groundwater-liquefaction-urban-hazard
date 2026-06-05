"""R31 static-counterfactual versus observed-storage triage update.

This diagnostic answers a narrow reviewer-facing question: if a static
water-table screen is the counterfactual baseline, how many point-city exposure
units receive a non-regulatory follow-up flag after applying the observed
storage-derived water-table perturbation?

The tiers are analytical effect-size bins, not engineering or regulatory risk
classes. They reuse the R27 zero-aware finite-Monte-Carlo FDR correction.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
MATERIAL = 0.01
TARGETED = 0.005


def rounded_key(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["dP", "dP_lo", "dP_hi"]:
        out[f"{col}_key"] = out[col].round(12)
    return out


def tier_from_flags(d_p: float, fdr: bool, material: bool) -> str:
    if material:
        return "A material adjustment"
    if bool(fdr) and abs(float(d_p)) >= TARGETED:
        return "B targeted follow-up"
    if bool(fdr):
        return "C detectable sub-material update"
    return "D static-routine baseline"


def tier_rank(tier: str) -> int:
    return {"D": 0, "C": 1, "B": 2, "A": 3}[tier[0]]


def direction_label(d_p: float) -> str:
    if d_p > 0:
        return "increase-side"
    if d_p < 0:
        return "depletion-side"
    return "near-zero"


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    policy = rounded_key(pd.read_csv(DER / "policy_priority_table_v2.csv"))
    zero = rounded_key(pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv"))

    zero_keep = [
        "name",
        "country",
        "dP_key",
        "dP_lo_key",
        "dP_hi_key",
        "p_two_zero_aware",
        "zero_exact_dP",
        "fdr_bh_zero_aware",
        "fdr_by_zero_aware",
        "material_bh_zero_aware",
        "material_by_zero_aware",
    ]
    merged = policy.merge(
        zero[zero_keep],
        on=["name", "country", "dP_key", "dP_lo_key", "dP_hi_key"],
        how="left",
        validate="one_to_one",
    )
    if merged["fdr_bh_zero_aware"].isna().any():
        missing = merged.loc[merged["fdr_bh_zero_aware"].isna(), ["name", "country", "dP"]]
        raise RuntimeError(f"Unmatched zero-aware rows:\n{missing.to_string(index=False)}")

    merged["static_counterfactual_tier"] = "D static-routine baseline"
    merged["observed_tier_bh"] = [
        tier_from_flags(d_p, fdr, mat)
        for d_p, fdr, mat in zip(
            merged["dP"],
            merged["fdr_bh_zero_aware"],
            merged["material_bh_zero_aware"],
        )
    ]
    merged["observed_tier_by"] = [
        tier_from_flags(d_p, fdr, mat)
        for d_p, fdr, mat in zip(
            merged["dP"],
            merged["fdr_by_zero_aware"],
            merged["material_by_zero_aware"],
        )
    ]
    merged["observed_rank_bh"] = merged["observed_tier_bh"].map(tier_rank)
    merged["observed_rank_by"] = merged["observed_tier_by"].map(tier_rank)
    merged["direction_side"] = merged["dP"].map(direction_label)
    merged["ab_followup_bh"] = merged["observed_tier_bh"].str.startswith(("A", "B"))
    merged["ab_followup_by"] = merged["observed_tier_by"].str.startswith(("A", "B"))
    merged["detectable_update_bh"] = merged["observed_tier_bh"].str.startswith(("A", "B", "C"))
    merged["detectable_update_by"] = merged["observed_tier_by"].str.startswith(("A", "B", "C"))
    merged["population_million"] = merged["population"] / 1e6

    row_cols = [
        "name",
        "country",
        "lat",
        "lon",
        "population",
        "population_million",
        "P0",
        "dP",
        "dP_lo",
        "dP_hi",
        "p_two_zero_aware",
        "zero_exact_dP",
        "fdr_bh_zero_aware",
        "fdr_by_zero_aware",
        "material_bh_zero_aware",
        "material_by_zero_aware",
        "static_counterfactual_tier",
        "observed_tier_bh",
        "observed_tier_by",
        "direction_side",
        "ab_followup_bh",
        "ab_followup_by",
        "detectable_update_bh",
        "detectable_update_by",
        "screening_tier",
        "policy_action",
        "susceptibility_proxy_count",
    ]
    rows = merged.sort_values(["observed_rank_bh", "dP"], ascending=[False, False])[
        row_cols
    ]

    count_rows = []
    for method, tier_col, ab_col, det_col in [
        ("BH zero-aware", "observed_tier_bh", "ab_followup_bh", "detectable_update_bh"),
        ("BY zero-aware", "observed_tier_by", "ab_followup_by", "detectable_update_by"),
    ]:
        for tier, g in merged.groupby(tier_col, dropna=False):
            count_rows.append(
                {
                    "method": method,
                    "tier": tier,
                    "n_point_city_units": int(len(g)),
                    "population_million": float(g["population_million"].sum()),
                    "n_increase_side": int((g["dP"] > 0).sum()),
                    "n_depletion_side": int((g["dP"] < 0).sum()),
                    "n_near_zero": int((g["dP"] == 0).sum()),
                }
            )
        for label, mask in [
            ("A_or_B_followup", merged[ab_col]),
            ("detectable_A_B_C_update", merged[det_col]),
        ]:
            g = merged[mask]
            count_rows.append(
                {
                    "method": method,
                    "tier": label,
                    "n_point_city_units": int(len(g)),
                    "population_million": float(g["population_million"].sum()),
                    "n_increase_side": int((g["dP"] > 0).sum()),
                    "n_depletion_side": int((g["dP"] < 0).sum()),
                    "n_near_zero": int((g["dP"] == 0).sum()),
                }
            )
    counts = pd.DataFrame(count_rows)

    trigger = pd.read_csv(DER / "water_table_trigger_r20.csv")
    wtd = policy.merge(
        trigger[
            [
                "name",
                "country",
                "lat",
                "lon",
                "recent_cumulative_water_table_rise_m_sy010",
            ]
        ],
        on=["name", "country", "lat", "lon"],
        validate="one_to_one",
    )
    wtd["static_shallow_wtd_proxy_le_10m"] = wtd["wtd"] <= 10
    wtd["observed_wtd_sy010"] = np.maximum(
        wtd["wtd"] - wtd["recent_cumulative_water_table_rise_m_sy010"], 0.0
    )
    wtd["observed_shallow_wtd_proxy_le_10m"] = wtd["observed_wtd_sy010"] <= 10
    wtd["shallow_proxy_crossing"] = (
        wtd["static_shallow_wtd_proxy_le_10m"]
        != wtd["observed_shallow_wtd_proxy_le_10m"]
    )
    wtd["shallow_proxy_crossing_direction"] = np.select(
        [
            (~wtd["static_shallow_wtd_proxy_le_10m"])
            & wtd["observed_shallow_wtd_proxy_le_10m"],
            wtd["static_shallow_wtd_proxy_le_10m"]
            & (~wtd["observed_shallow_wtd_proxy_le_10m"]),
        ],
        ["becomes_shallow_proxy", "leaves_shallow_proxy"],
        default="no_crossing",
    )
    wtd_cols = [
        "name",
        "country",
        "lat",
        "lon",
        "population",
        "wtd",
        "recent_cumulative_water_table_rise_m_sy010",
        "observed_wtd_sy010",
        "static_shallow_wtd_proxy_le_10m",
        "observed_shallow_wtd_proxy_le_10m",
        "shallow_proxy_crossing",
        "shallow_proxy_crossing_direction",
        "dP",
        "fdr_sig",
    ]
    wtd_crossings = wtd.loc[wtd["shallow_proxy_crossing"], wtd_cols].sort_values(
        "recent_cumulative_water_table_rise_m_sy010", ascending=False
    )

    bh_ab = merged[merged["ab_followup_bh"]]
    by_ab = merged[merged["ab_followup_by"]]
    bh_det = merged[merged["detectable_update_bh"]]
    by_det = merged[merged["detectable_update_by"]]
    summary = {
        "n_cities": int(len(merged)),
        "definition": (
            "Static counterfactual is D for all cities; observed tiers are analytical "
            "effect-size bins using R27 zero-aware FDR. Tiers are non-regulatory "
            "follow-up flags, not engineering hazard classes."
        ),
        "bh_ab_followup_units": int(len(bh_ab)),
        "bh_a_material_units": int((merged["observed_tier_bh"] == "A material adjustment").sum()),
        "bh_b_targeted_units": int((merged["observed_tier_bh"] == "B targeted follow-up").sum()),
        "bh_c_detectable_units": int(
            (merged["observed_tier_bh"] == "C detectable sub-material update").sum()
        ),
        "bh_detectable_a_b_c_units": int(len(bh_det)),
        "bh_ab_increase_side": int((bh_ab["dP"] > 0).sum()),
        "bh_ab_depletion_side": int((bh_ab["dP"] < 0).sum()),
        "bh_ab_population_million": float(bh_ab["population_million"].sum()),
        "bh_detectable_population_million": float(bh_det["population_million"].sum()),
        "by_ab_followup_units": int(len(by_ab)),
        "by_a_material_units": int((merged["observed_tier_by"] == "A material adjustment").sum()),
        "by_b_targeted_units": int((merged["observed_tier_by"] == "B targeted follow-up").sum()),
        "by_c_detectable_units": int(
            (merged["observed_tier_by"] == "C detectable sub-material update").sum()
        ),
        "by_detectable_a_b_c_units": int(len(by_det)),
        "by_ab_increase_side": int((by_ab["dP"] > 0).sum()),
        "by_ab_depletion_side": int((by_ab["dP"] < 0).sum()),
        "by_ab_population_million": float(by_ab["population_million"].sum()),
        "wtd_proxy_crossing_units_sy010": int(len(wtd_crossings)),
        "wtd_proxy_becomes_shallow_units_sy010": int(
            (wtd_crossings["shallow_proxy_crossing_direction"] == "becomes_shallow_proxy").sum()
        ),
        "wtd_proxy_leaves_shallow_units_sy010": int(
            (wtd_crossings["shallow_proxy_crossing_direction"] == "leaves_shallow_proxy").sum()
        ),
        "recommended_headline": (
            f"Under the zero-aware BH screen, observed storage-derived water-table change "
            f"moves {len(bh_ab)} point-city exposure units from the static counterfactual "
            f"into A/B follow-up tiers ({int((merged['observed_tier_bh'] == 'A material adjustment').sum())} material, "
            f"{int((merged['observed_tier_bh'] == 'B targeted follow-up').sum())} targeted; "
            f"{int((bh_ab['dP'] > 0).sum())} increase-side and {int((bh_ab['dP'] < 0).sum())} depletion-side)."
        ),
    }
    return rows, counts, summary, wtd_crossings


def main() -> None:
    rows, counts, summary, wtd_crossings = build_tables()
    rows.to_csv(DER / "static_observed_triage_tier_change_r31.csv", index=False)
    counts.to_csv(DER / "static_observed_triage_tier_counts_r31.csv", index=False)
    wtd_crossings.to_csv(DER / "static_observed_wtd_proxy_crossings_r31.csv", index=False)
    (DER / "static_observed_triage_tier_summary_r31.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
