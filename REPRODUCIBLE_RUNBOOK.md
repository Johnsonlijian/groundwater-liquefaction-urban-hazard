# Reproducible runbook

This runbook documents the local command sequence used for the derived outputs in this repository.

## Environment

Python 3.11 was used locally. Install dependencies:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## Raw data boundary

Raw third-party data are not included. Download them from the sources in `DATASETS_AND_LINKS.csv` and place them under `data_raw/` with the paths expected by the scripts.

## Full reconstruction sequence

```powershell
python scripts\\build_cohort.py
python scripts\\attach_gem_hazard.py
python scripts\\assemble_inputs.py
python scripts\\grace_trend.py
python scripts\\groundwater_isolation.py
python scripts\\analyze_v2.py
python scripts\\make_nature_water_r19_figures.py
python scripts\\r20_spatial_trigger_analysis.py
python scripts\\r21_ghsl_gsfc_jpl_robustness.py
```

## Minimum verification from included derived data

The headline numbers can be rechecked without raw downloads:

```powershell
python scripts\\verify_derived_outputs.py
```

Expected summary:

- Clean seismic cohort: 444 cities.
- CI excludes zero: 319.
- FDR-significant cities under primary Benjamini-Hochberg control: 330.
- Stricter Benjamini-Yekutieli dependency-aware sensitivity: 261.
- Material + FDR-significant increases: 3.
- Material + FDR-significant decreases: 3.
- Material point-city hotspots after 50 km metropolitan deduplication: 5 clusters.
- Material point-city hotspots after GHSL urban-centre aggregation: 5 urban centres.
- Material hotspot regions at GRACE-scale 300 km grouping: 2 regions.
- Positive material hotspots within 50 km of the coastline: 3 of 3.
- GHSL R2024A polygon matches: 444/444 cities.
- CSR-GSFC hotspot sign agreement: 6/6 material hotspots.
- JPL CRI-filtered mascon: protected by Earthdata authentication in this run.
- Beijing: Delta P_liq approximately +0.0003, positive interval, recent TWS trend +0.57 cm yr-1.
- Sensitivity grid rows: 150.
- Six-hotspot city-grid rows: 900.
- Six baseline material hotspots: all retain baseline direction under the positive-scaling sensitivity grid.
- Largest hotspot-magnitude sensitivity factor in the deterministic grid: specific yield.
- Median +0.01 water-table-rise trigger: about 14.5 m.
- Beijing +0.01 water-table-rise trigger: about 17.1 m.

`scripts\\analyze_v2.py` reconstructs the final city table and hotspot table, but it expects the Natural Earth lake boundary data under `data_raw/` so that the inland-water-body exclusion can be recomputed.

## Figure outputs

Generated figures are stored under `figures/`:

- `Fig1_mechanism.png`
- `Fig1_mechanism.svg`
- `Fig1_mechanism.pdf`
- `Fig2_global_signresolved.png`
- `Fig2_global_signresolved.svg`
- `Fig2_global_signresolved.pdf`
- `Fig3_regional.png`
- `Fig3_regional.svg`
- `Fig3_regional.pdf`
- `Fig4_timeseries.png`
- `Fig4_timeseries.svg`
- `Fig4_timeseries.pdf`
- `Fig5_policy_robustness.png`
- `Fig5_policy_robustness.svg`
- `Fig5_policy_robustness.pdf`
- `Fig6_trigger_spatial_robustness.png`
- `Fig6_trigger_spatial_robustness.svg`
- `Fig6_trigger_spatial_robustness.pdf`
- `Fig7_ghsl_gsfc_robustness.png`
- `Fig7_ghsl_gsfc_robustness.svg`
- `Fig7_ghsl_gsfc_robustness.pdf`

## Guardrails

Do not reinterpret the outputs as precise city-scale engineering predictions. GRACE/GRACE-FO provides a regional groundwater-storage driver, while cities are exposure units. The analysis does not claim a diffuse global increase and does not claim that groundwater causes earthquakes.
