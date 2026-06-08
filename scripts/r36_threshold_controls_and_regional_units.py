"""R36 reviewer-facing threshold, control and regional-unit diagnostics.

This script does not change the liquefaction model or introduce new claims.
It converts existing derived outputs into tables that answer likely Nature
Water reviewer questions:

1. what |Delta P_liq| >= 0.01 means within the cohort distribution;
2. why a non-rejected geographic null can coexist with many sign-detectable
   city exposure units;
3. why regional groups, not point cities, are the storage-driver inference
   scale;
4. whether low-sensitivity strata behave like negative controls; and
5. how specific yield controls materiality without assigning unsupported
   local aquifer priors.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
MATERIAL = 0.01
TARGETED = 0.005


def pct(x: float) -> float:
    return float(100.0 * x)


def quantile_records(values: pd.Series, prefix: str) -> list[dict[str, float | str]]:
    qs = [0.5, 0.75, 0.9, 0.95, 0.975, 0.99, 1.0]
    return [
        {"metric": f"{prefix}_q{int(q * 1000):03d}", "value": float(values.quantile(q))}
        for q in qs
    ]


def reviewer_safe_alias(
    src_name: str,
    dst_name: str,
    column_terms: dict[str, str] | None = None,
    value_terms: dict[str, str] | None = None,
) -> None:
    """Create submission-facing CSV aliases with conservative labels.

    Legacy file names remain in the reproducibility tree for traceability. These
    aliases keep the same numerical content while avoiding words that imply
    regulatory thresholds or city-scale risk ranking.
    """

    src = DER / src_name
    if not src.exists():
        return
    if not column_terms and not value_terms:
        shutil.copyfile(src, DER / dst_name)
        return

    df = pd.read_csv(src)
    if column_terms:
        renamed = {}
        for col in df.columns:
            new = col
            for old, repl in column_terms.items():
                new = new.replace(old, repl)
            renamed[col] = new
        df = df.rename(columns=renamed)
    if value_terms:
        obj_cols = [
            col for col in df.columns
            if str(df[col].dtype) == "object" or str(df[col].dtype).startswith("str")
        ]
        for col in obj_cols:
            values = df[col].astype(str)
            for old, repl in value_terms.items():
                values = values.str.replace(old, repl, regex=False)
            df[col] = values
    df.to_csv(DER / dst_name, index=False, encoding="utf-8")


def sy_class(threshold: float | None) -> str:
    if threshold is None or not np.isfinite(threshold):
        return "never material in tested S_y range"
    if threshold >= 0.20:
        return "material under most tested S_y values"
    if threshold >= 0.15:
        return "material under low-to-moderate S_y values"
    if threshold >= 0.10:
        return "material at baseline S_y=0.10 but not at higher S_y"
    if threshold >= 0.05:
        return "material only under very low S_y"
    return "below tested S_y materiality range"


def main() -> None:
    cities = pd.read_csv(DER / "city_results_v2.csv")
    zero = pd.read_csv(DER / "zero_aware_fdr_city_results_r27.csv")
    r31 = pd.read_csv(DER / "static_observed_triage_tier_change_r31.csv")
    water = pd.read_csv(DER / "water_table_trigger_r20.csv")
    policy = pd.read_csv(DER / "policy_priority_table_v2.csv")
    sy = pd.read_csv(DER / "specific_yield_thresholds_r28.csv")
    mat = pd.read_csv(DER / "materiality_uncertainty_table_r33.csv")

    join_keys = ["name", "country", "lat", "lon"]
    merged = (
        r31.merge(
            water[
                [
                    "name",
                    "country",
                    "lat",
                    "lon",
                    "metro_cluster_50km",
                    "grace_scale_cluster_300km",
                    "water_table_rise_trigger_m_for_plus0p01",
                    "recent_cumulative_water_table_rise_m_sy010",
                    "distance_to_coast_km",
                ]
            ],
            on=join_keys,
            how="left",
            validate="one_to_one",
        )
        .merge(
            policy[
                [
                    "name",
                    "country",
                    "lat",
                    "lon",
                    "vs30",
                    "wtd",
                    "dw_km",
                    "pga_475_g",
                ]
            ],
            on=join_keys,
            how="left",
            validate="one_to_one",
        )
    )

    abs_dp = cities["dP"].abs()
    material_raw = abs_dp >= MATERIAL
    targeted_raw = abs_dp >= TARGETED
    ab = r31["ab_followup_bh"].astype(bool)
    material_bh = r31["material_bh_zero_aware"].astype(bool)
    detectable_bh = r31["fdr_bh_zero_aware"].astype(bool)

    threshold_rows: list[dict[str, float | str | int]] = [
        {"metric": "n_cities", "value": int(len(cities))},
        {"metric": "material_threshold_abs_delta_p", "value": MATERIAL},
        {"metric": "targeted_threshold_abs_delta_p", "value": TARGETED},
        {"metric": "raw_abs_delta_p_ge_0p01_count", "value": int(material_raw.sum())},
        {"metric": "raw_abs_delta_p_ge_0p01_fraction", "value": float(material_raw.mean())},
        {"metric": "zero_aware_fdr_and_abs_delta_p_ge_0p01_count", "value": int(material_bh.sum())},
        {"metric": "zero_aware_fdr_and_abs_delta_p_ge_0p01_fraction", "value": float(material_bh.mean())},
        {"metric": "raw_abs_delta_p_ge_0p005_count", "value": int(targeted_raw.sum())},
        {"metric": "static_counterfactual_ab_followup_count", "value": int(ab.sum())},
        {"metric": "static_counterfactual_ab_followup_fraction", "value": float(ab.mean())},
        {"metric": "abs_delta_p_0p01_percentile_rank_all_cities", "value": float((abs_dp <= MATERIAL).mean())},
        {
            "metric": "abs_delta_p_0p01_percentile_rank_fdr_detectable_cities",
            "value": float((r31.loc[detectable_bh, "dP"].abs() <= MATERIAL).mean()),
        },
        {
            "metric": "interpretation",
            "value": (
                "|Delta P_liq| >= 0.01 is a top-tail follow-up reporting increment "
                "inside this model, not an engineering safety or damage threshold."
            ),
        },
    ]
    threshold_rows.extend(quantile_records(abs_dp, "abs_delta_p_all_cities"))
    threshold_rows.extend(
        quantile_records(water["water_table_rise_trigger_m_for_plus0p01"].dropna(), "water_table_rise_for_plus0p01_m")
    )
    threshold_table = pd.DataFrame(threshold_rows)
    threshold_table.to_csv(DER / "threshold_interpretation_r36.csv", index=False)

    direction_sets = []
    for label, mask in [
        ("all cities", pd.Series(True, index=r31.index)),
        ("zero-aware FDR-detectable cities", detectable_bh),
        ("A/B follow-up point-city units", ab),
        ("A material point-city units", material_bh),
    ]:
        subset = r31.loc[mask]
        direction_sets.append(
            {
                "set": label,
                "n": int(len(subset)),
                "n_positive": int((subset["dP"] > 0).sum()),
                "n_negative": int((subset["dP"] < 0).sum()),
                "mean_delta_p": float(subset["dP"].mean()) if len(subset) else np.nan,
                "mean_abs_delta_p": float(subset["dP"].abs().mean()) if len(subset) else np.nan,
                "sum_positive_delta_p": float(subset.loc[subset["dP"] > 0, "dP"].sum()),
                "sum_negative_delta_p": float(subset.loc[subset["dP"] < 0, "dP"].sum()),
                "cancellation_ratio_abs_sum_neg_over_pos": (
                    float(abs(subset.loc[subset["dP"] < 0, "dP"].sum()) / subset.loc[subset["dP"] > 0, "dP"].sum())
                    if subset.loc[subset["dP"] > 0, "dP"].sum() != 0
                    else np.nan
                ),
            }
        )
    null_table = pd.DataFrame(direction_sets)
    null_table.to_csv(DER / "null_detectability_reconciliation_r36.csv", index=False)

    ab_units = merged[merged["ab_followup_bh"].astype(bool)].copy()
    regional_rows = []
    for gid, g in ab_units.groupby("grace_scale_cluster_300km"):
        regional_rows.append(
            {
                "grace_scale_cluster_300km": int(gid),
                "n_point_city_units": int(len(g)),
                "n_metro_clusters_50km": int(g["metro_cluster_50km"].nunique()),
                "n_countries": int(g["country"].nunique()),
                "n_increase_side": int((g["dP"] > 0).sum()),
                "n_depletion_side": int((g["dP"] < 0).sum()),
                "n_material_units": int(g["material_bh_zero_aware"].sum()),
                "population_million_sum": float(g["population_million"].sum()),
                "mean_abs_delta_p": float(g["dP"].abs().mean()),
                "max_abs_delta_p": float(g["dP"].abs().max()),
                "representative_names": "; ".join(g.sort_values("population", ascending=False)["name"].head(8).tolist()),
                "interpretation": "regional storage-setting follow-up group; point cities are exposure locators",
            }
        )
    regional_table = pd.DataFrame(regional_rows).sort_values(
        ["n_material_units", "n_point_city_units", "max_abs_delta_p"],
        ascending=False,
    )
    regional_table.to_csv(DER / "regional_followup_groups_r36.csv", index=False)

    control_specs = [
        ("low shaking PGA475 < 0.10 g", merged["pga_475_g"] < 0.10),
        ("stiff-site proxy Vs30 > 500 m s-1", merged["vs30"] > 500),
        ("deep baseline water table > 30 m", merged["wtd"] > 30),
        ("low baseline model index P0 < 0.05", merged["P0"] < 0.05),
        ("low susceptibility proxy count <= 1", merged["susceptibility_proxy_count"] <= 1),
        ("far from mapped water distance > 20 km", merged["dw_km"] > 20),
    ]
    control_rows = []
    for label, mask in control_specs:
        g = merged.loc[mask].copy()
        control_rows.append(
            {
                "control_stratum": label,
                "n": int(len(g)),
                "mean_abs_delta_p": float(g["dP"].abs().mean()) if len(g) else np.nan,
                "max_abs_delta_p": float(g["dP"].abs().max()) if len(g) else np.nan,
                "n_zero_aware_fdr_detectable": int(g["fdr_bh_zero_aware"].sum()) if len(g) else 0,
                "n_ab_followup": int(g["ab_followup_bh"].sum()) if len(g) else 0,
                "n_material": int(g["material_bh_zero_aware"].sum()) if len(g) else 0,
                "ab_followup_fraction": float(g["ab_followup_bh"].mean()) if len(g) else np.nan,
                "largest_names": "; ".join(g.sort_values("dP", key=lambda s: s.abs(), ascending=False)["name"].head(5).tolist())
                if len(g)
                else "",
                "interpretation": "negative-control style stratum; strong A/B updates should be rare or absent",
            }
        )
    control_table = pd.DataFrame(control_rows)
    control_table.to_csv(DER / "negative_control_strata_r36.csv", index=False)

    sy_ledger = sy.merge(
        mat[["name", "country", "mc_pr_abs_delta_p_ge_0p01", "gsfc_recent_material", "gsfc_statistical_sign_support_p05"]],
        on=["name", "country"],
        how="left",
    )
    sy_ledger["sy_dependency_class"] = sy_ledger["sy_material_threshold"].map(sy_class)
    sy_ledger["material_at_sy_0p05"] = sy_ledger["dP_sy005"].abs() >= MATERIAL
    sy_ledger["material_at_sy_0p10"] = sy_ledger["dP_sy010"].abs() >= MATERIAL
    sy_ledger["material_at_sy_0p25"] = sy_ledger["dP_sy025"].abs() >= MATERIAL
    sy_ledger[
        [
            "name",
            "country",
            "role",
            "direction",
            "regional_setting",
            "baseline_dP_sy010",
            "sy_material_threshold",
            "sy_dependency_class",
            "material_at_sy_0p05",
            "material_at_sy_0p10",
            "material_at_sy_0p25",
            "mc_pr_abs_delta_p_ge_0p01",
            "gsfc_statistical_sign_support_p05",
            "gsfc_recent_material",
            "interpretation",
        ]
    ].to_csv(DER / "specific_yield_scenario_ledger_r36.csv", index=False)

    summary = {
        "n_cities": int(len(cities)),
        "mean_delta_p": float(cities["dP"].mean()),
        "mean_abs_delta_p": float(abs_dp.mean()),
        "raw_abs_delta_p_ge_0p01_count": int(material_raw.sum()),
        "zero_aware_material_bh_count": int(material_bh.sum()),
        "ab_followup_count": int(ab.sum()),
        "ab_followup_300km_groups": int(regional_table["grace_scale_cluster_300km"].nunique()),
        "largest_ab_group_n_point_city_units": int(regional_table["n_point_city_units"].max()),
        "threshold_0p01_percentile_rank_all_cities": float((abs_dp <= MATERIAL).mean()),
        "control_strata_max_material_count": int(control_table["n_material"].max()),
        "sy_material_threshold_range_for_six_material_units": [
            float(mat["sy_material_threshold"].min()),
            float(mat["sy_material_threshold"].max()),
        ],
    }
    (DER / "threshold_controls_summary_r36.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Reviewer-safe aliases for legacy derived filenames. The content is
    # unchanged except label-only text/column replacement in files whose old
    # exploratory names used "trigger", "priority" or "hotspot".
    conservative_values = {
        "A material hotspot": "A material follow-up unit",
        "depletion-side hotspot": "depletion-side follow-up screen",
        "coastal-sensitive positive hotspot": "coastal-sensitive positive CSR screening unit",
        "coastal hotspot": "coastal CSR screening unit",
        "hotspot": "follow-up unit",
        "trigger": "follow-up flag",
    }
    alias_specs = {
        "hotspot_sensitivity_envelope_v2.csv": ("followup_unit_sensitivity_envelope_v2.csv", None, conservative_values),
        "hotspot_sensitivity_city_grid_v2.csv": ("followup_unit_sensitivity_city_grid_v2.csv", None, conservative_values),
        "hotspot_spatial_robustness_r20.csv": ("material_unit_spatial_robustness_r20.csv", None, conservative_values),
        "hotspot_driver_sign_robustness_r20.csv": ("material_unit_driver_sign_robustness_r20.csv", None, conservative_values),
        "hotspot_ghsl_polygon_robustness_r21.csv": ("material_unit_ghsl_polygon_robustness_r21.csv", None, conservative_values),
        "product_consensus_hotspots_r23.csv": ("product_consensus_material_units_r23.csv", None, conservative_values),
        "policy_priority_table_v2.csv": ("policy_followup_table_v2.csv", None, conservative_values),
        "policy_exposure_summary_v2.csv": ("policy_followup_exposure_summary_v2.csv", None, conservative_values),
        "water_table_trigger_r20.csv": (
            "water_table_followup_flag_r20.csv",
            {
                "trigger": "followup_flag",
                "is_material_hotspot": "is_material_screening_unit",
            },
            conservative_values,
        ),
        "attribution_confidence_matrix_r20.csv": ("attribution_evidence_boundary_matrix_r20.csv", None, conservative_values),
        "attribution_confidence_matrix_r24.csv": ("attribution_evidence_boundary_matrix_r24.csv", None, conservative_values),
        "attribution_confidence_matrix_r25.csv": ("attribution_evidence_boundary_matrix_r25.csv", None, conservative_values),
    }
    for src_name, (dst_name, column_terms, value_terms) in alias_specs.items():
        reviewer_safe_alias(src_name, dst_name, column_terms, value_terms)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
