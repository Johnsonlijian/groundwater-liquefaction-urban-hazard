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
python scripts\\r28_specific_yield_sensitivity.py
python scripts\\r29_submission_polish_tables.py
python scripts\\r31_static_observed_triage_change.py
python scripts\\r33_statistical_object_audit.py
python scripts\\r32_decision_synthesis_fig7.py
python scripts\\r34_reference_claim_journal_audit.py
python scripts\\r36_threshold_controls_and_regional_units.py
python scripts\\r37_third_product_engineering_policy_protocol.py
python scripts\\r40_event_hindcast_article_validation.py
python scripts\\r41_article_hierarchy_and_evidence_ladder.py
python scripts\\r42_article_display_reorder_and_protocol.py
python scripts\\r39_article_dataset_release.py
python scripts\\build_nature_water_visual_upgrade_pack.py
python scripts\\build_3d_dgls_hero.py
python figures_pro\\python\\doctor.py
python figures_pro\\python\\build_svg_suite.py
python figures_pro\\python\\build_3d_dgls_hero.py
python figures_pro\\python\\audit_figures.py
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
- Zero-aware material screening-unit count: 6 under Benjamini-Hochberg and 5 under Benjamini-Yekutieli.
- R31 static-counterfactual A/B follow-up units: 28 under zero-aware Benjamini-Hochberg and 22 under zero-aware Benjamini-Yekutieli.
- R31 static-counterfactual A/B split under zero-aware Benjamini-Hochberg: 6 material and 22 targeted units; 19 increase-side and 9 depletion-side units.
- R33 independence-scale audit for those 28 A/B point-city units: 21 50 km metropolitan clusters, 22 GHSL urban centres and 10 GRACE-scale 300 km regional groups.
- R33 zero-aware block FDR counts: 276 CSR grid-cell blocks and 67 GRACE-scale 300 km blocks.
- R33 GSFC statistical sign support: 4/6 CSR-material baseline units at p < 0.05.
- R33 GSFC material support: 1/6 CSR-material baseline units; positive coastal GSFC material support: 0/3.
- R33 Monte Carlo materiality probabilities for the six baseline CSR-material units under the stated S_y prior: 0.30-0.55.
- R34 source registry and claim-evidence map present at repository root.
- R34 reference audit covers 37 manuscript references: 28 Crossref-verified, 3 DOI-resolver verified, 3 URL-reachable, 2 network warnings, and 1 CSR dataset DOI target-page warning.
- R36 reporting-threshold interpretation: abs(Delta P_liq) >= 0.01 is near the 98.6th percentile of the cohort.
- R36 regional payload: 28 A/B point-city units occupy 10 GRACE-scale 300 km regional groups, with 17 point-city units in the largest group.
- R36 negative-control style strata: maximum material-unit count is 0 across the reported low-sensitivity strata.
- R37 CSR-GFZ raw TWS sign agreement: 86.0% across all cities and 6/6 CSR-material units.
- R37 CSR-GFZ leakage-adjusted sign agreement: 69.1% across all cities and 6/6 CSR-material units.
- R37 GFZ-material counts at S_y = 0.10: 14 all-city raw TWS units and 33 all-city leakage-adjusted units; these are stress-test diagnostics, not replacement main results.
- R37 engineering-context enrichment: low Vs30, near-water proximity, at least two proxies and at least three proxies pass one-sided Fisher tests; high PGA and shallow WTD alone are not used as enrichment claims.
- R37 policy protocol tables present: `preimplementation_policy_protocol_r37.csv`, `regional_evidence_scorecard_r37.csv`, and `external_collaborator_role_matrix_r37.csv`.
- R39 JPL CRI Article status file present; status remains Earthdata-authentication protected unless credentials or an authenticated local NetCDF are supplied.
- R39 aquifer-context specific-yield products present: 6 review-prior classes, 444 city rows and 6 material-unit phase rows.
- R39 evidence-tier cards present: 5 regional cards.
- R39 named local release present: `releases/Dynamic_Groundwater_Liquefaction_Screening_Dataset_v1_0.zip`.
- R40 event-inventory benchmark present: 4 events, 326 observed liquefaction samples and 403 controls.
- R40 benchmark interpretation: dynamic groundwater update changes AUC by only -0.0025 to +0.0008, so it is a claim-boundary diagnostic.
- R41 regional hierarchy present: 10 GRACE-scale regional groups.
- R41 four-product evidence ladder present: 5 regional rows.
- Material + FDR-significant increases: 3.
- Material + FDR-significant decreases: 3.
- Material point-city screening units after 50 km metropolitan deduplication: 5 clusters.
- Material point-city screening units after GHSL urban-centre aggregation: 5 urban centres.
- Material screening-unit regions at GRACE-scale 300 km grouping: 2 regions.
- Positive material screening units within 50 km of the coastline: 3 of 3.
- GHSL R2024A polygon matches: 444/444 cities.
- CSR-GSFC screening-unit sign agreement: 6/6 CSR-material units.
- GSFC-material units among CSR-material units: 1/6.
- Positive coastal units that remain GSFC-material: 0/3.
- JPL CRI-filtered mascon: protected by Earthdata authentication in this run.
- Beijing: Delta P_liq approximately +0.0003, positive interval, recent TWS trend +0.57 cm yr-1.
- Sensitivity grid rows: 150.
- Six follow-up-unit city-grid rows: 900.
- Six baseline material screening units: all retain baseline direction under the positive-scaling sensitivity grid.
- R23 product-consensus table: GSFC is an independent sign check, not a materiality proof for every CSR-material unit.
- R24 JPL CRI status: correct CRI-filtered collection verified; protected NetCDF remains Earthdata-authentication blocked unless local credentials or an authenticated file are supplied.
- R24 Yokohama local groundwater evidence: 3,781 monthly records parsed from official municipal PDFs; 20 of 23 trend-qualified wells rise over 2015/04-2025/03; median slope about +0.0418 m yr-1.
- R24 Mumbai-Bhayandar local evidence status: DOI-verified Mumbai station evidence is contradictory to positive-recovery attribution, so the CSR-positive screen remains candidate-only.
- R25 Tokyo official representative groundwater evidence: 4 of 4 representative confined wells rise over 2015-2024; median OLS slope about +0.608 m yr-1.
- R25 Tokyo 2024 regional summary: 79 of 91 confined observation wells rising.
- R25 Tokyo Open Data / official PDF annual-table checks: 78 of 90 valid 2016 changes positive and 75 of 91 extracted 2022 changes positive.
- R25 CGWB source retry status: no successful access to the monitoring page, Greater Mumbai PDF or Maharashtra yearbook through proxy/direct sessions.
- R25 JPL CRI runner status: Earthdata-protected; no local credentials, `earthaccess` package or authenticated local NetCDF detected.
- R39 JPL CRI status: Article ledger generated; no JPL-derived numerical result is asserted without authenticated ingestion.
- R39/R40/R41/R42 dataset release status: local Zenodo-ready package generated with manifest, checksums, citation metadata, event-benchmark tables, display-order products and derived tables; GitHub release `v0.8.0-nature-water-article-r42` is published at `https://github.com/Johnsonlijian/groundwater-liquefaction-urban-hazard/releases/tag/v0.8.0-nature-water-article-r42`; Zenodo DOI minting remains pending author-controlled Zenodo publication.
- R42 Article display repair: `Fig2_global_payload_article.*`, `Fig3_regional_evidence_cards_article.*`, `Fig6_engineering_event_boundary_article.*`, `review_protocol_box1_r42.csv` and `article_display_reorder_summary_r42.json` are present.
- R45 visual-upgrade figure pack: `figures/visual_upgrade/` contains six code-generated SVG/PDF/PNG upgraded display candidates, an optional 3D mechanism hero and a contact sheet. These are visual re-expressions of the existing evidence and do not add new numerical claims.
- R46 formal figure factory: `figures_pro/` contains mirrored derived inputs,
  SVG/PDF/PNG/PPTX outputs, Blender source scripts, a Nature Water policy note,
  SHA-256 manifest and `audit_report.md`. The audit verifies file completeness,
  editable SVG provenance, selected numerical labels, preview resolution,
  placeholder/identity scans and the local Blender availability boundary.
