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
python scripts\\r23_product_consensus_recalibration.py
python scripts\\r24_jpl_cri_and_local_groundwater_evidence.py
python scripts\\r25_tokyo_mumbai_evidence_deepening.py
python scripts\\r27_zero_aware_fdr.py
```

## Minimum verification from included derived data

The headline numbers can be rechecked without raw downloads:

```powershell
python scripts\\verify_derived_outputs.py
```

Expected summary:

- Clean seismic cohort: 444 cities.
- CI excludes zero: 319.
- Original city-table FDR-significant cities under primary Benjamini-Hochberg control: 330.
- Original stricter Benjamini-Yekutieli dependency-aware sensitivity: 261.
- Zero-aware finite-Monte-Carlo FDR-sensitive cities: 311 under Benjamini-Hochberg and 245 under Benjamini-Yekutieli.
- Zero-aware material hotspot count: 6 under Benjamini-Hochberg and 5 under Benjamini-Yekutieli.
- Material + FDR-significant increases: 3.
- Material + FDR-significant decreases: 3.
- Material point-city hotspots after 50 km metropolitan deduplication: 5 clusters.
- Material point-city hotspots after GHSL urban-centre aggregation: 5 urban centres.
- Material hotspot regions at GRACE-scale 300 km grouping: 2 regions.
- Positive material hotspots within 50 km of the coastline: 3 of 3.
- GHSL R2024A polygon matches: 444/444 cities.
- CSR-GSFC hotspot sign agreement: 6/6 CSR-material hotspots.
- GSFC-material hotspots among CSR-material hotspots: 1/6.
- Positive coastal hotspots that remain GSFC-material: 0/3.
- JPL CRI-filtered mascon: protected by Earthdata authentication in this run.
- Beijing: Delta P_liq approximately +0.0003, positive interval, recent TWS trend +0.57 cm yr-1.
- Sensitivity grid rows: 150.
- Six-hotspot city-grid rows: 900.
- Six baseline material hotspots: all retain baseline direction under the positive-scaling sensitivity grid.
- R23 product-consensus table: GSFC is an independent sign check, not a materiality proof for every CSR-material hotspot.
- R24 JPL CRI status: correct CRI-filtered collection verified; protected NetCDF remains Earthdata-authentication blocked unless local credentials or an authenticated file are supplied.
- R24 Yokohama local groundwater evidence: 3,781 monthly records parsed from official municipal PDFs; 20 of 23 trend-qualified wells rise over 2015/04-2025/03; median slope about +0.0418 m yr-1.
- R24 Mumbai-Bhayandar local evidence status: DOI-verified Mumbai station evidence is contradictory to positive-recovery attribution, so the hotspot remains candidate-only.
- R25 Tokyo official representative groundwater evidence: 4 of 4 representative confined wells rise over 2015-2024; median OLS slope about +0.608 m yr-1.
- R25 Tokyo 2024 regional summary: 79 of 91 confined observation wells rising.
- R25 Tokyo Open Data / official PDF annual-table checks: 78 of 90 valid 2016 changes positive and 75 of 91 extracted 2022 changes positive.
- R25 CGWB source retry status: no successful access to the monitoring page, Greater Mumbai PDF or Maharashtra yearbook through proxy/direct sessions.
- R25 JPL CRI runner status: Earthdata-protected; no local credentials, `earthaccess` package or authenticated local NetCDF detected.
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
- `FigS1_yokohama_local_groundwater_r24.png`
- `FigS1_yokohama_local_groundwater_r24.svg`
- `FigS1_yokohama_local_groundwater_r24.pdf`
- `FigS2_tokyo_representative_groundwater_r25.png`
- `FigS2_tokyo_representative_groundwater_r25.svg`
- `FigS2_tokyo_representative_groundwater_r25.pdf`

## Guardrails

Do not reinterpret the outputs as precise city-scale engineering predictions. GRACE/GRACE-FO provides a regional groundwater-storage driver, while cities are exposure units. The analysis does not claim a diffuse global increase and does not claim that groundwater causes earthquakes.
