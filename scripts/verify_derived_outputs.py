"""Verify headline numbers from included derived outputs only."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
MATERIAL = 0.01


def main() -> None:
    summary = json.loads((DER / "core_summary_v2.json").read_text(encoding="utf-8"))
    cities = pd.read_csv(DER / "city_results_v2.csv")
    hotspots = pd.read_csv(DER / "hotspot_table.csv")
    grid = pd.read_csv(DER / "sensitivity_grid_v2.csv")
    envelope = pd.read_csv(DER / "hotspot_sensitivity_envelope_v2.csv")
    policy = pd.read_csv(DER / "policy_priority_table_v2.csv")

    material = cities[cities["fdr_sig"] & (cities["dP"].abs() >= MATERIAL)]
    assert summary["n"] == len(cities) == 444
    assert summary["n_fdr_sig"] == int(cities["fdr_sig"].sum()) == 330
    assert len(material[material["dP"] > 0]) == summary["n_material_inc"] == 3
    assert len(material[material["dP"] < 0]) == summary["n_material_dec"] == 3
    assert len(hotspots) == 6
    assert len(grid) == 150
    assert int(grid["hotspot_sign_reversals"].sum()) == 0
    assert len(envelope) == 6
    assert bool(envelope["sign_consistent_across_grid"].all())
    assert len(policy) == 444

    beijing = cities[cities["name"] == "Beijing"].iloc[0]
    assert beijing["dP"] > 0
    assert beijing["dP_lo"] > 0

    print("Derived-output verification passed.")
    print(f"Cities: {len(cities)}")
    print(f"FDR-significant: {int(cities['fdr_sig'].sum())}")
    print(f"Material increases/decreases: {summary['n_material_inc']}/{summary['n_material_dec']}")
    print(f"Beijing dP: {beijing['dP']:+.6f}; TWS trend: {beijing['tws_cm_yr']:+.2f} cm yr-1")
    print(f"Sensitivity combinations: {len(grid)}; hotspot sign reversals: {int(grid['hotspot_sign_reversals'].sum())}")


if __name__ == "__main__":
    main()