- Largest follow-up-unit magnitude sensitivity factor in the deterministic grid: specific yield.
- R28 S_y* thresholds: the six CSR-material screening units remain material only for S_y at or below about 0.11-0.16.
- Beijing R28 S_y* threshold: never material across S_y = 0.05-0.25.
- Tokyo/Tianjin R28 context: material only at low S_y.
- R29 confidence ledger rows: 6 main-text rows and 7 detailed rows including the Beijing mechanism anchor.
- Median +0.01 water-table-rise flag: about 14.5 m.
- Beijing +0.01 water-table-rise flag: about 17.1 m.

`scripts\\analyze_v2.py` reconstructs the final city table and baseline material-unit table, but it expects the Natural Earth lake boundary data under `data_raw/` so that the inland-water-body exclusion can be recomputed.

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
- `Fig6_evidence_boundary.png`
- `Fig6_evidence_boundary.svg`
- `Fig6_evidence_boundary.pdf`
- `Fig2_event_hindcast_article.png`
- `Fig2_event_hindcast_article.svg`
- `Fig2_event_hindcast_article.pdf`
- `Fig2_global_payload_article.png`
- `Fig2_global_payload_article.svg`
- `Fig2_global_payload_article.pdf`
- `Fig3_regional_evidence_cards_article.png`
- `Fig3_regional_evidence_cards_article.svg`
- `Fig3_regional_evidence_cards_article.pdf`
- `Fig3_regional_hierarchical_screen_article.png`
- `Fig3_regional_hierarchical_screen_article.svg`
- `Fig3_regional_hierarchical_screen_article.pdf`
- `Fig4_evidence_tier_cards_article.png`
- `Fig4_evidence_tier_cards_article.svg`
- `Fig4_evidence_tier_cards_article.pdf`
- `Fig4_four_product_evidence_ladder_article.png`
- `Fig4_four_product_evidence_ladder_article.svg`
- `Fig4_four_product_evidence_ladder_article.pdf`
- `Fig5_aquifer_class_phase_article.png`
- `Fig5_aquifer_class_phase_article.svg`
- `Fig5_aquifer_class_phase_article.pdf`
- `Fig6_engineering_event_boundary_article.png`
- `Fig6_engineering_event_boundary_article.svg`
- `Fig6_engineering_event_boundary_article.pdf`
- `FigS1_yokohama_local_groundwater_r24.png`
- `FigS1_yokohama_local_groundwater_r24.svg`
- `FigS1_yokohama_local_groundwater_r24.pdf`
- `FigS2_tokyo_representative_groundwater_r25.png`
- `FigS2_tokyo_representative_groundwater_r25.svg`
- `FigS2_tokyo_representative_groundwater_r25.pdf`
- `FigS3_water_table_followup_flag_spatial_robustness.png`
- `FigS3_water_table_followup_flag_spatial_robustness.svg`
- `FigS3_water_table_followup_flag_spatial_robustness.pdf`
- `FigS4_r37_third_product_engineering_protocol.png`
- `FigS4_r37_third_product_engineering_protocol.svg`
- `FigS4_r37_third_product_engineering_protocol.pdf`

