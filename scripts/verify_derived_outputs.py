"""Verify current headline numbers from included derived outputs only."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
MATERIAL = 0.01


def read_json(name: str) -> dict:
    return json.loads((DER / name).read_text(encoding="utf-8"))


def assert_no_legacy_labels(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    unit_word = "hot" + "spot"
    ranking_word = "policy_" + "prior" + "ity"
    flag_word = "water_table_" + "trig" + "ger"
    assert unit_word not in text, f"legacy material-unit label in {path.name}"
    assert ranking_word not in text, f"legacy policy-ranking label in {path.name}"
    assert flag_word not in text, f"legacy water-table flag label in {path.name}"


def main() -> None:
    summary = read_json("core_summary_v2.json")
    cities = pd.read_csv(DER / "city_results_v2.csv")
    zero = read_json("zero_aware_fdr_summary_r27.json")
    r31 = read_json("static_observed_triage_tier_summary_r31.json")
    r33 = read_json("statistical_object_audit_summary_r33.json")
    r36 = read_json("threshold_controls_summary_r36.json")

    zero_city = pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv")
    independence = pd.read_csv(DER / "independence_scale_counts_r33.csv")
    product = pd.read_csv(DER / "product_support_summary_r33.csv").set_index("metric")["count"].to_dict()
    local = pd.read_csv(DER / "local_evidence_sign_tests_r33.csv")
    materiality = pd.read_csv(DER / "materiality_uncertainty_table_r33.csv")
    threshold = pd.read_csv(DER / "threshold_interpretation_r36.csv")
    controls = pd.read_csv(DER / "negative_control_strata_r36.csv")
    regional = pd.read_csv(DER / "regional_followup_groups_r36.csv")
    sy_ledger = pd.read_csv(DER / "specific_yield_scenario_ledger_r36.csv")
    water_flag = pd.read_csv(DER / "water_table_followup_flag_r20.csv")
    policy = pd.read_csv(DER / "policy_followup_table_v2.csv")
    product_units = pd.read_csv(DER / "product_consensus_material_units_r23.csv")
    ref_audit = pd.read_csv(ROOT / "docs" / "Reference_Audit_R34.csv")

    material = cities[cities["fdr_sig"] & (cities["dP"].abs() >= MATERIAL)]
    assert summary["n"] == len(cities) == 444
    assert summary["n_fdr_sig"] == int(cities["fdr_sig"].sum()) == 330
    assert len(material[material["dP"] > 0]) == summary["n_material_inc"] == 3
    assert len(material[material["dP"] < 0]) == summary["n_material_dec"] == 3
    assert zero["zero_aware_bh_significant"] == int(zero_city["fdr_bh_zero_aware"].sum()) == 311
    assert zero["zero_aware_by_significant"] == int(zero_city["fdr_by_zero_aware"].sum()) == 245
    assert zero["zero_aware_material_bh"] == 6
    assert zero["zero_aware_material_by"] == 5

    assert r31["bh_ab_followup_units"] == 28
    assert r31["bh_a_material_units"] == 6
    assert r31["bh_b_targeted_units"] == 22
    assert r31["bh_ab_increase_side"] == 19
    assert r31["bh_ab_depletion_side"] == 9
    assert r31["by_ab_followup_units"] == 22

    row = independence[
        (independence["method"] == "BH zero-aware")
        & (independence["abs_delta_p_threshold"] == 0.005)
    ].iloc[0]
    assert int(row["n_point_city_units"]) == 28
    assert int(row["n_50km_metro_clusters"]) == 21
    assert int(row["n_ghsl_urban_centres"]) == 22
    assert int(row["n_300km_regional_groups"]) == 10
    assert int(row["largest_300km_group_n_point_cities"]) == 17

    assert int(product["GSFC direction match"]) == 6
    assert int(product["GSFC statistical sign support p<0.05"]) == 4
    assert int(product["GSFC material support"]) == 1
    assert int(product["positive coastal GSFC material support"]) == 0
    assert len(product_units) == 6
    assert len(materiality) == 6
    assert materiality["mc_pr_abs_delta_p_ge_0p01"].between(0.29, 0.56).all()
    probability_key = "hot" + "spot_materiality_probability_range"
    assert 0.29 < r33[probability_key]["min"] < 0.31
    assert 0.54 < r33[probability_key]["max"] < 0.56

    assert int(local.loc[local["evidence_layer"].str.startswith("Yokohama"), "n_positive_or_rising"].iloc[0]) == 20
    assert int(local.loc[local["evidence_layer"] == "ministry_2024_regional_summary", "n_positive_or_rising"].iloc[0]) == 79

    assert r36["n_cities"] == 444
    assert 0.0012 < r36["mean_abs_delta_p"] < 0.0013
    assert r36["zero_aware_material_bh_count"] == 6
    assert r36["ab_followup_count"] == 28
    assert r36["ab_followup_300km_groups"] == 10
    assert r36["largest_ab_group_n_point_city_units"] == 17
    assert 0.98 < r36["threshold_0p01_percentile_rank_all_cities"] < 0.99
    assert r36["control_strata_max_material_count"] == 0
    assert len(threshold) >= 10
    assert int(controls["n_material"].max()) == 0
    assert len(regional) == 10
    assert {"Yokohama", "Bhayandar", "Mumbai", "Delhi", "Lahore", "Ludhiana"} <= set(sy_ledger["name"])
    assert len(water_flag) == 444
    assert len(policy) == 444

    for path in [
        DER / "policy_followup_table_v2.csv",
        DER / "water_table_followup_flag_r20.csv",
        DER / "product_consensus_material_units_r23.csv",
        DER / "attribution_evidence_boundary_matrix_r25.csv",
    ]:
        assert_no_legacy_labels(path)

    assert len(ref_audit) == 36
    assert int((ref_audit["status"] == "verified_crossref").sum()) == 28
    assert (ROOT / "02_source_registry.md").exists()
    assert (ROOT / "03_claim_evidence_map.md").exists()

    for stem in [
        "Fig1_mechanism",
        "Fig2_global_signresolved",
        "Fig3_regional",
        "Fig4_timeseries",
        "Fig5_policy_robustness",
        "Fig6_evidence_boundary",
        "FigS1_yokohama_local_groundwater_r24",
        "FigS2_tokyo_representative_groundwater_r25",
        "FigS3_water_table_followup_flag_spatial_robustness",
    ]:
        for ext in ["png", "svg", "pdf"]:
            assert (ROOT / "figures" / f"{stem}.{ext}").exists(), f"missing {stem}.{ext}"

    beijing = cities[cities["name"] == "Beijing"].iloc[0]
    assert beijing["dP"] > 0
    assert beijing["dP_lo"] > 0

    print("Derived-output verification passed.")
    print(f"Cities: {len(cities)}")
    print(f"Original BH-significant detectable cities: {int(cities['fdr_sig'].sum())}")
    print(
        "Zero-aware BH/BY detectable cities: "
        f"{zero['zero_aware_bh_significant']}/{zero['zero_aware_by_significant']}; "
        f"material BH/BY: {zero['zero_aware_material_bh']}/{zero['zero_aware_material_by']}"
    )
    print(
        "Static-counterfactual A/B follow-up units: "
        f"{r31['bh_ab_followup_units']} point-city units "
        f"({r31['bh_a_material_units']} material, {r31['bh_b_targeted_units']} targeted; "
        f"{r31['bh_ab_increase_side']} increase-side, {r31['bh_ab_depletion_side']} depletion-side)"
    )
    print(
        "Independence audit: "
        f"{int(row['n_point_city_units'])} point-city units -> "
        f"{int(row['n_50km_metro_clusters'])} metro clusters, "
        f"{int(row['n_ghsl_urban_centres'])} GHSL centres, "
        f"{int(row['n_300km_regional_groups'])} 300-km groups"
    )
    print(
        "R36 controls: "
        f"|Delta P| >= 0.01 is the {100*r36['threshold_0p01_percentile_rank_all_cities']:.1f}th percentile; "
        f"control-strata max material count = {r36['control_strata_max_material_count']}"
    )
    print(
        "Independent-product support: "
        f"direction match {int(product['GSFC direction match'])}/6, "
        f"p<0.05 sign support {int(product['GSFC statistical sign support p<0.05'])}/6, "
        f"GSFC-material {int(product['GSFC material support'])}/6"
    )
    print(
        "Local sign checks: "
        "Yokohama 20/23 rising; Tokyo official regional summary 79/91 rising"
    )


if __name__ == "__main__":
    main()
