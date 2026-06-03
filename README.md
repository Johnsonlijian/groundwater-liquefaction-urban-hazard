# Groundwater change and urban earthquake-liquefaction hazard

This repository is the clean reproducibility package for the paper:

**Groundwater change reshapes urban earthquake-liquefaction hazard in opposite directions**

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

The headline numbers are in `data_derived/core_summary_v2.json` and `data_derived/city_results_v2.csv`. The final material, FDR-significant hotspot table is `data_derived/hotspot_table.csv`.

Current summary:

- City cohort: 444 seismically exposed cities.
- FDR-significant detectable change under primary Benjamini-Hochberg control: 330 cities.
- Stricter Benjamini-Yekutieli dependency-aware sensitivity: 261 cities.
- Material and FDR-significant increases: 3 cities.
- Material and FDR-significant decreases: 3 cities.
- Material point-city hotspots after 50 km metropolitan deduplication: 5 clusters.
- Material hotspot regions at GRACE-scale 300 km grouping: 2 regions.
- Positive material hotspots within 50 km of the coastline: 3 of 3.
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
- Coastal robustness diagnostics: `data_derived/coastal_robustness_r20.csv`.
- Available-driver sign checks: `data_derived/hotspot_driver_sign_robustness_r20.csv`.
- Water-table-rise trigger table: `data_derived/water_table_trigger_r20.csv`.
- Attribution-confidence matrix and external-product status: `data_derived/attribution_confidence_matrix_r20.csv`, `data_derived/external_product_status_r20.csv`.

The extended sensitivity grid varies PGA-to-PGV conversion, specific yield and storage-trend magnitude. The number of cities crossing the material threshold changes across that grid, but the six baseline material hotspots retain their baseline direction under 900 positive-scaling hotspot-city evaluations. The parameter-effect diagnostic identifies specific yield as the largest hotspot-magnitude sensitivity factor in this deterministic grid. Independent multi-mascon coastal robustness is not claimed; JPL CRI-filtered mascons, NASA GSFC mascons and GHSL urban-centre polygons are recorded as pending follow-up products in `data_derived/external_product_status_r20.csv`.

## Boundary of use

GRACE/GRACE-FO constrains a regional storage driver at roughly 300 km scale. The city is the exposure unit. City values are directional screening estimates, not site-specific engineering predictions. The analysis does not claim that groundwater causes earthquakes.

## Intended public remote

`https://github.com/Johnsonlijian/groundwater-liquefaction-urban-hazard`

## Citation

Use the metadata in `CITATION.cff` once the manuscript and Zenodo record are finalized.
