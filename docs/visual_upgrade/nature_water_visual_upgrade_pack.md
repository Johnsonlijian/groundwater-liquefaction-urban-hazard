# Nature Water Visual Upgrade Pack

## Goal

Upgrade the Article figure set from functional data displays to high-information, Nature-style argument surfaces while keeping every scientific claim evidence-bounded and editable.

## Provenance Boundary

The web-generated reference images supplied by the author are used only as layout inspiration: dense paneling, arena-style hierarchy, icons, evidence badges and strong takeaway strips. No AI-generated raster is used as a submission-facing scientific figure.

## Export Contract

- Primary editable outputs: SVG files under `paper_figures/output/svg/`.
- Secondary editable/storyboard output: one PPTX deck under `paper_figures/output/pptx/`.
- Submission derivatives: PDF and PNG previews under `paper_figures/output/pdf/` and `paper_figures/output/png/`.

## Figure Storyline

| Figure | Role | Single takeaway | Boundary |
|---|---|---|---|
| Fig. 1 | 3D mechanism / framework | Groundwater management moves a water-table state variable inside a published liquefaction screen. | Schematic mechanism, not engineering design or site prediction. |
| Fig. 2 | Global arena | The global mean is null, but regional review payload remains. | City points are exposure markers; GRACE inference is regional. |
| Fig. 3 | Regional evidence arena | Five regional cases have different evidence classes and claim strength. | Positive coastal cases remain sign-supported/candidate, not globally material proof. |
| Fig. 4 | Product ladder | CSR, GSFC, GFZ, JPL and local evidence are a guardrail ladder, not a single-raster proof. | JPL CRI remains auth boundary unless ingested. |
| Fig. 5 | Aquifer phase / materiality | Sign is product-tested; materiality is aquifer-conditioned by S_y. | Aquifer classes are priors, not local calibration. |
| Fig. 6 | Engineering and event boundary | Flags concentrate in susceptible settings; event benchmark limits prediction claims. | Event test is neutral/negative for broad dynamic superiority. |

## Visual Grammar

- Navy: framework, evidence hierarchy, review protocol.
- Teal/blue: depletion-side or product guardrail.
- Coral/red: recharge-side or contradiction/candidate warning.
- Green: supported local mechanism or enrichment.
- Amber: authentication or boundary.
- Grey: null, scale, and non-regulatory constraints.

## Implementation

Chosen tool: Python-generated direct SVG plus python-pptx.

Reason: SVG preserves editable vector text/shapes for manuscript figures; PPTX gives the author a familiar editable slide layer for micro-adjustment. Python is used only as a reproducible vector engine, not as an AI image generator.

