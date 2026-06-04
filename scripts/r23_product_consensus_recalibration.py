"""R23 product-consensus recalibration after hostile review.

R21 closed the independent-GSFC sign gap, but it also exposed a stricter
materiality boundary: GSFC preserves hotspot signs but not most CSR material
magnitudes. This script makes that distinction explicit.

Outputs:
- data_derived/product_consensus_hotspots_r23.csv
- data_derived/product_consensus_summary_r23.json
- figures/Fig7_ghsl_gsfc_robustness.{png,svg,pdf}
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
MATERIAL = 0.01
NEAR_MATERIAL = 0.0075


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    multi = pd.read_csv(DER / "multi_product_sign_robustness_r21.csv")
    spatial = pd.read_csv(DER / "hotspot_spatial_robustness_r20.csv")
    attribution = pd.read_csv(DER / "attribution_confidence_matrix_r20.csv")
    return multi, spatial, attribution


def attribution_for_city(name: str) -> tuple[str, str]:
    if name == "Yokohama":
        return "Yokohama / Tokyo Bay", "low-pending"
    if name in {"Mumbai", "Bhayandar"}:
        return "Mumbai-Bhayandar cluster", "low-pending"
    if name == "Delhi":
        return "Delhi", "medium-high"
    if name == "Lahore":
        return "Lahore", "medium-high"
    if name == "Ludhiana":
        return "Ludhiana / Punjab", "medium"
    return "", ""


def classify_row(row: pd.Series) -> tuple[str, str]:
    csr_material = bool(row["csr_material"])
    gsfc_material = bool(row["gsfc_recent_material"])
    sign_supported = bool(row["gsfc_sign_supported"])
    near = bool(row["gsfc_recent_near_material"])
    direction = "increase" if row["csr_dP"] > 0 else "decrease"
    coastal = bool(row.get("coastal_lt50km", False))

    if csr_material and gsfc_material and sign_supported:
        grade = "CSR-material; GSFC-material; sign-supported"
    elif csr_material and sign_supported and near:
        grade = "CSR-material; GSFC-sign-supported; GSFC-near-material"
    elif csr_material and sign_supported:
        grade = "CSR-material; GSFC-sign-supported; GSFC-sub-material"
    elif csr_material:
        grade = "CSR-material; product follow-up required"
    else:
        grade = "not a CSR-material screening unit"

    if direction == "increase" and coastal and not gsfc_material:
        interpretation = (
            "candidate recharge-side screening signal; CSR-material and GSFC-sign-supported, "
            "but not GSFC-material and still requires local groundwater and additional product evidence"
        )
    elif direction == "increase":
        interpretation = "recharge-side screening signal requiring local groundwater attribution"
    elif gsfc_material:
        interpretation = "depletion-side product-material screening unit under CSR and GSFC"
    elif near:
        interpretation = "depletion-side CSR-material screening unit with GSFC near the material threshold"
    else:
        interpretation = "depletion-side CSR-material screening unit with GSFC sign support only"
    return grade, interpretation


def build_consensus_table(multi: pd.DataFrame, spatial: pd.DataFrame) -> pd.DataFrame:
    hs = multi[multi["is_material_hotspot"]].copy()
    coast_cols = ["name", "country", "distance_to_coast_km", "coastal_lt50km", "direction"]
    hs = hs.merge(spatial[coast_cols], on=["name", "country"], how="left")
    hs["csr_dP"] = hs["dP"]
    hs["csr_material"] = hs["csr_dP"].abs() >= MATERIAL
    hs["gsfc_recent_material"] = hs["gsfc_recent_dP"].abs() >= MATERIAL
    hs["gsfc_recent_near_material"] = (hs["gsfc_recent_dP"].abs() >= NEAR_MATERIAL) & ~hs["gsfc_recent_material"]
    hs["gsfc_sign_supported"] = hs["csr_gsfc_recent_sign_match"] & hs["csr_gsfc_theilsen_sign_match"]
    hs["product_material_supported"] = hs["csr_material"] & hs["gsfc_recent_material"] & hs["gsfc_sign_supported"]
    hs["product_sign_only"] = hs["csr_material"] & hs["gsfc_sign_supported"] & ~hs["gsfc_recent_material"]

    regions = []
    confidences = []
    grades = []
    interpretations = []
    for _, row in hs.iterrows():
        region, confidence = attribution_for_city(str(row["name"]))
        grade, interpretation = classify_row(row)
        regions.append(region)
        confidences.append(confidence)
        grades.append(grade)
        interpretations.append(interpretation)
    hs["attribution_region"] = regions
    hs["management_attribution_confidence"] = confidences
    hs["product_consensus_grade"] = grades
    hs["manuscript_interpretation"] = interpretations

    columns = [
        "name",
        "country",
        "ghsl_uc_name",
        "direction",
        "csr_recent_tws_cm_yr",
        "csr_dP",
        "csr_material",
        "gsfc_recent_tws_cm_yr",
        "gsfc_recent_se_cm_yr",
        "gsfc_recent_p",
        "gsfc_recent_theilsen_cm_yr",
        "gsfc_recent_dP",
        "gsfc_recent_material",
        "gsfc_recent_near_material",
        "gsfc_sign_supported",
        "csr_gsfc_recent_sign_match",
        "csr_gsfc_theilsen_sign_match",
        "product_material_supported",
        "product_sign_only",
        "distance_to_coast_km",
        "coastal_lt50km",
        "management_attribution_confidence",
        "product_consensus_grade",
        "manuscript_interpretation",
    ]
    return hs[columns].sort_values("csr_dP", ascending=False)


def build_summary(multi: pd.DataFrame, consensus: pd.DataFrame) -> dict[str, object]:
    positive = consensus["csr_dP"] > 0
    negative = consensus["csr_dP"] < 0
    summary = {
        "n_cities": int(len(multi)),
        "n_csr_material_hotspots": int(consensus["csr_material"].sum()),
        "n_gsfc_sign_supported_hotspots": int(consensus["gsfc_sign_supported"].sum()),
        "n_gsfc_material_hotspots": int(consensus["gsfc_recent_material"].sum()),
        "n_gsfc_near_material_hotspots": int(consensus["gsfc_recent_near_material"].sum()),
        "n_positive_csr_material_hotspots": int(positive.sum()),
        "n_positive_gsfc_material_hotspots": int((positive & consensus["gsfc_recent_material"]).sum()),
        "n_positive_coastal_lt50km": int((positive & consensus["coastal_lt50km"]).sum()),
        "n_negative_csr_material_hotspots": int(negative.sum()),
        "n_negative_gsfc_material_hotspots": int((negative & consensus["gsfc_recent_material"]).sum()),
        "all_city_csr_gsfc_recent_sign_agreement_fraction": float(multi["csr_gsfc_recent_sign_match"].mean()),
        "all_city_csr_gsfc_theilsen_sign_agreement_fraction": float(multi["csr_gsfc_theilsen_sign_match"].mean()),
        "interpretation": (
            "GSFC is used as an independent sign check, not as proof that all CSR-material "
            "screening units are material under an independent product."
        ),
    }
    return summary


def configure_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def make_fig7(multi: pd.DataFrame, consensus: pd.DataFrame, summary: dict[str, object]) -> None:
    configure_matplotlib()
    red = "#c7362f"
    blue = "#2f6fb3"
    ink = "#202020"
    gray = "#c9c9c9"

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(7.2, 9.6),
        dpi=240,
        gridspec_kw={"height_ratios": [1.65, 1.55, 1.1]},
    )
    fig.suptitle("Product-consensus robustness: sign support is not materiality proof", fontsize=12, weight="bold")

    ordered = consensus.sort_values("csr_dP").reset_index(drop=True)
    y = np.arange(len(ordered))
    colors = np.where(ordered["csr_dP"] > 0, red, blue)
    axes[0].barh(y, ordered["csr_dP"], color=colors, alpha=0.82, height=0.62, label="CSR Delta P")
    axes[0].scatter(
        ordered["gsfc_recent_dP"],
        y,
        marker="D",
        s=36,
        color="white",
        edgecolor=ink,
        lw=0.8,
        zorder=5,
        label="GSFC Delta P",
    )
    axes[0].axvline(0, color=ink, lw=0.8)
    axes[0].axvline(MATERIAL, color="#777777", lw=0.7, ls="--")
    axes[0].axvline(-MATERIAL, color="#777777", lw=0.7, ls="--")
    axes[0].set_yticks(y, ordered["name"] + " (" + ordered["ghsl_uc_name"].fillna("unmatched") + ")", fontsize=7)
    axes[0].set_xlabel("Cumulative Delta screening index")
    axes[0].set_title("a CSR materiality vs GSFC magnitude", loc="left", weight="bold")
    axes[0].legend(loc="lower right", fontsize=7)

    all_df = multi.dropna(subset=["dP", "gsfc_recent_dP"]).copy()
    axes[1].scatter(all_df["dP"], all_df["gsfc_recent_dP"], s=10, color=gray, alpha=0.55)
    axes[1].scatter(
        consensus["csr_dP"],
        consensus["gsfc_recent_dP"],
        s=48,
        c=np.where(consensus["csr_dP"] > 0, red, blue),
        edgecolor=ink,
        lw=0.5,
        zorder=5,
    )
    lim = max(abs(all_df["dP"]).max(), abs(all_df["gsfc_recent_dP"]).max(), 0.03)
    lim = min(max(lim * 1.05, 0.03), 0.08)
    axes[1].plot([-lim, lim], [-lim, lim], color="#888888", lw=0.7, ls=":")
    for v in [-MATERIAL, 0, MATERIAL]:
        axes[1].axhline(v, color="#999999", lw=0.6, ls="--" if v else "-")
        axes[1].axvline(v, color="#999999", lw=0.6, ls="--" if v else "-")
    offsets = {
        "Yokohama": (0.0010, 0.0022, "left"),
        "Bhayandar": (0.0010, -0.0015, "left"),
        "Mumbai": (0.0010, -0.0036, "left"),
        "Delhi": (0.0010, -0.0030, "left"),
        "Lahore": (0.0010, 0.0026, "left"),
        "Ludhiana": (-0.0024, -0.0024, "right"),
    }
    for _, row in consensus.iterrows():
        dx, dy, ha = offsets.get(row["name"], (0.0010, 0.0010, "left"))
        axes[1].text(row["csr_dP"] + dx, row["gsfc_recent_dP"] + dy, row["name"], fontsize=6.3, va="center", ha=ha)
    axes[1].set_xlim(-lim, lim)
    axes[1].set_ylim(-lim, lim)
    axes[1].set_xlabel("CSR Delta screening index")
    axes[1].set_ylabel("GSFC Delta screening index")
    axes[1].set_title("b All-city product comparison", loc="left", weight="bold")

    axes[2].axis("off")
    lines = [
        ("CSR-material units", f"{summary['n_csr_material_hotspots']}/6"),
        ("GSFC sign-supported", f"{summary['n_gsfc_sign_supported_hotspots']}/6"),
        ("GSFC-material units", f"{summary['n_gsfc_material_hotspots']}/6"),
        ("GSFC near-material", f"{summary['n_gsfc_near_material_hotspots']}/6"),
        ("Positive coastal units", f"{summary['n_positive_coastal_lt50km']}/3"),
        ("Positive GSFC-material", f"{summary['n_positive_gsfc_material_hotspots']}/3"),
        ("All-city sign agreement", f"{summary['all_city_csr_gsfc_recent_sign_agreement_fraction']:.2f}"),
    ]
    axes[2].text(0.02, 0.98, "c Product-consensus ledger", transform=axes[2].transAxes, fontsize=9.5, weight="bold", va="top")
    y0 = 0.88
    for i, (label, value) in enumerate(lines):
        axes[2].text(0.03, y0 - i * 0.11, label, transform=axes[2].transAxes, fontsize=8.0, color="#555555")
        axes[2].text(0.97, y0 - i * 0.11, value, transform=axes[2].transAxes, fontsize=8.0, ha="right", color=ink)
    axes[2].text(
        0.03,
        0.05,
        "GSFC is an independent sign check here. It does not prove that every\n"
        "CSR-material screening unit is material under an independent product.",
        transform=axes[2].transAxes,
        fontsize=7.2,
        color="#666666",
    )

    for ax in axes[:2]:
        ax.grid(True, color="#e4e4e4", lw=0.5)
        ax.set_axisbelow(True)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for ext in ["png", "svg", "pdf"]:
        fig.savefig(FIG / f"Fig7_ghsl_gsfc_robustness.{ext}", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    multi, spatial, _ = load_inputs()
    consensus = build_consensus_table(multi, spatial)
    summary = build_summary(multi, consensus)
    consensus.to_csv(DER / "product_consensus_hotspots_r23.csv", index=False, encoding="utf-8")
    (DER / "product_consensus_summary_r23.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_fig7(multi, consensus, summary)
    print(json.dumps(summary, indent=2))
    print("Saved R23 product-consensus table and revised Fig7.")


if __name__ == "__main__":
    main()
