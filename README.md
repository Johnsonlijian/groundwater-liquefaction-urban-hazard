# Managed groundwater trajectories and liquefaction-screening blind spots

This repository is the clean reproducibility package for the paper:

**Managed groundwater trajectories expose a dynamic blind spot in liquefaction screening**

The analysis couples observed GRACE/GRACE-FO terrestrial-water-storage change to the water-table term of a published global liquefaction model for seismically exposed cities. It perturbs only the storage-derived water-table driver and reports a bounded, regional screening result: no diffuse global increase, but sign-resolved regional corrections to static water-table screening assumptions.

## What is included

- `scripts/`: analysis, sensitivity, spatial-robustness and figure-generation scripts.
- `data_derived/`: derived city tables, follow-up-unit tables and summary JSON files.
- `figures/`: generated manuscript figures.
- `DATASETS_AND_LINKS.csv`: source-data registry and download/licence notes.
- `02_source_registry.md`: source-to-claim registry for the R34 pre-submission audit.
- `03_claim_evidence_map.md`: bounded claim-evidence map and forbidden-wording guardrails.
- `docs/Reference_Audit_R34.*`: author-side reference authenticity and reachability audit.
- `REPRODUCIBLE_RUNBOOK.md`: command sequence and expected outputs.

## What is not included

Raw third-party data, downloaded archives, active manuscripts, cover letters, reviewer drafts, private logs and submission files are intentionally excluded. Recreate raw inputs from the public sources listed in `DATASETS_AND_LINKS.csv`.

## Core output

The baseline city table is in `data_derived/core_summary_v2.json` and `data_derived/city_results_v2.csv`. The zero-aware finite-Monte-Carlo FDR audit used in the current manuscript is in `data_derived/zero_aware_fdr_summary_r27.json` and `data_derived/zero_aware_fdr_city_results_r27.csv`. The static-counterfactual diagnostic introduced in R31 is in `data_derived/static_observed_triage_tier_summary_r31.json`, `data_derived/static_observed_triage_tier_change_r31.csv`, `data_derived/static_observed_triage_tier_counts_r31.csv` and `data_derived/static_observed_wtd_proxy_crossings_r31.csv`. The R33 statistical-object audit is in `data_derived/statistical_object_audit_summary_r33.json` plus the R33 CSV tables. R36 adds threshold interpretation, regional follow-up groups, negative-control style strata and reviewer-safe submission aliases. R37 adds the GFZ GravIS third-product/leakage stress test, engineering-context enrichment diagnostics, a regional evidence scorecard and a pre-implementation policy protocol. R39 adds the Article-route JPL CRI status ledger, aquifer-context specific-yield priors, evidence-tier cards and the named local dataset release package. R40 adds a public historical-event inventory benchmark. R41 adds the Article regional hierarchy, four-product evidence ladder and readiness dashboard. R34 adds the source registry, claim-evidence map and reference audit used for pre-submission claim calibration. The baseline material-unit alias is `data_derived/material_screening_units_v2.csv`.

Current summary:

