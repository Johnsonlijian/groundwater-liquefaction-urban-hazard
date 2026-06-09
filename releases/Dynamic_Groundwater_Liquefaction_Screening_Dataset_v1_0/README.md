# DGLS-v1: Dynamic Groundwater-Liquefaction Screening Dataset for Seismic Urban Basins

Local release prepared: 2026-06-09T02:59:55.436626+00:00

This derived-data release supports the manuscript "Dynamic groundwater trajectories define review needs for liquefaction-sensitive water management".

## Contents

- 444 city exposure units and modelled Delta P_liq outputs.
- Historical-event inventory benchmark tables for Article claim calibration.
- Zero-aware FDR and static-counterfactual review tiers.
- 50 km / GHSL / 300 km independence-scale diagnostics.
- CSR, GSFC and GFZ product-support tables.
- JPL CRI access status: `earthdata_authentication_required_not_ingested`. The protected NetCDF is not redistributed and is not used as a claim unless authenticated sampling is completed.
- Aquifer-context S_y review priors and phase calculations.
- Evidence-tier cards for regional sign and claim class.
- Article display-order products, engineering-context enrichment diagnostics and non-regulatory review protocol.

## Article display sequence

The current Article display sequence is:

1. `Fig1_mechanism.*`
2. `Fig2_global_payload_article.*`
3. `Fig3_regional_evidence_cards_article.*`
4. `Fig4_four_product_evidence_ladder_article.*`
5. `Fig5_aquifer_class_phase_article.*`
6. `Fig6_engineering_event_boundary_article.*`
7. main-text Table/Box 1 protocol (`review_protocol_box1_r42.csv`)

Legacy/supporting figure stems such as `Fig2_global_signresolved.*`, `Fig2_event_hindcast_article.*`, `Fig3_regional.*` and `Fig6_evidence_boundary.*` are retained for reproducibility and audit trail. They are not the current Article display order.

## Boundary

This is a derived screening dataset, not a hazard map, city ranking, regulatory threshold, damage forecast or engineering factor-of-safety dataset. GRACE/GRACE-FO products are regional storage drivers. Local wells, S_y, sediment and liquefaction records must replace review priors before site use.

## DOI

Zenodo DOI: to be minted by the author after repository upload/release approval.
