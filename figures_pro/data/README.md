# Figure Data Mirror

These files mirror selected `data_derived/` products used by the figure
factory. They are copied here to make each figure's data dependency explicit.

- `dgls_city_outputs.csv`: 444 city exposure-unit outputs.
- `regional_groups.csv`: 300-km GRACE-scale regional groups.
- `product_consensus.csv`: CSR/GSFC/GFZ/JPL/local evidence ladder.
- `engineering_enrichment.csv`: engineering-context enrichment tests.
- `event_boundary.csv`: historical-event boundary benchmark metrics.
- `sy_phase.csv`: aquifer-context specific-yield phase table.
- `evidence_cards.csv`: regional evidence card ledger.
- `protocol_steps.csv`: seven-step non-regulatory protocol.
- `display_summary.json`: global-null/regional-payload counts.

Do not edit these mirrored files by hand. Regenerate them from `data_derived/`
or update the source script when upstream outputs change.
