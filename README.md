# Groundwater management and urban earthquake-liquefaction hazard

This repository is the clean reproducibility package for the paper:

**Groundwater management drives opposite shifts in urban earthquake-liquefaction hazard**

The analysis couples observed GRACE/GRACE-FO groundwater-storage change to the water-table term of a published global liquefaction model for seismically exposed cities. It perturbs only the measured groundwater driver and reports a bounded, regional screening result: no diffuse global increase, but bidirectional regional shifts associated with recharge and depletion.

## What is included

- `scripts/`: analysis, sensitivity and figure-generation scripts.
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
- FDR-significant detectable change: 330 cities.
- Material and FDR-significant increases: 3 cities.
- Material and FDR-significant decreases: 3 cities.
- Cohort mean Delta P_liq: +0.00042.
- Beijing is sign-positive but sub-material: Delta P_liq = +0.00025.
- Extended parameter grid: `data_derived/sensitivity_grid_v2.csv`.
- Six-hotspot sensitivity envelope: `data_derived/hotspot_sensitivity_envelope_v2.csv`.
- Validation evidence matrix: `data_derived/validation_evidence_matrix_v2.csv`.
- Policy-priority screening table: `data_derived/policy_priority_table_v2.csv`.

The extended sensitivity grid varies PGA-to-PGV conversion, specific yield and groundwater-trend magnitude. The number of cities crossing the material threshold changes across that grid, but the six baseline material hotspots do not reverse sign.

## Boundary of use

GRACE/GRACE-FO constrains a regional storage driver at roughly 300 km scale. The city is the exposure unit. City values are directional screening estimates, not site-specific engineering predictions. The analysis does not claim that groundwater causes earthquakes.

## Intended public remote

`https://github.com/Johnsonlijian/groundwater-liquefaction-urban-hazard`

## Citation

Use the metadata in `CITATION.cff` once the manuscript and Zenodo record are finalized.
