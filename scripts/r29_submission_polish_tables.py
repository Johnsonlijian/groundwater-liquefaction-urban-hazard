"""R29 submission-polish tables for Nature Portfolio-style evidence ledgers.

The manuscript should not carry a wide, page-breaking table. This script
creates two compact derived tables:

- confidence_ledger_main_r29.csv: the six-row, six-column main-text ledger.
- confidence_ledger_detail_r29.csv: the detailed point-unit evidence table for SI.

No new science is introduced here; the script repackages existing R23/R25/R28
evidence boundaries into submission-friendly tables.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"


def fmt_bool(value: bool) -> str:
    return "yes" if bool(value) else "no"


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    city = pd.read_csv(DER / "city_results_v2.csv")
    gw = pd.read_csv(DER / "city_gws.csv")
    hotspot = pd.read_csv(DER / "hotspot_table.csv")
    consensus = pd.read_csv(DER / "product_consensus_hotspots_r23.csv")
    sy = pd.read_csv(DER / "specific_yield_thresholds_r28.csv")

    main_rows = [
        {
            "Region": "North China Plain / Beijing",
            "Direction": "increase / recovery",
            "CSR material?": "no; sub-material in global screen",
            "GSFC material?": "not used as material claim",
            "Local sign": "supports increase",
            "Manuscript use": "mechanism anchor; not one of the six material CSR exposure units",
        },
        {
            "Region": "Tokyo Bay / Yokohama",
            "Direction": "increase",
            "CSR material?": "yes",
            "GSFC material?": "no",
            "Local sign": "supports increase",
            "Manuscript use": "locally sign-supported positive screen; not product-material proof",
        },
        {
            "Region": "Mumbai-Bhayandar / Mumbai",
            "Direction": "increase in CSR screen",
            "CSR material?": "yes",
            "GSFC material?": "no",
            "Local sign": "contradicts positive recovery",
            "Manuscript use": "candidate-only coastal CSR signal; not positive recharge validation",
        },
        {
            "Region": "Delhi / New Delhi",
            "Direction": "decrease / depletion",
            "CSR material?": "yes",
            "GSFC material?": "yes",
            "Local sign": "supports depletion",
            "Manuscript use": "strongest product-material depletion screen",
        },
        {
            "Region": "Lahore",
            "Direction": "decrease / depletion",
            "CSR material?": "yes",
            "GSFC material?": "near-material, not material",
            "Local sign": "supports depletion",
            "Manuscript use": "depletion-side screen; near product-material under GSFC",
        },
        {
            "Region": "Ludhiana / Punjab",
            "Direction": "decrease / depletion",
            "CSR material?": "yes",
            "GSFC material?": "near-material, not material",
            "Local sign": "supports depletion regionally",
            "Manuscript use": "depletion-side screen; regional context, not a safety-benefit claim",
        },
    ]

    detail = []
    for _, r in hotspot.sort_values("dP", ascending=False).iterrows():
        c = consensus[(consensus["name"] == r["name"]) & (consensus["country"] == r["country"])].iloc[0]
        sy_row = sy[(sy["name"] == r["name"]) & (sy["country"] == r["country"])].iloc[0]
        region = {
            "Yokohama": "Tokyo Bay/Yokohama",
            "Bhayandar": "Mumbai-Bhayandar",
            "Mumbai": "Mumbai-Bhayandar",
            "Delhi": "Delhi/Punjab",
            "Lahore": "Lahore/Punjab",
            "Ludhiana": "Ludhiana/Punjab",
        }[r["name"]]
        direction = "increase" if r["dP"] > 0 else "decrease"
        local = {
            "Yokohama": "supported sign",
            "Bhayandar": "contradictory",
            "Mumbai": "contradictory",
            "Delhi": "supported depletion",
            "Lahore": "supported depletion",
            "Ludhiana": "regional depletion context",
        }[r["name"]]
        use = {
            "Yokohama": "positive screen; sign-bounded",
            "Bhayandar": "candidate boundary only",
            "Mumbai": "candidate boundary only",
            "Delhi": "strongest product-material depletion screen",
            "Lahore": "depletion-side screen; near GSFC-material",
            "Ludhiana": "depletion-side screen; near GSFC-material",
        }[r["name"]]
        detail.append(
            {
                "exposure_unit": f"{r['name']}, {r['country']}",
                "region": region,
                "population_million": r["population"] / 1e6,
                "csr_tws_trend_cm_yr": r["tws_cm_yr"],
                "csr_delta_p_liq": r["dP"],
                "csr_delta_p_liq_90pct_low": r["dP_lo"],
                "csr_delta_p_liq_90pct_high": r["dP_hi"],
                "gsfc_recent_delta_p_liq": c["gsfc_recent_dP"],
                "gsfc_material": bool(c["gsfc_recent_material"]),
                "gsfc_near_material": bool(c["gsfc_recent_near_material"]),
                "local_confidence": {
                    "Yokohama": "medium-high sign / low-management",
                    "Bhayandar": "low-contradictory",
                    "Mumbai": "low-contradictory",
                    "Delhi": "medium-high",
                    "Lahore": "medium-high",
                    "Ludhiana": "medium",
                }[r["name"]],
                "sy_material_threshold": sy_row["sy_material_threshold"],
                "manuscript_use": use,
            }
        )

    beijing_idx = int(city.index[city["name"].eq("Beijing")][0])
    beijing = city.iloc[beijing_idx]
    beijing_gw = gw.iloc[beijing_idx]
    beijing_sy = sy[sy["name"].eq("Beijing")].iloc[0]
    detail.append(
        {
            "exposure_unit": "Beijing, CN",
            "region": "North China Plain / Beijing",
            "population_million": beijing["population"] / 1e6,
            "csr_tws_trend_cm_yr": beijing_gw["recent_trend_cm_yr"],
            "csr_delta_p_liq": beijing["dP"],
            "csr_delta_p_liq_90pct_low": beijing["dP_lo"],
            "csr_delta_p_liq_90pct_high": beijing["dP_hi"],
            "gsfc_recent_delta_p_liq": pd.NA,
            "gsfc_material": False,
            "gsfc_near_material": False,
            "local_confidence": "high mechanism support",
            "sy_material_threshold": beijing_sy["sy_material_threshold"],
            "manuscript_use": "mechanism anchor; sub-material in global screen",
        }
    )

    main = pd.DataFrame(main_rows)
    detailed = pd.DataFrame(detail)
    main.to_csv(DER / "confidence_ledger_main_r29.csv", index=False, encoding="utf-8")
    detailed.to_csv(DER / "confidence_ledger_detail_r29.csv", index=False, encoding="utf-8")
    return main, detailed


def main() -> None:
    main_table, detail_table = build_tables()
    print(main_table.to_string(index=False))
    print(f"Saved {len(main_table)} main-ledger rows and {len(detail_table)} detailed rows.")


if __name__ == "__main__":
    main()
