"""R37 third-product, engineering-context and policy-protocol increments.

This script adds evidence that is useful for Nature Water review without
changing the primary model:

1. sample the credential-free GFZ GravIS RL06 TWS product at the 444 city
   exposure points and compare 2015-2024 signs with CSR and GSFC;
2. repeat the GFZ trend test after subtracting the provided spatial-leakage
   layer as a coastal/leakage stress test;
3. test whether A/B follow-up units are enriched in engineering-relevant
   proxy settings already used by the Zhu et al. model;
4. write a region-level validation scorecard, policy protocol table and
   collaborator-needs matrix for submission-facing use.

The outputs are diagnostics and evidence ledgers. They do not create a new
site-specific hazard map, do not assert earthquake causation and do not treat
GRACE as a city well.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from scipy.spatial import cKDTree
from scipy.stats import fisher_exact, linregress

from zhu2017 import p_liquefaction


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
RAW = ROOT / "data_raw"
FIG = ROOT / "figures"
COLLAB = ROOT / "collaboration"

GFZ_NC = RAW / "grace" / "gfz" / "GRAVIS-3_GFZOP_0600_TWS_GRID_GFZ_0006.nc"

NYEARS_RECENT = 10
SY_DEFAULT = 0.10
MATERIAL = 0.01
TARGETED = 0.005


def load_city_model_frame() -> pd.DataFrame:
    results = pd.read_csv(DER / "city_results_v2.csv")
    inputs = pd.read_csv(DER / "city_inputs.csv")[
        ["name", "country", "lat", "lon", "pga_475_g", "vs30", "precip", "dw_km"]
    ]
    cities = results.merge(
        inputs,
        on=["name", "country", "lat", "lon"],
        how="left",
        validate="one_to_one",
    )
    cities.insert(0, "city_row_id", np.arange(len(cities), dtype=int))
    return cities


def decimal_years_from_gfz_time(time_values: np.ndarray) -> np.ndarray:
    origin = pd.Timestamp("2002-04-18")
    dates = origin + pd.to_timedelta(np.asarray(time_values, float), unit="D")
    return np.array(
        [
            d.year + (d.dayofyear - 0.5) / (366.0 if d.is_leap_year else 365.0)
            for d in pd.DatetimeIndex(dates)
        ],
        dtype=float,
    )


def vector_trend_cm_yr(values: np.ndarray, years: np.ndarray, start: int = 2015, end: int = 2024) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return OLS slope, p value and n months for columns of a time x city matrix."""
    mask_time = (years >= start) & (years < end + 1)
    x_all = years[mask_time]
    y_all = values[mask_time, :]
    slopes = np.full(y_all.shape[1], np.nan)
    pvals = np.full(y_all.shape[1], np.nan)
    nmonths = np.zeros(y_all.shape[1], dtype=int)
    for j in range(y_all.shape[1]):
        y = y_all[:, j].astype(float)
        mask = np.isfinite(y)
        nmonths[j] = int(mask.sum())
        if mask.sum() >= 12:
            lr = linregress(x_all[mask], y[mask])
            slopes[j] = float(lr.slope)
            pvals[j] = float(lr.pvalue)
    return slopes, pvals, nmonths