- City cohort: 444 seismically exposed cities.
- Original city-table FDR-significant detectable change under primary Benjamini-Hochberg control: 330 cities.
- Original stricter Benjamini-Yekutieli dependency-aware sensitivity: 261 cities.
- Zero-aware finite-Monte-Carlo FDR-sensitive detectable change: 311 Benjamini-Hochberg cities and 245 Benjamini-Yekutieli cities.
- Zero-aware material screening-unit count: 6 under Benjamini-Hochberg and 5 under Benjamini-Yekutieli.
- Static-counterfactual A/B follow-up units under zero-aware Benjamini-Hochberg: 28 point-city exposure units.
- Static-counterfactual material/targeted split: 6 material and 22 targeted units.
- Static-counterfactual A/B direction split: 19 increase-side and 9 depletion-side units.
- Static-counterfactual Benjamini-Yekutieli sensitivity: 22 A/B follow-up units, including 5 material and 17 targeted units.
- Static-counterfactual A/B independence audit: 28 point-city units reduce to 21 50 km metropolitan clusters, 22 GHSL urban centres and 10 GRACE-scale 300 km regional groups.
- Largest A/B 300 km regional group: 17 point-city exposure units.
- Material and FDR-significant increases: 3 cities.
- Material and FDR-significant decreases: 3 cities.
- Material point-city screening units after 50 km metropolitan deduplication: 5 clusters.
- Material point-city screening units after GHSL urban-centre aggregation: 5 urban centres.
- Material screening-unit regions at GRACE-scale 300 km grouping: 2 regions.
- Positive material screening units within 50 km of the coastline: 3 of 3.
- GHSL R2024A polygon matches: 444/444 cities, including 436 within-polygon matches.
- CSR-GSFC screening-unit sign agreement: 6/6 CSR-material units under OLS and Theil-Sen trends.
- Product-consensus materiality under GSFC: 1/6 CSR-material units.
- Product-consensus statistical sign support under GSFC (p < 0.05): 4/6 CSR-material units.
- Positive coastal units that remain GSFC-material: 0/3.
- CSR-GFZ raw TWS sign agreement: 86.0% across all cities and 6/6 CSR-material units.
- CSR-GFZ leakage-adjusted sign agreement: 69.1% across all cities and 6/6 CSR-material units.
- A/B follow-up units are enriched in low Vs30, near-water proximity, at least two susceptibility proxies and at least three susceptibility proxies; they are not enriched at the PGA >= 0.2 g threshold.
- Cohort mean Delta P_liq: +0.00042.
- Beijing is sign-positive but sub-material: Delta P_liq = +0.00025.
- Extended parameter grid: `data_derived/sensitivity_grid_v2.csv`.
- Six follow-up-unit sensitivity envelope: `data_derived/followup_unit_sensitivity_envelope_v2.csv`.
- Six follow-up-unit city-by-parameter grid: `data_derived/followup_unit_sensitivity_city_grid_v2.csv`.
- Parameter-effect diagnostic: `data_derived/sensitivity_parameter_effects_v2.csv`.
- Groundwater evidence-support matrix: `data_derived/evidence_support_matrix_v2.csv`.
- Policy follow-up screening table: `data_derived/policy_followup_table_v2.csv`.
- Policy follow-up exposure summary: `data_derived/policy_followup_exposure_summary_v2.csv`.
- Spatial robustness summary: `data_derived/r20_spatial_followup_summary.json`.
- Metropolitan deduplication: `data_derived/metro_deduplication_r20.csv`.
- Block-level FDR diagnostics: `data_derived/spatial_block_fdr_r20.csv`.
- Zero-aware FDR audit: `data_derived/zero_aware_fdr_city_results_r27.csv`, `data_derived/zero_aware_fdr_summary_r27.json`.
- Coastal robustness diagnostics: `data_derived/coastal_robustness_r20.csv`.
- Available-driver sign checks for material units: `data_derived/material_unit_driver_sign_robustness_r20.csv`.
- Water-table-rise follow-up flag table: `data_derived/water_table_followup_flag_r20.csv`.
- Attribution-confidence matrix and external-product status: `data_derived/attribution_confidence_matrix_r20.csv`, `data_derived/external_product_status_r20.csv`.
- GHSL urban-centre matches and aggregates: `data_derived/ghsl_urban_centre_matches_r21.csv`, `data_derived/ghsl_urban_centre_aggregates_r21.csv`.
- GSFC independent mascon trends: `data_derived/gsfc_city_trends_r21.csv`.
- Multi-product sign robustness: `data_derived/multi_product_sign_robustness_r21.csv`.
- Product-consensus screening-unit classification: `data_derived/product_consensus_material_units_r23.csv`.
- Product-consensus summary: `data_derived/product_consensus_summary_r23.json`.
- R21 external-data status: `data_derived/r21_external_data_status.csv`.
- R24 JPL CRI access status: `data_derived/r24_jpl_cri_access_status.csv`.
- R24 Yokohama municipal groundwater extraction: `data_derived/yokohama_groundwater_monthly_r24.csv`, `data_derived/yokohama_groundwater_trends_r24.csv`.
- R24 local evidence registry: `data_derived/local_groundwater_evidence_registry_r24.csv`.
- R24 attribution-confidence matrix: `data_derived/attribution_confidence_matrix_r24.csv`.
- R24 local-evidence summary: `data_derived/r24_local_evidence_summary.json`.
- R25 Tokyo Bay official groundwater evidence summary: `data_derived/tokyo_bay_groundwater_evidence_summary_r25.csv`.
- R25 Tokyo representative confined-well trends: `data_derived/tokyo_representative_groundwater_trends_r25.csv`.
- R25 Mumbai-Bhayandar evidence boundary: `data_derived/mumbai_bhayandar_evidence_boundary_r25.csv`.
- R25 CGWB access retry status: `data_derived/cgwb_access_retry_status_r25.csv`.
- R25 Earthdata/JPL CRI runner status: `data_derived/jpl_cri_earthdata_runner_status_r25.csv`.
- R25 updated local evidence registry and attribution matrix: `data_derived/local_groundwater_evidence_registry_r25.csv`, `data_derived/attribution_confidence_matrix_r25.csv`.
- R28 specific-yield materiality thresholds: `data_derived/specific_yield_thresholds_r28.csv`.
- R28 specific-yield scenario table: `data_derived/specific_yield_scenarios_r28.csv`.
- R28 regional specific-yield materiality summary: `data_derived/specific_yield_region_summary_r28.csv`.
- R29 main-text confidence ledger: `data_derived/confidence_ledger_main_r29.csv`.
- R29 detailed evidence-confidence ledger: `data_derived/confidence_ledger_detail_r29.csv`.
- R31 static-counterfactual triage diagnostics: `data_derived/static_observed_triage_tier_summary_r31.json`, `data_derived/static_observed_triage_tier_change_r31.csv`, `data_derived/static_observed_triage_tier_counts_r31.csv`, `data_derived/static_observed_wtd_proxy_crossings_r31.csv`.
- R33 statistical-object audit summary: `data_derived/statistical_object_audit_summary_r33.json`.
- R33 zero-aware spatial block FDR diagnostics: `data_derived/spatial_block_fdr_zero_aware_r33.csv`.
- R33 zero-aware downstream audit: `data_derived/zero_aware_downstream_audit_r33.csv`.
- R33 materiality uncertainty table: `data_derived/materiality_uncertainty_table_r33.csv`.
- R33 independence-scale counts: `data_derived/independence_scale_counts_r33.csv`.
- R33 product-support classification and summary: `data_derived/product_support_table_r33.csv`, `data_derived/product_support_summary_r33.csv`.
- R33 local sign tests for Tokyo Bay/Yokohama: `data_derived/local_evidence_sign_tests_r33.csv`.
- R34 source registry and claim-evidence map: `02_source_registry.md`, `03_claim_evidence_map.md`.
- R34 reference audit: `docs/Reference_Audit_R34.csv`, `docs/Reference_Audit_R34.md`.
- R36 threshold interpretation and controls: `data_derived/threshold_interpretation_r36.csv`, `data_derived/null_detectability_reconciliation_r36.csv`, `data_derived/regional_followup_groups_r36.csv`, `data_derived/negative_control_strata_r36.csv`, `data_derived/specific_yield_scenario_ledger_r36.csv`, `data_derived/threshold_controls_summary_r36.json`.
- R37 GFZ third-product and leakage stress test: `data_derived/gfz_gravis_stress_summary_r37.csv`, `data_derived/gfz_gravis_city_trends_r37.csv`, `data_derived/material_unit_gfz_gravis_stress_test_r37.csv`, `data_derived/three_product_city_consensus_r37.csv`.
- R37 engineering and policy protocol: `data_derived/engineering_susceptibility_enrichment_r37.csv`, `data_derived/ab_followup_engineering_profile_r37.csv`, `data_derived/regional_evidence_scorecard_r37.csv`, `data_derived/preimplementation_policy_protocol_r37.csv`, `data_derived/external_collaborator_role_matrix_r37.csv`, `figures/Fig6_evidence_boundary.*`, `figures/FigS4_r37_third_product_engineering_protocol.*`.
- R39 JPL CRI Article-route status: `data_derived/jpl_cri_article_status_r39.csv`, `data_derived/jpl_cri_article_status_r39.json`.
- R39 aquifer-context specific-yield products: `data_derived/aquifer_class_sy_priors_r39.csv`, `data_derived/city_aquifer_class_sy_results_r39.csv`, `data_derived/material_unit_aquifer_class_phase_r39.csv`, `data_derived/aquifer_class_sy_summary_r39.json`, `figures/Fig5_aquifer_class_phase_article.*`.
- R39 evidence-tier cards and named dataset release: `data_derived/evidence_tier_cards_r39.csv`, `data_derived/evidence_tier_cards_r39.md`, `figures/Fig4_evidence_tier_cards_article.*`, `releases/Dynamic_Groundwater_Liquefaction_Screening_Dataset_v1_0/`, `releases/Dynamic_Groundwater_Liquefaction_Screening_Dataset_v1_0.zip`.
- R40 historical-event benchmark: `data_derived/event_hindcast_inventory_registry_r40.csv`, `data_derived/event_hindcast_samples_r40.csv`, `data_derived/event_hindcast_metrics_r40.csv`, `data_derived/event_hindcast_summary_r40.json`, `figures/Fig2_event_hindcast_article.*`.
- R41 Article regional hierarchy and evidence ladder: `data_derived/regional_hierarchical_evidence_model_r41.csv`, `data_derived/four_product_evidence_ladder_r41.csv`, `data_derived/article_readiness_dashboard_r41.csv`, `data_derived/article_readiness_summary_r41.json`, `figures/Fig3_regional_hierarchical_screen_article.*`, `figures/Fig4_four_product_evidence_ladder_article.*`.