Visual-upgrade candidates are stored under `figures/visual_upgrade/`:

- `Fig1_3D_DGLS_mechanism_upgrade.*`
- `Fig2_global_null_regional_payload_upgrade.*`
- `Fig3_regional_evidence_arena_upgrade.*`
- `Fig4_product_evidence_ladder_upgrade.*`
- `Fig5_aquifer_sy_phase_arena_upgrade.*`
- `Fig6_engineering_event_protocol_arena_upgrade.*`
- `GraphicalAbstract_3D_DGLS_mechanism_hero.*`
- `contact_sheet.png`

The formal Nature Water figure factory is stored under `figures_pro/`:

- `figures_pro/export/svg/`: editable SVG sources for Fig. 1-Fig. 6, Box 1 and
  the optional graphical abstract.
- `figures_pro/export/pdf/`: vector PDF derivatives.
- `figures_pro/export/png_600dpi/`: high-resolution previews and contact sheet.
- `figures_pro/export/pptx/NatureWater_Editable_Figure_Upgrade_Pack.pptx`:
  editable deck for author micro-adjustment.
- `figures_pro/blender/`: Blender Python source for the Fig. 1 3D aquifer
  cutaway scene. A `.blend` render requires a local Blender installation.
- `figures_pro/audit_report.md` and `figures_pro/export/manifest_sha256.txt`:
  figure-integrity audit and checksums.
- `figures_pro/journal_policy_note.md`: Nature Water Article, double-anonymized
  review and AI-image policy notes checked on 2026-06-09.

## Guardrails

Do not reinterpret the outputs as precise city-scale engineering predictions. GRACE/GRACE-FO provides a regional groundwater-storage driver, while cities are exposure units. The analysis does not claim a diffuse global increase and does not claim that groundwater causes earthquakes.