def lonlat_to_xyz(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    lon_r = np.deg2rad(lon)
    lat_r = np.deg2rad(lat)
    return np.column_stack(
        (
            np.cos(lat_r) * np.cos(lon_r),
            np.cos(lat_r) * np.sin(lon_r),
            np.sin(lat_r),
        )
    )


def chord_to_km(chord: np.ndarray) -> np.ndarray:
    return 2.0 * 6371.0088 * np.arcsin(np.clip(chord / 2.0, 0.0, 1.0))


def finite_sign(values: pd.Series | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, float)
    return np.where(np.isfinite(arr), np.sign(arr), 0).astype(int)


def delta_p_from_trend(cities: pd.DataFrame, trend_cm_yr: np.ndarray) -> np.ndarray:
    pgv = cities["pga_475_g"].to_numpy(float) * 100.0
    base = p_liquefaction(
        pgv,
        cities["vs30"].to_numpy(float),
        cities["precip"].to_numpy(float),
        cities["dw_km"].to_numpy(float),
        cities["wtd"].to_numpy(float),
    )
    delta_wtd_m = -(np.asarray(trend_cm_yr, float) * NYEARS_RECENT / 100.0) / SY_DEFAULT
    new_wtd = np.maximum(cities["wtd"].to_numpy(float) + delta_wtd_m, 0.0)
    updated = p_liquefaction(
        pgv,
        cities["vs30"].to_numpy(float),
        cities["precip"].to_numpy(float),
        cities["dw_km"].to_numpy(float),
        new_wtd,
    )
    return updated - base


def sample_gfz_product(cities: pd.DataFrame) -> pd.DataFrame:
    if not GFZ_NC.exists():
        raise FileNotFoundError(f"Missing GFZ GravIS NetCDF: {GFZ_NC}")

    ds = xr.open_dataset(GFZ_NC, decode_times=False)
    try:
        lats = np.asarray(ds["lat"].values, float)
        lons = np.asarray(ds["lon"].values, float)
        city_lat = cities["lat"].to_numpy(float)
        city_lon = cities["lon"].to_numpy(float) % 360.0

        lat_idx = np.abs(lats[:, None] - city_lat[None, :]).argmin(axis=0)
        lon_idx = np.abs(lons[:, None] - city_lon[None, :]).argmin(axis=0)

        finite_mask = np.isfinite(
            np.asarray(ds["tws"].isel(time=slice(-12, None)).mean(dim="time", skipna=True).values, float)
        )
        sampled_finite = finite_mask[lat_idx, lon_idx]
        nearest_grid_distance_km = np.zeros(len(cities), dtype=float)
        if not sampled_finite.all():
            finite_lat_idx, finite_lon_idx = np.where(finite_mask)
            finite_lats = lats[finite_lat_idx]
            finite_lons = lons[finite_lon_idx]
            tree = cKDTree(lonlat_to_xyz(finite_lons, finite_lats))
            bad = np.where(~sampled_finite)[0]
            chord, nearest = tree.query(lonlat_to_xyz(city_lon[bad], city_lat[bad]), k=1)
            lat_idx[bad] = finite_lat_idx[nearest]
            lon_idx[bad] = finite_lon_idx[nearest]
            nearest_grid_distance_km[bad] = chord_to_km(chord)
        years = decimal_years_from_gfz_time(ds["time"].values)

        tws_values = np.asarray(ds["tws"].values[:, lat_idx, lon_idx], float)
        leakage_values = np.asarray(ds["leakage"].values[:, lat_idx, lon_idx], float)
        corrected_values = tws_values - leakage_values

        tws_slope, tws_p, tws_n = vector_trend_cm_yr(tws_values, years)
        corr_slope, corr_p, corr_n = vector_trend_cm_yr(corrected_values, years)
    finally:
        ds.close()

    out = cities[
        [
            "city_row_id",
            "name",
            "country",
            "lat",
            "lon",
            "population",
            "pga",
            "wtd",
            "tws_cm_yr",
            "dP",
            "fdr_sig",
        ]
    ].copy()
    out["gfz_grid_lat"] = lats[lat_idx]
    out["gfz_grid_lon"] = lons[lon_idx]
    out["gfz_nearest_finite_grid_distance_km"] = nearest_grid_distance_km
    out["gfz_tws_cm_yr"] = tws_slope
    out["gfz_tws_p"] = tws_p
    out["gfz_tws_n_months"] = tws_n
    out["gfz_leakage_corrected_tws_cm_yr"] = corr_slope
    out["gfz_leakage_corrected_p"] = corr_p
    out["gfz_leakage_corrected_n_months"] = corr_n
    out["gfz_dP_sy010"] = delta_p_from_trend(cities, tws_slope)
    out["gfz_leakage_corrected_dP_sy010"] = delta_p_from_trend(cities, corr_slope)
    out["csr_sign"] = finite_sign(out["tws_cm_yr"])
    out["gfz_sign"] = finite_sign(out["gfz_tws_cm_yr"])
    out["gfz_leakage_corrected_sign"] = finite_sign(out["gfz_leakage_corrected_tws_cm_yr"])
    out["csr_gfz_sign_match"] = out["csr_sign"] == out["gfz_sign"]
    out["csr_gfz_leakage_corrected_sign_match"] = out["csr_sign"] == out["gfz_leakage_corrected_sign"]
    out["gfz_material_sy010"] = out["gfz_dP_sy010"].abs() >= MATERIAL
    out["gfz_targeted_sy010"] = out["gfz_dP_sy010"].abs() >= TARGETED
    out["gfz_leakage_corrected_material_sy010"] = out["gfz_leakage_corrected_dP_sy010"].abs() >= MATERIAL
    out["gfz_leakage_corrected_targeted_sy010"] = out["gfz_leakage_corrected_dP_sy010"].abs() >= TARGETED
    out.to_csv(DER / "gfz_gravis_city_trends_r37.csv", index=False)

    gsfc = pd.read_csv(DER / "gsfc_city_trends_r21.csv")[
        ["name", "country", "lat", "lon", "gsfc_recent_tws_cm_yr", "gsfc_recent_dP", "csr_gsfc_recent_sign_match"]
    ]
    consensus = out.merge(gsfc, on=["name", "country", "lat", "lon"], how="left", validate="one_to_one")
    consensus["material_csr_sy010"] = consensus["dP"].abs() >= MATERIAL
    consensus["three_product_sign_consensus"] = (
        (finite_sign(consensus["tws_cm_yr"]) == finite_sign(consensus["gsfc_recent_tws_cm_yr"]))
        & (finite_sign(consensus["tws_cm_yr"]) == finite_sign(consensus["gfz_tws_cm_yr"]))
    )
    consensus["three_product_plus_leakage_sign_consensus"] = (
        consensus["three_product_sign_consensus"]
        & (finite_sign(consensus["tws_cm_yr"]) == finite_sign(consensus["gfz_leakage_corrected_tws_cm_yr"]))
    )
    consensus.to_csv(DER / "three_product_city_consensus_r37.csv", index=False)

    material_names = pd.read_csv(DER / "material_screening_units_v2.csv")[
        ["name", "country", "direction", "dP"]
    ].rename(columns={"dP": "csr_material_dP"})
    material = consensus.merge(material_names, on=["name", "country"], how="inner")
    material["safe_gfz_interpretation"] = np.where(
        material["three_product_plus_leakage_sign_consensus"],
        "CSR/GSFC/GFZ signs agree and GFZ leakage-adjusted sign agrees; magnitude remains product- and S_y-dependent",
        np.where(
            material["three_product_sign_consensus"],
            "CSR/GSFC/GFZ raw TWS signs agree, but leakage-adjusted GFZ weakens or reverses the sign",
            "third-product sign does not fully reproduce the CSR material-unit sign",
        ),
    )
    material.to_csv(DER / "material_unit_gfz_gravis_stress_test_r37.csv", index=False)

    summary_rows = [
        {
            "set": "all 444 city exposure units",
            "n": int(len(consensus)),
            "csr_gfz_sign_match_fraction": float(consensus["csr_gfz_sign_match"].mean()),
            "csr_gfz_leakage_corrected_sign_match_fraction": float(consensus["csr_gfz_leakage_corrected_sign_match"].mean()),
            "three_product_sign_consensus_fraction": float(consensus["three_product_sign_consensus"].mean()),
            "three_product_plus_leakage_sign_consensus_fraction": float(consensus["three_product_plus_leakage_sign_consensus"].mean()),
            "gfz_material_sy010_count": int(consensus["gfz_material_sy010"].sum()),
            "gfz_leakage_corrected_material_sy010_count": int(consensus["gfz_leakage_corrected_material_sy010"].sum()),
        },
        {
            "set": "six CSR-material point-city units",
            "n": int(len(material)),
            "csr_gfz_sign_match_fraction": float(material["csr_gfz_sign_match"].mean()),
            "csr_gfz_leakage_corrected_sign_match_fraction": float(material["csr_gfz_leakage_corrected_sign_match"].mean()),
            "three_product_sign_consensus_fraction": float(material["three_product_sign_consensus"].mean()),
            "three_product_plus_leakage_sign_consensus_fraction": float(material["three_product_plus_leakage_sign_consensus"].mean()),
            "gfz_material_sy010_count": int(material["gfz_material_sy010"].sum()),
            "gfz_leakage_corrected_material_sy010_count": int(material["gfz_leakage_corrected_material_sy010"].sum()),
        },
    ]
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(DER / "gfz_gravis_stress_summary_r37.csv", index=False)
    return consensus, material, summary


def engineering_enrichment() -> pd.DataFrame:
    r31 = pd.read_csv(DER / "static_observed_triage_tier_change_r31.csv")
    policy = pd.read_csv(DER / "policy_followup_table_v2.csv")[
        [
            "name",
            "country",
            "lat",
            "lon",
            "soft_soil_proxy_vs30_le_360",
            "shallow_wtd_proxy_le_10m",
            "near_water_proxy_le_5km",
            "high_shaking_proxy_pga_ge_0p2g",
            "susceptibility_proxy_count",
        ]
    ]
    df = r31.merge(policy, on=["name", "country", "lat", "lon"], how="left", validate="one_to_one")
    if "susceptibility_proxy_count" not in df.columns:
        if "susceptibility_proxy_count_x" in df.columns:
            df["susceptibility_proxy_count"] = df["susceptibility_proxy_count_x"]
        elif "susceptibility_proxy_count_y" in df.columns:
            df["susceptibility_proxy_count"] = df["susceptibility_proxy_count_y"]
    follow = df["ab_followup_bh"].astype(bool)

    proxies = {
        "soft_soil_proxy_vs30_le_360": "low Vs30 proxy (<=360 m s-1)",
        "shallow_wtd_proxy_le_10m": "shallow baseline water table proxy (<=10 m)",
        "near_water_proxy_le_5km": "near mapped water proxy (<=5 km)",
        "high_shaking_proxy_pga_ge_0p2g": "high PGA475 proxy (>=0.2 g)",
    }
    rows: list[dict[str, object]] = []
    for col, label in proxies.items():
        flag = df[col].astype(bool)
        a = int((follow & flag).sum())
        b = int((follow & ~flag).sum())
        c = int((~follow & flag).sum())
        d = int((~follow & ~flag).sum())
        odds, p = fisher_exact([[a, b], [c, d]], alternative="greater")
        rows.append(
            {
                "proxy": col,
                "proxy_label": label,
                "followup_with_proxy": a,
                "followup_without_proxy": b,
                "nonfollowup_with_proxy": c,
                "nonfollowup_without_proxy": d,
                "followup_fraction_with_proxy": a / max(a + b, 1),
                "cohort_fraction_with_proxy": (a + c) / len(df),
                "odds_ratio_followup_enrichment": float(odds),
                "fisher_greater_p": float(p),
                "safe_interpretation": (
                    "enriched among A/B follow-up units; use as engineering-context support"
                    if p < 0.05 and a / max(a + b, 1) > (a + c) / len(df)
                    else "not enriched at this threshold; do not use as an enrichment claim"
                ),
            }
        )

    for threshold in [2, 3, 4]:
        flag = df["susceptibility_proxy_count"] >= threshold
        a = int((follow & flag).sum())
        b = int((follow & ~flag).sum())
        c = int((~follow & flag).sum())
        d = int((~follow & ~flag).sum())
        odds, p = fisher_exact([[a, b], [c, d]], alternative="greater")
        rows.append(
            {
                "proxy": f"susceptibility_proxy_count_ge_{threshold}",
                "proxy_label": f"at least {threshold} engineering-context proxies",
                "followup_with_proxy": a,
                "followup_without_proxy": b,
                "nonfollowup_with_proxy": c,
                "nonfollowup_without_proxy": d,
                "followup_fraction_with_proxy": a / max(a + b, 1),
                "cohort_fraction_with_proxy": (a + c) / len(df),
                "odds_ratio_followup_enrichment": float(odds),
                "fisher_greater_p": float(p),
                "safe_interpretation": (
                    "enriched among A/B follow-up units; use as engineering-context support"
                    if p < 0.05 and a / max(a + b, 1) > (a + c) / len(df)
                    else "not enriched at this threshold; do not use as an enrichment claim"
                ),
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(DER / "engineering_susceptibility_enrichment_r37.csv", index=False)

    profile_cols = [
        "name",
        "country",
        "lat",
        "lon",
        "population_million",
        "dP",
        "screening_tier",
        "direction_side",
        "ab_followup_bh",
        "material_bh_zero_aware",
        "soft_soil_proxy_vs30_le_360",
        "shallow_wtd_proxy_le_10m",
        "near_water_proxy_le_5km",
        "high_shaking_proxy_pga_ge_0p2g",
        "susceptibility_proxy_count",
    ]
    df.loc[follow, profile_cols].to_csv(DER / "ab_followup_engineering_profile_r37.csv", index=False)
    return out


def region_validation_scorecard(consensus: pd.DataFrame) -> pd.DataFrame:
    product = pd.read_csv(DER / "product_support_table_r33.csv")
    sy = pd.read_csv(DER / "specific_yield_thresholds_r28.csv")
    sy_lookup = {
        f"{r.name}|{r.country}": r.sy_material_threshold
        for r in sy.itertuples(index=False)
    }
    material_lookup = {
        f"{r.name}|{r.country}": r
        for r in product.itertuples(index=False)
    }

    def gfz_status(names: list[str], countries: list[str]) -> str:
        sub = consensus[
            consensus["name"].isin(names)
            & consensus["country"].isin(countries)
        ]
        if sub.empty:
            return "not sampled in named exposure units"
        raw = int(sub["csr_gfz_sign_match"].sum())
        leak = int(sub["csr_gfz_leakage_corrected_sign_match"].sum())
        return f"GFZ raw sign match {raw}/{len(sub)}; GFZ leakage-adjusted sign match {leak}/{len(sub)}"

    rows = [
        {
            "regional_unit": "North China Plain / Beijing-Tianjin-Hebei",
            "role": "recharge-side mechanism anchor",
            "primary_exposure_names": "Beijing; Tianjin",
            "csr_screen_status": "positive/recharge-side sign but Beijing is sub-material in global screen",
            "gsfc_status": "used as independent sign guardrail where available",
            "gfz_gravis_status": gfz_status(["Beijing", "Tianjin"], ["CN"]),
            "direct_well_evidence": "high: >2000 wells and about 190000 measurements in Long et al. 2025; Beijing urban well mechanism in Li/Wang et al. 2025",
            "insar_or_subsidence_evidence": "high deformation context; regional subsidence/recovery is heterogeneous",
            "engineering_susceptibility_context": "requires local alluvium/fill/CPT-SPT confirmation; not a site-hazard class",
            "coastal_leakage_risk": "low-to-moderate for Beijing; regional storage scale remains the main limitation",
            "specific_yield_support": "not assigned; Beijing not material across tested S_y range",
            "claim_class": "mechanism anchor, not material city validation",
            "submission_use": "Use to show recharge can raise the water-table term under managed recovery.",
        },
        {
            "regional_unit": "Tokyo Bay / Yokohama",
            "role": "coastal positive sign-supported screening unit",
            "primary_exposure_names": "Tokyo; Yokohama",
            "csr_screen_status": "Yokohama CSR-material at S_y=0.10; Tokyo targeted/sub-material depending S_y",
            "gsfc_status": "Yokohama GSFC sign support but not GSFC-material",
            "gfz_gravis_status": gfz_status(["Tokyo", "Yokohama"], ["JP"]),
            "direct_well_evidence": "medium-high sign: Yokohama 20/23 rising; Tokyo official records mostly rising",
            "insar_or_subsidence_evidence": "medium: deformation monitoring context exists; not proof of shallow liquefiable heads",
            "engineering_susceptibility_context": "coastal/near-water setting; local reclaimed/alluvial/fill data required before engineering claims",
            "coastal_leakage_risk": "high; positive interpretation requires leakage-aware product and local evidence note",
            "specific_yield_support": f"Yokohama S_y*={sy_lookup.get('Yokohama|JP', np.nan):.3f}; material only for low-to-moderate S_y",
            "claim_class": "sign-supported positive screen, not independent material proof",
            "submission_use": "Use as coastal, local-sign-supported follow-up case; state leakage and materiality boundaries plainly.",
        },
        {
            "regional_unit": "Mumbai-Bhayandar / Mumbai coast",
            "role": "candidate/guardrail positive CSR unit",
            "primary_exposure_names": "Mumbai; Bhayandar",
            "csr_screen_status": "CSR-material positive at S_y=0.10",
            "gsfc_status": "GSFC direction match only; no statistical sign or material support",
            "gfz_gravis_status": gfz_status(["Mumbai", "Bhayandar"], ["IN"]),
            "direct_well_evidence": "contradictory guardrail: Mumbai station literature supports depletion/increasing depth",
            "insar_or_subsidence_evidence": "medium-high Mumbai coastal subsidence context; not Bhayandar-specific validation",
            "engineering_susceptibility_context": "coastal/near-water urban setting; local hydrogeology contradicts a positive-recharge claim",
            "coastal_leakage_risk": "very high; do not present as positive validation",
            "specific_yield_support": f"Mumbai/Bhayandar S_y* approx {sy_lookup.get('Mumbai|IN', np.nan):.3f}/{sy_lookup.get('Bhayandar|IN', np.nan):.3f}",
            "claim_class": "candidate-only / contradiction boundary",
            "submission_use": "Use as a cautionary example of why local wells and leakage-aware checks are mandatory.",
        },
        {
            "regional_unit": "Delhi / New Delhi",
            "role": "depletion-side material/support case",
            "primary_exposure_names": "Delhi; New Delhi",
            "csr_screen_status": "negative/depletion-side material or targeted screen",
            "gsfc_status": "Delhi is the only GSFC-material support case among six CSR-material units",
            "gfz_gravis_status": gfz_status(["Delhi", "New Delhi"], ["IN"]),
            "direct_well_evidence": "medium-high: CGWB station literature shows long-term depletion across most of DMR except Yamuna floodplains",
            "insar_or_subsidence_evidence": "high heterogeneous groundwater-linked subsidence/recovery context",
            "engineering_susceptibility_context": "Yamuna/floodplain exceptions require local sediment and head review",
            "coastal_leakage_risk": "low",
            "specific_yield_support": f"Delhi S_y*={sy_lookup.get('Delhi|IN', np.nan):.3f} if present",
            "claim_class": "strong depletion-side product/material anchor",
            "submission_use": "Use to show the false-safety paradox: lower liquefaction metric does not mean reduced infrastructure risk.",
        },
        {
            "regional_unit": "Lahore / Punjab belt",
            "role": "depletion-side local well + InSAR anchor",
            "primary_exposure_names": "Lahore; Ludhiana",
            "csr_screen_status": "negative/depletion-side material or targeted screen",
            "gsfc_status": "sign support varies by city; not a uniform material claim",
            "gfz_gravis_status": gfz_status(["Lahore", "Ludhiana"], ["PK", "IN"]),
            "direct_well_evidence": "high for Lahore borehole/GRACE evidence; broader Punjab/NW India depletion supported by regional literature",
            "insar_or_subsidence_evidence": "high for Lahore PS-InSAR; medium for broader Punjab SBAS-InSAR",
            "engineering_susceptibility_context": "do not merge Pakistan Lahore and Indian Punjab as one aquifer without cautious regional wording",
            "coastal_leakage_risk": "low",
            "specific_yield_support": f"Lahore/Ludhiana S_y* approx {sy_lookup.get('Lahore|PK', np.nan):.3f}/{sy_lookup.get('Ludhiana|IN', np.nan):.3f}",
            "claim_class": "strong depletion/subsidence context; regional grouping must stay cautious",
            "submission_use": "Use as a depletion-side paradox and multi-hazard accounting case.",
        },
    ]
    out = pd.DataFrame(rows)
    out.to_csv(DER / "regional_validation_scorecard_r37.csv", index=False)
    return out


def write_policy_and_collaboration_tables() -> None:
    protocol = pd.DataFrame(
        [
            {
                "step": 1,
                "protocol_stage": "Eligibility",
                "review_question": "Is the planned water-management change in a seismic basin with susceptible urban ground?",
                "minimum_evidence": "PGA, Vs30/proxy sediment, shallow baseline water table, distance to water and exposed urban assets",
                "non_regulatory_action": "Enter groundwater-liquefaction review if several proxies align",
                "boundary": "Not a hazard class or permit rule",
            },
            {
                "step": 2,
                "protocol_stage": "Direction",
                "review_question": "Will the project or management trajectory shoal or deepen the water table?",
                "minimum_evidence": "Regional GRACE/GRACE-FO sign plus local wells where available",
                "non_regulatory_action": "Classify as recharge-side, depletion-side or unresolved",
                "boundary": "GRACE is regional storage, not a city well",
            },
            {
                "step": 3,
                "protocol_stage": "Magnitude",
                "review_question": "Could the trajectory cross a modelled screening increment?",
                "minimum_evidence": "A/B/C follow-up tier, water-table-rise flag and local specific yield where available",
                "non_regulatory_action": "Replace global S_y with local hydrogeology before decisions",
                "boundary": "Delta P_liq is a screening increment, not factor of safety",
            },
            {
                "step": 4,
                "protocol_stage": "Coastal/leakage check",
                "review_question": "Could leakage, reclamation, land-water mixing or deformation alter the sign?",
                "minimum_evidence": "Distance to coast, GFZ/JPL-style leakage check, InSAR/subsidence and local hydrostratigraphy",
                "non_regulatory_action": "Require a coastal evidence note before positive recharge interpretation",
                "boundary": "Especially important for Tokyo Bay and Mumbai-Bhayandar-type units",
            },
            {
                "step": 5,
                "protocol_stage": "Geotechnical translation",
                "review_question": "Are liquefiable layers actually present near assets?",
                "minimum_evidence": "CPT/SPT/boreholes, fill/alluvium/reclaimed land and shallow heads",
                "non_regulatory_action": "Commission local liquefaction review if data support concern",
                "boundary": "The global model cannot certify site risk",
            },
            {
                "step": 6,
                "protocol_stage": "Governance response",
                "review_question": "What should the water agency do before implementation?",
                "minimum_evidence": "Monitoring design, project timeline, utility/emergency exposure and responsible agency",
                "non_regulatory_action": "Add well monitoring, sediment review, InSAR/subsidence audit and emergency-planning consultation",
                "boundary": "Not a ban or regulatory threshold",
            },
            {
                "step": 7,
                "protocol_stage": "Decision record",
                "review_question": "What is the defensible output?",
                "minimum_evidence": "Evidence ledger with uncertainty, contradictions and data gaps",
                "non_regulatory_action": "Record routine monitor, targeted data collection, local geotechnical review or multi-hazard audit",
                "boundary": "No claim of damage prediction",
            },
        ]
    )
    protocol.to_csv(DER / "preimplementation_policy_protocol_r37.csv", index=False)

    collaborators = pd.DataFrame(
        [
            {
                "role": "Hydrogeology",
                "needed_contribution": "Local wells, aquifer units, specific yield/storativity, management history and shallow-head relevance",
                "deliverable": "Local water-table and S_y replacement memo",
                "submission_boundary": "Do not imply collaboration until written agreement exists",
            },
            {
                "role": "InSAR/geodesy",
                "needed_contribution": "Subsidence/uplift, aquifer compaction, coastal deformation and product cross-checks",
                "deliverable": "Deformation and leakage-risk memo",
                "submission_boundary": "Use only published/public evidence unless collaborator authorizes unpublished data",
            },
            {
                "role": "Geotechnical liquefaction",
                "needed_contribution": "CPT/SPT/borehole evidence, susceptible strata and local screening/factor-of-safety pathway",
                "deliverable": "Site-review checklist and data-gap table",
                "submission_boundary": "Global screen remains non-regulatory until local investigation",
            },
            {
                "role": "Urban-water governance",
                "needed_contribution": "Project timelines, agency mandates, monitoring design and risk-communication pathways",
                "deliverable": "Pre-implementation workflow and stakeholder map",
                "submission_boundary": "No policy endorsement is implied",
            },
        ]
    )
    collaborators.to_csv(DER / "external_collaborator_role_matrix_r37.csv", index=False)

    COLLAB.mkdir(exist_ok=True)
    packet = """# R37 External Collaborator Scoping Packet

This is a non-submission outreach aid. It does not state or imply that any
external collaborator is participating.

## One-line study boundary

The manuscript tests whether observed regional groundwater-storage trends
change the water-table term in a published liquefaction-screening model for
seismic cities. It does not predict earthquakes, site damage or engineering
factor of safety.

## Why external expertise helps

Nature Water reviewers are likely to ask for local wells, deformation context,
engineering liquefaction evidence and governance relevance. The current paper
has public evidence for direction and screening, but local collaborators could
replace global specific-yield assumptions, add borehole/CPT/SPT interpretation
and clarify project timelines.

## Data request

- Wells: screened interval, aquifer unit, monthly/annual heads, datum, quality
  flag and management timeline.
- Hydrogeology: specific yield/storativity ranges and whether the observed head
  change affects shallow liquefiable layers.
- InSAR: deformation trend, uncertainty, aquifer compaction/uplift attribution
  and coastal leakage/reclamation notes.
- Geotechnical: CPT/SPT/borehole logs, fill/reclaimed/alluvial layer mapping and
  local liquefaction-screening pathway.
- Governance: recharge, pumping restriction or transfer timeline; responsible
  agency; monitoring obligations; emergency/utility interfaces.

## Collaboration guardrails

- No public claim, co-author implication or data reuse before written approval.
- Raw third-party data and active submission files are not redistributed.
- The shared object is an evidence-bound screening protocol, not a regulatory
  hazard product.
"""
    (COLLAB / "r37_external_collaborator_packet.md").write_text(packet, encoding="utf-8")


def write_external_product_status() -> None:
    rows = [
        {
            "product": "GFZ GravIS RL06 Continental Water Storage Anomalies V.0006",
            "doi": "10.5880/GFZ.GRAVIS_06_L3_TWS",
            "url": "https://isdc-data.gfz.de/grace/GravIS/GFZ/Level-3/TWS/GRAVIS-3_GFZOP_0600_TWS_GRID_GFZ_0006.nc",
            "access_status": "downloaded and ingested",
            "local_path": str(GFZ_NC.relative_to(ROOT)),
            "bounded_use": "credential-free third-product TWS and leakage stress test; not city groundwater validation",
        },
        {
            "product": "JPL GRACE/GRACE-FO Mascon CRI Filtered RL06.3Mv04",
            "doi": "10.5067/TEMSC-3JC634",
            "url": "https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",
            "access_status": "verified collection; Earthdata authentication required; not ingested",
            "local_path": "",
            "bounded_use": "best future coastal mascon check; no JPL support claim until authenticated data are processed",
        },
        {
            "product": "COST-G GravIS RL02 Terrestrial Water Storage Anomalies V.0001",
            "doi": "10.5880/COST-G.GRAVIS_02_L3_TWS",
            "url": "https://isdc-data.gfz.de/grace/GravIS/COST-G/Level-3/TWS/GRAVIS-3_COSTG_0200_TWS_GRID_GFZ_0001.nc",
            "access_status": "verified direct-access option; not ingested in R37",
            "local_path": "",
            "bounded_use": "optional fourth-product ensemble stress test",
        },
    ]
    pd.DataFrame(rows).to_csv(DER / "external_product_status_r37.csv", index=False)


def configure_figure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "axes.labelsize": 7,
            "xtick.labelsize": 6,
            "ytick.labelsize": 6,
            "legend.fontsize": 6,
            "figure.dpi": 160,
        }
    )


def make_supplementary_figure_s4(material: pd.DataFrame, enrichment: pd.DataFrame) -> None:
    """Create a vector-first supplementary synthesis figure for R37."""

    configure_figure_style()
    FIG.mkdir(exist_ok=True)

    signal_pos = "#B24A3B"
    signal_neg = "#356C9C"
    neutral = "#4D4D4D"
    pale = "#F4F1EA"
    accent = "#3C8D76"
    warn = "#B77B20"

    fig = plt.figure(figsize=(11.2, 4.25))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.05, 1.05], wspace=0.34)

    # Panel a: product/leakage stress test on the six CSR-material units.
    ax = fig.add_subplot(gs[0, 0])
    plot = material.copy()
    plot["label"] = plot["name"] + " (" + plot["country"] + ")"
    plot = plot.sort_values("dP")
    y = np.arange(len(plot))
    ax.axvspan(-0.01, 0.01, color=pale, zorder=0)
    ax.axvline(0, color="#222222", lw=0.8)
    ax.axvline(-0.01, color="#999999", lw=0.7, ls="--")
    ax.axvline(0.01, color="#999999", lw=0.7, ls="--")
    series = [
        ("CSR primary", "dP", "#111111", "o"),
        ("GSFC guardrail", "gsfc_recent_dP", "#7E7E7E", "s"),
        ("GFZ raw", "gfz_dP_sy010", "#5B8E7D", "^"),
        ("GFZ minus leakage", "gfz_leakage_corrected_dP_sy010", "#D19C45", "D"),
    ]
    for i, (_, col, color, marker) in enumerate(series):
        ax.scatter(
            plot[col],
            y + (i - 1.5) * 0.12,
            s=28,
            color=color,
            marker=marker,
            edgecolor="white",
            linewidth=0.4,
            zorder=4,
        )
    for yi, row in zip(y, plot.itertuples(index=False)):
        lo = min(row.dP, row.gsfc_recent_dP, row.gfz_dP_sy010, row.gfz_leakage_corrected_dP_sy010)
        hi = max(row.dP, row.gsfc_recent_dP, row.gfz_dP_sy010, row.gfz_leakage_corrected_dP_sy010)
        ax.plot([lo, hi], [yi, yi], color="#CFCFCF", lw=0.8, zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["label"])
    ax.set_xlabel("Modelled screening increment, Delta P_liq")
    ax.set_title("a  Third-product and leakage stress test", loc="left", fontweight="bold", pad=6)
    ax.legend(
        [plt.Line2D([0], [0], marker=m, color="none", markerfacecolor=c, markeredgecolor="white", markersize=5)
         for _, _, c, m in series],
        [s[0] for s in series],
        loc="lower right",
        frameon=False,
        handletextpad=0.4,
    )
    # Panel b: engineering-context enrichment.
    ax = fig.add_subplot(gs[0, 1])
    keep = [
        "soft_soil_proxy_vs30_le_360",
        "near_water_proxy_le_5km",
        "susceptibility_proxy_count_ge_2",
        "susceptibility_proxy_count_ge_3",
        "shallow_wtd_proxy_le_10m",
        "high_shaking_proxy_pga_ge_0p2g",
    ]
    labels = {
        "soft_soil_proxy_vs30_le_360": "Low Vs30",
        "near_water_proxy_le_5km": "Near water",
        "susceptibility_proxy_count_ge_2": ">=2 proxies",
        "susceptibility_proxy_count_ge_3": ">=3 proxies",
        "shallow_wtd_proxy_le_10m": "Shallow WTD",
        "high_shaking_proxy_pga_ge_0p2g": "High PGA",
    }
    enrich = enrichment[enrichment["proxy"].isin(keep)].copy()
    enrich["order"] = enrich["proxy"].map({k: i for i, k in enumerate(keep)})
    enrich = enrich.sort_values("order", ascending=False)
    yy = np.arange(len(enrich))
    ax.barh(yy + 0.16, enrich["followup_fraction_with_proxy"] * 100, height=0.28, color=accent, label="A/B follow-up")
    ax.barh(yy - 0.16, enrich["cohort_fraction_with_proxy"] * 100, height=0.28, color="#C7C7C7", label="All cities")
    for yi, row in zip(yy, enrich.itertuples(index=False)):
        if row.fisher_greater_p < 0.05 and row.followup_fraction_with_proxy > row.cohort_fraction_with_proxy:
            ax.text(
                min(row.followup_fraction_with_proxy * 100 + 3, 98),
                yi + 0.16,
                f"p={row.fisher_greater_p:.3g}",
                va="center",
                ha="left",
                fontsize=5.8,
                color=accent,
            )
    ax.set_yticks(yy)
    ax.set_yticklabels([labels[p] for p in enrich["proxy"]])
    ax.set_xlim(0, 105)
    ax.set_xlabel("Share of units with proxy (%)")
    ax.set_title("b  Engineering-context enrichment", loc="left", fontweight="bold", pad=6)
    ax.legend(loc="lower right", frameon=False)
    # Panel c: policy protocol as an evidence-gated swimlane.
    ax = fig.add_subplot(gs[0, 2])
    ax.set_axis_off()
    ax.set_title("c  Pre-implementation review protocol", loc="left", fontweight="bold", pad=6)
    stages = [
        ("1", "Eligibility", "seismic basin + susceptible urban ground", "#ECE6D8"),
        ("2", "Direction", "regional storage sign + local wells", "#E4EEF5"),
        ("3", "Magnitude", "A/B/C tier + local S_y replacement", "#E9F1E6"),
        ("4", "Coastal check", "GFZ/JPL leakage + InSAR note", "#F5E8DE"),
        ("5", "Geotechnical", "CPT/SPT/boreholes; fill/alluvium", "#EEE8F3"),
        ("6", "Governance", "monitoring + emergency/utility review", "#E8ECEF"),
    ]
    y0 = 0.88
    gap = 0.137
    for i, (num, title, subtitle, color) in enumerate(stages):
        yb = y0 - i * gap
        box = FancyBboxPatch(
            (0.02, yb - 0.08),
            0.91,
            0.092,
            boxstyle="round,pad=0.008,rounding_size=0.018",
            facecolor=color,
            edgecolor="#777777",
            linewidth=0.6,
            transform=ax.transAxes,
        )
        ax.add_patch(box)
        ax.text(0.055, yb - 0.034, num, transform=ax.transAxes, ha="center", va="center",
                fontsize=8, fontweight="bold", color="#222222")
        ax.text(0.11, yb - 0.018, title, transform=ax.transAxes, ha="left", va="center",
                fontsize=7, fontweight="bold", color="#222222")
        ax.text(0.11, yb - 0.052, subtitle, transform=ax.transAxes, ha="left", va="center",
                fontsize=5.9, color="#333333")
        if i < len(stages) - 1:
            ax.annotate(
                "",
                xy=(0.475, yb - gap + 0.025),
                xytext=(0.475, yb - 0.091),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color="#666666"),
            )
    ax.text(
        0.02,
        0.03,
        "Output: routine monitor | targeted data collection | local geotechnical review | multi-hazard audit",
        transform=ax.transAxes,
        fontsize=5.9,
        color=warn,
        ha="left",
        va="bottom",
    )
    ax.text(
        0.02,
        -0.035,
        "Boundary: non-regulatory screen; no damage prediction or factor-of-safety estimate.",
        transform=ax.transAxes,
        fontsize=5.9,
        color=neutral,
        ha="left",
        va="bottom",
    )

    fig.suptitle(
        "Evidence-gated upgrade from regional storage signal to local review",
        x=0.02,
        y=1.03,
        ha="left",
        fontsize=9,
        fontweight="bold",
    )
    out = FIG / "FigS4_r37_third_product_engineering_protocol"
    fig.savefig(out.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=600, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    DER.mkdir(exist_ok=True)
    cities = load_city_model_frame()
    consensus, material, gfz_summary = sample_gfz_product(cities)
    enrichment = engineering_enrichment()
    scorecard = region_validation_scorecard(consensus)
    write_policy_and_collaboration_tables()
    write_external_product_status()
    make_supplementary_figure_s4(material, enrichment)

    summary = {
        "gfz_file_present": GFZ_NC.exists(),
        "gfz_file_size_bytes": GFZ_NC.stat().st_size if GFZ_NC.exists() else 0,
        "n_cities": int(len(consensus)),
        "all_city_csr_gfz_sign_match_fraction": float(gfz_summary.loc[0, "csr_gfz_sign_match_fraction"]),
        "all_city_csr_gfz_leakage_corrected_sign_match_fraction": float(
            gfz_summary.loc[0, "csr_gfz_leakage_corrected_sign_match_fraction"]
        ),
        "material_unit_csr_gfz_sign_match_fraction": float(gfz_summary.loc[1, "csr_gfz_sign_match_fraction"]),
        "material_unit_csr_gfz_leakage_corrected_sign_match_fraction": float(
            gfz_summary.loc[1, "csr_gfz_leakage_corrected_sign_match_fraction"]
        ),
        "gfz_material_sy010_count_all": int(gfz_summary.loc[0, "gfz_material_sy010_count"]),
        "gfz_leakage_corrected_material_sy010_count_all": int(
            gfz_summary.loc[0, "gfz_leakage_corrected_material_sy010_count"]
        ),
        "engineering_enriched_proxy_count_p_lt_0p05": int(
            ((enrichment["fisher_greater_p"] < 0.05)
             & (enrichment["followup_fraction_with_proxy"] > enrichment["cohort_fraction_with_proxy"])).sum()
        ),
        "n_region_scorecard_rows": int(len(scorecard)),
        "safe_boundary": (
            "GFZ strengthens independent TWS/leakage stress testing; JPL CRI remains "
            "Earthdata-protected and not ingested; engineering proxies support follow-up "
            "context but not site-specific hazard classes."
        ),
    }
    (DER / "r37_third_product_engineering_policy_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
