"""Compute zero-aware finite-Monte-Carlo FDR sensitivity for R27.

The original city table contains exact-zero Delta P rows whose intervals are
[0, 0]. Those rows should not contribute as directional discoveries. This
diagnostic keeps the reported hotspot screen traceable while applying a
finite-draw p-value correction for the 4,000 Monte Carlo samples.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
B = 4000
ALPHA = 0.10


def fdr_bh(p: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    n = len(p)
    thresh = alpha * np.arange(1, n + 1) / n
    hits = np.where(ranked <= thresh)[0]
    out = np.zeros(n, dtype=bool)
    if len(hits):
        out[order[: hits[-1] + 1]] = True
    return out


def fdr_by(p: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    n = len(p)
    c_m = np.sum(1 / np.arange(1, n + 1))
    order = np.argsort(p)
    ranked = p[order]
    thresh = alpha * np.arange(1, n + 1) / (n * c_m)
    hits = np.where(ranked <= thresh)[0]
    out = np.zeros(n, dtype=bool)
    if len(hits):
        out[order[: hits[-1] + 1]] = True
    return out


def main() -> None:
    df = pd.read_csv(DER / "city_results_v2.csv")
    exact_zero = (df["dP"] == 0.0) & (df["dP_lo"] == 0.0) & (df["dP_hi"] == 0.0)
    p = df["p_two"].astype(float).to_numpy(copy=True)
    p = np.where(exact_zero, 1.0, p)
    p = np.where(p <= 0, 1 / (B + 1), p)
    df["p_two_zero_aware"] = p
    df["zero_exact_dP"] = exact_zero
    df["fdr_bh_zero_aware"] = fdr_bh(p)
    df["fdr_by_zero_aware"] = fdr_by(p)
    df["material"] = df["dP"].abs() >= 0.01
    df["material_bh_zero_aware"] = df["material"] & df["fdr_bh_zero_aware"]
    df["material_by_zero_aware"] = df["material"] & df["fdr_by_zero_aware"]

    cols = [
        "name",
        "country",
        "dP",
        "dP_lo",
        "dP_hi",
        "p_two",
        "p_two_zero_aware",
        "zero_exact_dP",
        "fdr_sig",
        "fdr_bh_zero_aware",
        "fdr_by_zero_aware",
        "material_bh_zero_aware",
        "material_by_zero_aware",
    ]
    df[cols].to_csv(DER / "zero_aware_fdr_city_results_r27.csv", index=False)

    summary = {
        "n_cities": int(len(df)),
        "zero_exact_dP_rows": int(exact_zero.sum()),
        "original_bh_significant": int(df["fdr_sig"].sum()),
        "zero_aware_bh_significant": int(df["fdr_bh_zero_aware"].sum()),
        "zero_aware_by_significant": int(df["fdr_by_zero_aware"].sum()),
        "zero_aware_material_bh": int(df["material_bh_zero_aware"].sum()),
        "zero_aware_material_by": int(df["material_by_zero_aware"].sum()),
        "material_bh_names": df.loc[df["material_bh_zero_aware"], "name"].tolist(),
        "material_by_names": df.loc[df["material_by_zero_aware"], "name"].tolist(),
        "finite_monte_carlo_draws": B,
        "add_one_minimum_p": 1 / (B + 1),
    }
    (DER / "zero_aware_fdr_summary_r27.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
