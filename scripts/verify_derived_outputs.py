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

    for stem in [
        "Fig1_mechanism",
        "Fig2_global_signresolved",
        "Fig3_regional",
        "Fig4_timeseries",
        "Fig5_policy_robustness",
        "Fig6_trigger_spatial_robustness",
        "Fig7_ghsl_gsfc_robustness",
    ]:
        for ext in ["png", "svg", "pdf"]:
            assert (ROOT / "figures" / f"{stem}.{ext}").exists(), f"missing {stem}.{ext}"

    beijing = cities[cities["name"] == "Beijing"].iloc[0]
    assert beijing["dP"] > 0
    assert beijing["dP_lo"] > 0

    print("Derived-output verification passed.")
    print(f"Cities: {len(cities)}")
    print(f"FDR-significant BH/BY: {int(cities['fdr_sig'].sum())}/{r20['city_by_fdr_sig']}")
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
    print(f"JPL status: {r21['jpl_status']}")


if __name__ == "__main__":
    main()
