"""Verify headline numbers from included derived outputs only."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
MATERIAL = 0.01


def main() -> None:
    summary = json.loads((DER / "core_summary_v2.json").read_text(encoding="utf-8"))
    cities = pd.read_csv(DER / "city_results_v2.csv")
    hotspots = pd.read_csv(DER / "hotspot_table.csv")
    grid = pd.read_csv(DER / "sensitivity_grid_v2.csv")
    envelope = pd.read_csv(DER / "hotspot_sensitivity_envelope_v2.csv")
    city_grid = pd.read_csv(DER / "hotspot_sensitivity_city_grid_v2.csv")
    effects = pd.read_csv(DER / "sensitivity_parameter_effects_v2.csv")
    policy = pd.read_csv(DER / "policy_priority_table_v2.csv")
    exposure = pd.read_csv(DER / "policy_exposure_summary_v2.csv")
    r20 = json.loads((DER / "r20_spatial_trigger_summary.json").read_text(encoding="utf-8"))
    spatial = pd.read_csv(DER / "city_results_spatial_r20.csv")
    metro = pd.read_csv(DER / "metro_deduplication_r20.csv")
    blocks = pd.read_csv(DER / "spatial_block_fdr_r20.csv")
    coastal = pd.read_csv(DER / "coastal_robustness_r20.csv")
    signs = pd.read_csv(DER / "hotspot_driver_sign_robustness_r20.csv")
    trigger = pd.read_csv(DER / "water_table_trigger_r20.csv")
    external = pd.read_csv(DER / "external_product_status_r20.csv")
    r21 = json.loads((DER / "r21_multi_product_polygon_summary.json").read_text(encoding="utf-8"))
    ghsl_matches = pd.read_csv(DER / "ghsl_urban_centre_matches_r21.csv")
    ghsl_aggregates = pd.read_csv(DER / "ghsl_urban_centre_aggregates_r21.csv")
    hotspot_ghsl = pd.read_csv(DER / "hotspot_ghsl_polygon_robustness_r21.csv")
    gsfc = pd.read_csv(DER / "gsfc_city_trends_r21.csv")
    multiproduct = pd.read_csv(DER / "multi_product_sign_robustness_r21.csv")
    r21_status = pd.read_csv(DER / "r21_external_data_status.csv")
    r23 = json.loads((DER / "product_consensus_summary_r23.json").read_text(encoding="utf-8"))
    product_consensus = pd.read_csv(DER / "product_consensus_hotspots_r23.csv")
    r24 = json.loads((DER / "r24_local_evidence_summary.json").read_text(encoding="utf-8"))
    jpl_r24 = pd.read_csv(DER / "r24_jpl_cri_access_status.csv")
    yok_trends = pd.read_csv(DER / "yokohama_groundwater_trends_r24.csv")
    yok_monthly = pd.read_csv(DER / "yokohama_groundwater_monthly_r24.csv")
    local_registry = pd.read_csv(DER / "local_groundwater_evidence_registry_r24.csv")
    attribution_r24 = pd.read_csv(DER / "attribution_confidence_matrix_r24.csv")
    r25 = json.loads((DER / "r25_evidence_deepening_summary.json").read_text(encoding="utf-8"))
    tokyo_summary = pd.read_csv(DER / "tokyo_bay_groundwater_evidence_summary_r25.csv")
    tokyo_trends = pd.read_csv(DER / "tokyo_representative_groundwater_trends_r25.csv")
    tokyo_levels = pd.read_csv(DER / "tokyo_representative_groundwater_levels_r25.csv")
    tokyo_2016 = pd.read_csv(DER / "tokyo_open_data_table5_groundwater_2016_r25.csv")
    tokyo_2022 = pd.read_csv(DER / "tokyo_2022_pdf_table5_extracted_rows_r25.csv")
    cgwb_r25 = pd.read_csv(DER / "cgwb_access_retry_status_r25.csv")
    mumbai_r25 = pd.read_csv(DER / "mumbai_bhayandar_evidence_boundary_r25.csv")
    jpl_r25 = pd.read_csv(DER / "jpl_cri_earthdata_runner_status_r25.csv")
    local_registry_r25 = pd.read_csv(DER / "local_groundwater_evidence_registry_r25.csv")
    attribution_r25 = pd.read_csv(DER / "attribution_confidence_matrix_r25.csv")
    zero_fdr = pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv")
    zero_summary = json.loads((DER / "zero_aware_fdr_summary_r27.json").read_text(encoding="utf-8"))
    sy_thresh = pd.read_csv(DER / "specific_yield_thresholds_r28.csv")
    sy_scenarios = pd.read_csv(DER / "specific_yield_scenarios_r28.csv")
    sy_region = pd.read_csv(DER / "specific_yield_region_summary_r28.csv")
    confidence_main = pd.read_csv(DER / "confidence_ledger_main_r29.csv")
    confidence_detail = pd.read_csv(DER / "confidence_ledger_detail_r29.csv")

    material = cities[cities["fdr_sig"] & (cities["dP"].abs() >= MATERIAL)]
    assert summary["n"] == len(cities) == 444
    assert summary["n_fdr_sig"] == int(cities["fdr_sig"].sum()) == 330
    assert len(material[material["dP"] > 0]) == summary["n_material_inc"] == 3
    assert len(material[material["dP"] < 0]) == summary["n_material_dec"] == 3
    assert len(hotspots) == 6
    assert len(grid) == 150
    assert int(grid["hotspot_sign_reversals"].sum()) == 0
    assert len(envelope) == 6
    assert bool(envelope["sign_consistent_across_grid"].all())
    assert len(city_grid) == 900
    assert not bool(city_grid["sign_reversed_from_baseline"].any())
    assert len(effects) == 3
    assert effects.iloc[0]["parameter"] == "Specific yield"
    assert len(policy) == 444
    assert not exposure.empty
    assert r20["n_cities"] == len(spatial) == 444
    assert r20["city_bh_fdr_sig"] == int(cities["fdr_sig"].sum()) == 330
    assert r20["city_by_fdr_sig"] == 261
    assert r20["n_material_point_hotspots"] == 6
    assert r20["n_material_metro_clusters_50km"] == 5
    assert r20["n_material_300km_blocks"] == 2
    assert r20["n_positive_material_hotspots_coastal_lt50km"] == 3
    assert r20["n_material_hotspots_available_sign_robust"] == 5
    assert r20["n_material_hotspots_available_sign_probable"] == 1
    assert 14.0 < r20["median_trigger_rise_m"] < 15.0
    assert 16.5 < r20["beijing_trigger_rise_m"] < 17.5
    assert len(metro[metro["n_material_point_hotspots"] > 0]) == 5
    assert len(blocks[blocks["n_material_hotspots"] > 0]) >= 8
    assert len(coastal) == 6
    assert len(signs) == 6
    assert len(trigger) == 444
    assert set(external["status_in_this_project"]) >= {"ingested and used", "not yet ingested"}
    assert r21["n_cities"] == 444
    assert r21["n_ghsl_matched_cities"] == len(ghsl_matches) == 444
    assert r21["n_ghsl_within_polygon"] == 436
    assert r21["n_ghsl_nearest_le50km"] == 8
    assert r21["n_material_ghsl_urban_centres"] == 5
    assert r21["n_material_hotspots_csr_gsfc_recent_sign_match"] == 6
    assert r21["n_material_hotspots_csr_gsfc_theilsen_sign_match"] == 6
    assert r21["n_material_hotspots_csr_gsfc_ghsl_robust"] == 6
    assert len(ghsl_aggregates) >= 1
    assert len(hotspot_ghsl) == 6
    assert len(gsfc) == 444
    assert len(multiproduct) == 444
    assert "auth-blocked" in str(r21["jpl_status"])
    assert set(r21_status["status_in_this_project"]) >= {"ingested and used", "auth-blocked unless local Earthdata credentials are provided"}
    assert len(product_consensus) == 6
    assert r23["n_csr_material_hotspots"] == 6
    assert r23["n_gsfc_sign_supported_hotspots"] == 6
    assert r23["n_gsfc_material_hotspots"] == 1
    assert r23["n_gsfc_near_material_hotspots"] == 2
    assert r23["n_positive_gsfc_material_hotspots"] == 0
    assert jpl_r24.iloc[0]["short_name"] == "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4"
    assert jpl_r24.iloc[0]["collection_id"] == "C3195527175-POCLOUD"
    assert "auth_blocked" in str(jpl_r24.iloc[0]["status_in_this_project"])
    assert r24["jpl_cri_status"] == "auth_blocked"
    assert len(yok_monthly) == r24["yokohama_n_monthly_records"] == 3781
    assert len(yok_trends) == r24["yokohama_n_trend_wells"] == 23
    assert int((yok_trends["slope_m_per_year"] > 0).sum()) == r24["yokohama_positive_wells"] == 20
    assert int(((yok_trends["slope_m_per_year"] > 0) & (yok_trends["p_value"] < 0.05)).sum()) == 15
    assert 0.04 < r24["yokohama_median_slope_m_per_year"] < 0.05
    assert "Yokohama / Tokyo Bay" in set(local_registry["region_or_cluster"])
    assert "Mumbai-Bhayandar cluster" in set(local_registry["region_or_cluster"])
    assert "low-contradictory" in set(attribution_r24["attribution_confidence"])
    assert r25["tokyo_representative_wells"]["n_wells"] == len(tokyo_trends) == 4
    assert r25["tokyo_representative_wells"]["n_positive_ols"] == int((tokyo_trends["ols_slope_m_per_year"] > 0).sum()) == 4
    assert 0.60 < r25["tokyo_representative_wells"]["median_slope_m_per_year"] < 0.62
    assert len(tokyo_levels) == 40
    assert r25["tokyo_2024_regional_summary"]["observation_wells"] == 91
    assert r25["tokyo_2024_regional_summary"]["rising_confined_wells"] == 79
    assert len(tokyo_2016) == 91
    assert int((pd.to_numeric(tokyo_2016["change_2016_minus_2015_m"], errors="coerce") > 0).sum()) == 78
    assert len(tokyo_2022) == 91
    assert int((tokyo_2022["change_2022_minus_2021_m"] > 0).sum()) == 75
    assert len(tokyo_summary) == 4
    assert not bool(cgwb_r25["status"].eq("ok").any())
    assert {"Crossref", "AGRIS metadata page"} <= set(mumbai_r25["source"])
    assert jpl_r25.iloc[0]["run_status"] == "earthaccess_missing_and_no_local_file"
    assert "Tokyo Bay / Yokohama" in set(local_registry_r25["city_or_region"])
    assert "Mumbai-Bhayandar" in set(local_registry_r25["city_or_region"])
    assert "medium-high sign / low-management" in set(attribution_r25["attribution_confidence"])
    assert len(zero_fdr) == zero_summary["n_cities"] == 444
    assert zero_summary["zero_exact_dP_rows"] == int(zero_fdr["zero_exact_dP"].sum()) == 15
    assert zero_summary["original_bh_significant"] == int(cities["fdr_sig"].sum()) == 330
    assert zero_summary["zero_aware_bh_significant"] == int(zero_fdr["fdr_bh_zero_aware"].sum()) == 311
    assert zero_summary["zero_aware_by_significant"] == int(zero_fdr["fdr_by_zero_aware"].sum()) == 245
    assert zero_summary["zero_aware_material_bh"] == int(zero_fdr["material_bh_zero_aware"].sum()) == 6
    assert zero_summary["zero_aware_material_by"] == int(zero_fdr["material_by_zero_aware"].sum()) == 5
    assert zero_summary["material_bh_names"] == ["Yokohama", "Bhayandar", "Mumbai", "Delhi", "Lahore", "Ludhiana"]
    assert zero_summary["material_by_names"] == ["Yokohama", "Bhayandar", "Mumbai", "Lahore", "Ludhiana"]
    assert len(sy_thresh) == 9
    assert len(sy_scenarios) == 54
    assert len(sy_region) >= 18
    mat_names = {"Yokohama", "Bhayandar", "Mumbai", "Delhi", "Lahore", "Ludhiana"}
    sy_mat = sy_thresh[sy_thresh["name"].isin(mat_names)].set_index("name")
    assert set(sy_mat.index) == mat_names
    assert sy_mat["sy_material_threshold"].notna().all()
    assert sy_mat["sy_material_threshold"].between(0.10, 0.17).all()
    assert 0.13 < float(sy_thresh.loc[sy_thresh["name"] == "Yokohama", "sy_material_threshold"].iloc[0]) < 0.14
    assert 0.10 < float(sy_thresh.loc[sy_thresh["name"] == "Mumbai", "sy_material_threshold"].iloc[0]) < 0.11
    assert pd.isna(sy_thresh.loc[sy_thresh["name"] == "Beijing", "sy_material_threshold"].iloc[0])
    assert 0.08 < float(sy_thresh.loc[sy_thresh["name"] == "Tokyo", "sy_material_threshold"].iloc[0]) < 0.09
    assert 0.07 < float(sy_thresh.loc[sy_thresh["name"] == "Tianjin", "sy_material_threshold"].iloc[0]) < 0.08
    assert len(confidence_main) == 6
    assert set(confidence_main["Region"]) == {
        "North China Plain / Beijing",
        "Tokyo Bay / Yokohama",
        "Mumbai-Bhayandar / Mumbai",
        "Delhi / New Delhi",
        "Lahore",
        "Ludhiana / Punjab",
    }
    assert len(confidence_detail) == 7
    assert "Beijing, CN" in set(confidence_detail["exposure_unit"])
    assert set(confidence_detail["local_confidence"]) >= {
        "medium-high sign / low-management",
        "low-contradictory",
        "high mechanism support",
    }

    for stem in [
        "Fig1_mechanism",
        "Fig2_global_signresolved",
        "Fig3_regional",
        "Fig4_timeseries",
        "Fig5_policy_robustness",
        "Fig6_trigger_spatial_robustness",
        "Fig7_ghsl_gsfc_robustness",
        "FigS1_yokohama_local_groundwater_r24",
        "FigS2_tokyo_representative_groundwater_r25",
    ]:
        for ext in ["png", "svg", "pdf"]:
            assert (ROOT / "figures" / f"{stem}.{ext}").exists(), f"missing {stem}.{ext}"

    beijing = cities[cities["name"] == "Beijing"].iloc[0]
    assert beijing["dP"] > 0
    assert beijing["dP_lo"] > 0

    print("Derived-output verification passed.")
    print(f"Cities: {len(cities)}")
    print(f"FDR-significant BH/BY (original city table): {int(cities['fdr_sig'].sum())}/{r20['city_by_fdr_sig']}")
    print(
        "Zero-aware finite-Monte-Carlo BH/BY: "
        f"{zero_summary['zero_aware_bh_significant']}/{zero_summary['zero_aware_by_significant']}; "
        f"material BH/BY: {zero_summary['zero_aware_material_bh']}/{zero_summary['zero_aware_material_by']}"
    )
    print(f"Material increases/decreases: {summary['n_material_inc']}/{summary['n_material_dec']}")
    print(f"Beijing dP: {beijing['dP']:+.6f}; TWS trend: {beijing['tws_cm_yr']:+.2f} cm yr-1")
    print(f"Sensitivity combinations: {len(grid)}; hotspot sign reversals: {int(grid['hotspot_sign_reversals'].sum())}")
    print(f"Hotspot city-grid rows: {len(city_grid)}")
    print(f"Largest hotspot-magnitude sensitivity factor: {effects.iloc[0]['parameter']}")
    print(f"R20 metro/300km hotspot groups: {r20['n_material_metro_clusters_50km']}/{r20['n_material_300km_blocks']}")
    print(f"Median/Beijing +0.01 trigger: {r20['median_trigger_rise_m']:.2f}/{r20['beijing_trigger_rise_m']:.2f} m")
    print(f"GHSL matches: {r21['n_ghsl_matched_cities']}/444; material GHSL UCs: {r21['n_material_ghsl_urban_centres']}")
    print(f"CSR-GSFC hotspot sign agreement: {r21['n_material_hotspots_csr_gsfc_recent_sign_match']}/6")
    print(f"R23 GSFC-material hotspots: {r23['n_gsfc_material_hotspots']}/6; positive GSFC-material: {r23['n_positive_gsfc_material_hotspots']}/3")
    print(f"R29 confidence ledger rows: main={len(confidence_main)}, detail={len(confidence_detail)}")
    print(f"JPL status: {r21['jpl_status']}")
    print(f"R24 JPL CRI status: {r24['jpl_cri_status']}; collection: {jpl_r24.iloc[0]['collection_id']}")
    print(
        "R24 Yokohama local wells: "
        f"{r24['yokohama_positive_wells']}/{r24['yokohama_n_trend_wells']} rising; "
        f"median {r24['yokohama_median_slope_m_per_year']:+.4f} m yr-1"
    )
    print(f"R24 Mumbai-Bhayandar status: {r24['mumbai_bhayandar_status']}")
    print(
        "R25 Tokyo representative wells: "
        f"{r25['tokyo_representative_wells']['n_positive_ols']}/{r25['tokyo_representative_wells']['n_wells']} rising; "
        f"median {r25['tokyo_representative_wells']['median_slope_m_per_year']:+.3f} m yr-1"
    )
    print(
        "R25 Tokyo official summary/table checks: "
        f"{r25['tokyo_2024_regional_summary']['rising_confined_wells']}/"
        f"{r25['tokyo_2024_regional_summary']['observation_wells']} rising in 2024; "
        f"{r25['tokyo_open_data_table5_2016']['n_positive_2016_minus_2015']}/90 positive in 2016; "
        f"{r25['tokyo_pdf_table5_2022']['n_positive_2022_minus_2021']}/91 positive in 2022"
    )
    print(f"R25 JPL runner status: {jpl_r25.iloc[0]['run_status']}")
    print(
        "R28 S_y thresholds: "
        f"Yokohama {float(sy_thresh.loc[sy_thresh['name'] == 'Yokohama', 'sy_material_threshold'].iloc[0]):.3f}; "
        "Beijing never material; "
        f"Tokyo {float(sy_thresh.loc[sy_thresh['name'] == 'Tokyo', 'sy_material_threshold'].iloc[0]):.3f}; "
        f"Tianjin {float(sy_thresh.loc[sy_thresh['name'] == 'Tianjin', 'sy_material_threshold'].iloc[0]):.3f}"
    )


if __name__ == "__main__":
    main()
