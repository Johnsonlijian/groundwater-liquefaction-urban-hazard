# R34 Reference Audit

Date: 2026-06-08

References checked: 37

## Status counts

- `verified_crossref`: 28
- `verified_doi_resolves`: 3
- `verified_url_reachable`: 3
- `warning_doi_target`: 1
- `warning_network_error`: 2

## Warnings / Manual Follow-up

- Ref. 5: `warning_network_error` - ConnectionError: HTTPSConnectionPool(host='faculty.engineering.ucdavis.edu', port=443): Read timed out.
- Ref. 30: `warning_network_error` - ReadTimeout: HTTPSConnectionPool(host='earthdata.nasa.gov', port=443): Read timed out. (read timeout=16)
- Ref. 33: `warning_doi_target` - Crossref 404; doi.org GET 500; http://www2.csr.utexas.edu/grace/RL06_mascons.html

## Interpretation

This is an author-side audit. Crossref/doi.org/URL reachability supports reference authenticity, but final bibliography decisions still require author review for reports, official web pages and dataset landing pages.

## Article addendum, 2026-06-09

The R34 audit above covered the then-current 37-reference Nature Water package.
The current Article manuscript contains 41 references. Therefore R34 should not
be cited as a complete audit of the Article bibliography until the audit script
is rerun on the Article reference list.

New Article references requiring inclusion in the next formal audit:

- Ref. 38: Johnson, A. I. *Specific yield: compilation of specific yields for
  various materials*. U.S. Geological Survey Water-Supply Paper 1662-D (1967).
  DOI: `10.3133/wsp1662D`.
- Ref. 39: Lv, M. et al. A comprehensive review of specific yield in land
  surface and groundwater studies. *Journal of Advances in Modeling Earth
  Systems* **13**, e2020MS002270 (2021). DOI: `10.1029/2020MS002270`.
- Ref. 40: Schmitt, R. G. et al. *An Open Repository of
  Earthquake-Triggered Ground-Failure Inventories*. U.S. Geological Survey data
  release collection (2017). DOI: `10.5066/F7H70DB4`.
- Ref. 41: Allstadt, K. E. & Thompson, E. M. *Inventory of liquefaction
  features triggered by the 7 January 2020 M6.4 Puerto Rico earthquake*. U.S.
  Geological Survey data release (2021). DOI: `10.5066/P9HZRXI9`.

Manual-warning reinterpretation for R34 warnings:

- Ref. 5 should be treated as an official-report landing/PDF reachability item,
  not a fabricated citation.
- Ref. 30 should be treated as an official PO.DAAC/JPL dataset DOI page with
  Earthdata-protected data access.
- Ref. 33 should be treated as a CSR official-data-page support item when DOI
  landing is unstable.
