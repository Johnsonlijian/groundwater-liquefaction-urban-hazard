# Method limits and claim boundary

This package supports a directional screening analysis.

## Supported claims

- Observed groundwater change creates regional, bidirectional shifts in modelled liquefaction probability.
- The global mean response across the screened city cohort is near zero.
- Six cities are both material under the chosen threshold and FDR-significant in the recent-window analysis.
- The six baseline material hotspots keep their direction across the reported 150-combination sensitivity grid and 900 hotspot-city evaluations.
- In the deterministic parameter grid, specific yield is the largest hotspot-magnitude sensitivity factor, followed by groundwater-trend magnitude.
- Recharge-side increases and depletion-side decreases should be interpreted as a water-security versus seismic-safety trade-off.

## Unsupported claims

- Groundwater causes earthquakes.
- Liquefaction hazard is increasing everywhere.
- GRACE/GRACE-FO resolves city- or neighbourhood-scale shallow groundwater.
- The reported city values are precise engineering predictions or factor-of-safety estimates.
- The screening tiers in `policy_priority_table_v2.csv` are regulatory thresholds.
- The population-weighted exposure summary is an engineering loss estimate.
- Groundwater depletion is a seismic-safety benefit.

## Scale statement

GRACE/GRACE-FO constrains storage change at regional scale. The city is used as an exposure unit located within that regional driver. Site-specific engineering assessment requires local wells, stratigraphy, susceptibility mapping and event-specific shaking.