The extended sensitivity grid varies PGA-to-PGV conversion, specific yield and storage-trend magnitude. The number of cities crossing the material threshold changes across that grid, but the six baseline CSR-material screening units retain their baseline direction under 900 positive-scaling unit evaluations. The parameter-effect diagnostic identifies specific yield as the largest magnitude sensitivity factor in this deterministic grid. R28 adds unit-specific S_y* thresholds: the six CSR-material units retain abs(Delta P_liq) >= 0.01 only when S_y is at or below about 0.11-0.16; Beijing is sub-material across the tested range; Tokyo and Tianjin become material only at low S_y. R33 adds a Monte Carlo materiality audit: the six baseline CSR-material units have threshold-crossing probabilities of 0.30-0.55 under the stated Uniform(0.05, 0.25) S_y prior. R36 shows that the 0.01 reporting increment is a top-tail cohort rule near the 98.6th percentile, that the 28 A/B point-city units occupy ten 300 km regional groups, and that low-sensitivity negative-control strata contain no material units. R37 adds a credential-free GFZ GravIS RL06 TWS stress test: all six CSR-material units retain their sign in raw GFZ TWS and in the GFZ leakage-adjusted TWS diagnostic. R39 reorganizes specific-yield uncertainty by aquifer-context review classes and packages the products as **Dynamic Groundwater-Liquefaction Screening Dataset v1.0** for Zenodo deposition. R40 pairs four public historical liquefaction inventories with USGS Zhu event rasters; the dynamic update is neutral/negative for broad event-discrimination improvement, so the benchmark is used as a claim boundary. R41 formalizes the regional hierarchy and evidence ladder for the Article route. R37 also shows that A/B follow-up units are enriched in selected engineering-context proxies, but the output remains a local-review cue rather than a site-specific liquefaction map. R29 repackages the evidence hierarchy as a six-row main-text confidence ledger plus a seven-row detailed ledger that adds the Beijing mechanism anchor. GHSL urban-centre polygons, NASA GSFC mascons and GFZ GravIS are ingested and used. GSFC and GFZ are interpreted as independent sign/leakage guardrails, not as proof that all CSR-material units are material under every product. JPL CRI-filtered mascons remain an Earthdata-authentication boundary and are not used for numerical claims. R24/R25 local evidence upgrades Tokyo Bay/Yokohama to local and official sign-supported (Yokohama: 20 of 23 trend-qualified municipal wells rising over 2015/04-2025/03; Tokyo: 4 of 4 representative confined wells rising over 2015-2024 and 79 of 91 confined observation wells rising in the 2024 official regional summary). Mumbai-Bhayandar remains candidate-only because DOI-verified Mumbai station evidence points toward groundwater-depth increase/depletion rather than positive recovery and CGWB official raw endpoints were not accessible in this run.

## Boundary of use

GRACE/GRACE-FO constrains a regional storage-derived water-table driver at roughly 300 km scale. The city is the exposure unit. City values are directional screening estimates, not site-specific engineering predictions. The analysis does not claim that groundwater causes earthquakes.

## Intended public remote

`https://github.com/Johnsonlijian/groundwater-liquefaction-urban-hazard`

## Citation

Use the metadata in `CITATION.cff` once the manuscript and Zenodo record are finalized.
