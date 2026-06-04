# Regional storage-derived water-table change and urban earthquake-liquefaction hazard

This repository is the clean reproducibility package for the paper:

**Water-storage gains and losses indicate opposite liquefaction-screening priorities in seismic cities**

The analysis couples observed GRACE/GRACE-FO terrestrial-water-storage change to the water-table term of a published global liquefaction model for seismically exposed cities. It perturbs only the storage-derived water-table driver and reports a bounded, regional screening result: no diffuse global increase, but bidirectional regional shifts associated with recharge and depletion.

## What is included

- `scripts/`: analysis, sensitivity, spatial-robustness and figure-generation scripts.
- `data_derived/`: derived city tables, hotspot tables and summary JSON files.
- `figures/`: generated manuscript figures.
- `DATASETS_AND_LINKS.csv`: source-data registry and download/licence notes.
- `REPRODUCIBLE_RUNBOOK.md`: command sequence and expected outputs.

## What is not included

Raw third-party data, downloaded archives, active manuscripts, cover letters, reviewer drafts, private logs and submission files are intentionally excluded. Recreate raw inputs from the public sources listed in `DATASETS_AND_LINKS.csv`.

## Core output

The baseline city table is in `data_derived/core_summary_v2.json` and `data_derived/city_results_v2.csv`. The zero-aware finite-Monte-Carlo FDR audit used in the current manuscript is in `data_derived/zero_aware_fdr_summary_r27.json` and `data_derived/zero_aware_fdr_city_results_r27.csv`. The material hotspot table is `data_derived/hotspot_table.csv`.

Current summary:

- City cohort: 444 seismically exposed cities.
- Original city-table FDR-significant detectable change under primary Benjamini-Hochberg control: 330 cities.
- Original stricter Benjamini-Yekutieli dependency-aware sensitivity: 261 cities.
- Zero-aware finite-Monte-Carlo FDR-sensitive detectable change: 311 Benjamini-Hochberg cities and 245 Benjamini-Yekutieli cities.
- Zero-aware material hotspot count: 6 under Benjamini-Hochberg and 5 under Benjamini-Yekutieli.
- Material and FDR-significant increases: 3 cities.
- Material and FDR-significant decreases: 3 cities.
- Material point-city hotspots after 50 km metropolitan deduplication: 5 clusters.
- Material point-city hotspots after GHSL urban-centre aggregation: 5 urban centres.
- Material hotspot regions at GRACE-scale 300 km grouping: 2 regions.
- Positive material hotspots within 50 km of the coastline: 3 of 3.
- GHSL R2024A polygon matches: 444/444 cities, including 436 within-polygon matches.
- CSR-GSFC hotspot sign agreement: 6/6 CSR-material hotspots under OLS and Theil-Sen trends.
- Product-consensus materiality under GSFC: 1/6 CSR-material hotspots.
- Positive coastal hotspots that remain GSFC-material: 0/3.
- Cohort mean Delta P_liq: +0.00042.
- Beijing is sign-positive but sub-material: Delta P_liq = +0.00025.
- Extended parameter grid: `data_derived/sensitivity_grid_v2.csv`.
- Six-hotspot sensitivity envelope: `data_derived/hotspot_sensitivity_envelope_v2.csv`.
- Six-hotspot city-by-parameter grid: `data_derived/hotspot_sensitivity_city_grid_v2.csv`.
- Parameter-effect diagnostic: `data_derived/sensitivity_parameter_effects_v2.csv`.
- Validation evidence matrix: `data_derived/validation_evidence_matrix_v2.csv`.
- Policy-priority screening table: `data_derived/policy_priority_table_v2.csv`.
- Policy exposure summary: `data_derived/policy_exposure_summary_v2.csv`.
- Spatial robustness summary: `data_derived/r20_spatial_trigger_summary.json`.
- Metropolitan deduplication: `data_derived/metro_deduplication_r20.csv`.
- Block-level FDR diagnostics: `data_derived/spatial_block_fdr_r20.csv`.
- Zero-aware FDR audit: `data_derived/zero_aware_fdr_city_results_r27.csv`, `data_derived/zero_aware_fdr_summary_r27.json`.
- Coastal robustness diagnostics: `data_derived/coastal_robustness_r20.csv`.
- Available-driver sign checks: `data_derived/hotspot_driver_sign_robustness_r20.csv`.
- Water-table-rise trigger table: `data_derived/water_table_trigger_r20.csv`.
- Attribution-confidence matrix and external-product status: `data_derived/attribution_confidence_matrix_r20.csv`, `data_derived/external_product_status_r20.csv`.
- GHSL urban-centre matches and aggregates: `data_derived/ghsl_urban_centre_matches_r21.csv`, `data_derived/ghsl_urban_centre_aggregates_r21.csv`.
- GSFC independent mascon trends: `data_derived/gsfc_city_trends_r21.csv`.
- Multi-product sign robustness: `data_derived/multi_product_sign_robustness_r21.csv`.
- Product-consensus hotspot classification: `data_derived/product_consensus_hotspots_r23.csv`.
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

The extended sensitivity grid varies PGA-to-PGV conversion, specific yield and storage-trend magnitude. The number of cities crossing the material threshold changes across that grid, but the six baseline CSR-material hotspots retain their baseline direction under 900 positive-scaling hotspot-city evaluations. The parameter-effect diagnostic identifies specific yield as the largest hotspot-magnitude sensitivity factor in this deterministic grid. GHSL urban-centre polygons and NASA GSFC mascons are now ingested and used. GSFC is interpreted as an independent sign check, not as proof that all CSR-material hotspots are material under another product. JPL CRI-filtered mascons remain an Earthdata-authentication boundary and are not used for claims. R24/R25 local evidence upgrades Tokyo Bay/Yokohama to local and official sign-supported (Yokohama: 20 of 23 trend-qualified municipal wells rising over 2015/04-2025/03; Tokyo: 4 of 4 representative confined wells rising over 2015-2024 and 79 of 91 confined observation wells rising in the 2024 official regional summary). Mumbai-Bhayandar remains candidate-only because DOI-verified Mumbai station evidence points toward groundwater-depth increase/depletion rather than positive recovery and CGWB official raw endpoints were not accessible in this run.

## Boundary of use

GRACE/GRACE-FO constrains a regional storage-derived water-table driver at roughly 300 km scale. The city is the exposure unit. City values are directional screening estimates, not site-specific engineering predictions. The analysis does not claim that groundwater causes earthquakes.

## Intended public remote

`https://github.com/Johnsonlijian/groundwater-liquefaction-urban-hazard`

## Citation

Use the metadata in `CITATION.cff` once the manuscript and Zenodo record are finalized.
