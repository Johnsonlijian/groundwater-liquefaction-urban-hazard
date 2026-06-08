"""R39 Article-route evidence products and named dataset release.

This round adds four Article-facing products without weakening the existing
Nature Water Analysis package:

1. a fresh JPL CRI access/run status that records whether Earthdata credentials
   or a local authenticated NetCDF are available;
2. aquifer-context S_y review classes and phase calculations;
3. evidence-tier cards for the regional claim classes;
4. a local named release package for the derived dataset.

The script never treats JPL CRI as ingested unless an authenticated NetCDF is
present locally. It also treats aquifer classes as review priors, not as
site-calibrated hydrogeology.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
RAW = ROOT / "data_raw"
REL = ROOT / "releases" / "Dynamic_Groundwater_Liquefaction_Screening_Dataset_v1_0"
sys.path.insert(0, str(ROOT / "scripts"))

from zhu2017 import p_liquefaction


MATERIAL = 0.01
TARGETED = 0.005
NYEARS = 10.0
JPL_SHORT = "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4"
JPL_COLLECTION = "C3195527175-POCLOUD"
JPL_GRANULE = "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI"
JPL_DATA_URL = (
    "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/"
    "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4/"
    "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc"
)
JPL_MD5_URL = (
    "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-public/"
    "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4/"
    "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc.md5"
)
JPL_CANDIDATES = [
    RAW / "grace" / "jpl" / "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc",
    RAW / "grace" / "jpl" / "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4.nc",
]


AQUIFER_PRIORS = {
    "semi-confined basin-fill recovery": {
        "sy_low": 0.05,
        "sy_mid": 0.10,
        "sy_high": 0.15,
        "basis": "managed basin-fill/recovery setting; use low-to-moderate unconfined-equivalent S_y review range",
    },
    "coastal mixed/delta-reclaimed review": {
        "sy_low": 0.06,
        "sy_mid": 0.12,
        "sy_high": 0.18,
        "basis": "coastal mixed aquifer/reclamation/leakage review; not a local shallow-head calibration",
    },
    "alluvial/basin-fill depletion": {
        "sy_low": 0.08,
        "sy_mid": 0.14,
        "sy_high": 0.22,
        "basis": "alluvial or basin-fill depletion setting; moderate-to-high review range",
    },
    "alluvial-delta floodplain proxy": {
        "sy_low": 0.08,
        "sy_mid": 0.16,
        "sy_high": 0.25,
        "basis": "low Vs30 and near-water proxy for unconsolidated alluvial/delta/floodplain context",
    },
    "mixed urban aquifer context": {
        "sy_low": 0.05,
        "sy_mid": 0.12,
        "sy_high": 0.20,
        "basis": "default review range when no stronger context proxy is available",
    },
    "stiff/deep low-sensitivity control": {
        "sy_low": 0.03,
        "sy_mid": 0.06,
        "sy_high": 0.10,
        "basis": "control class for stiff, deep-water or far-from-water settings; not used to expand claims",
    },
}


@dataclass
class JplStatus:
    checked_at_utc: str
    short_name: str
    collection_id: str
    granule: str
    data_url: str
    md5_url: str
    md5_text: str
    credential_files_detected: int
    credential_envs_detected: int
    local_netcdf_detected: str
    local_netcdf_md5: str
    anonymous_data_status: str
    anonymous_s3_status: str
    run_status: str
    article_claim_use: str
    next_action: str


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def md5_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def detect_credentials() -> tuple[int, int]:
    home = Path.home()
    files = [home / ".netrc", home / "_netrc", home / ".urs_cookies", home / ".dodsrc"]
    envs = [
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
        "EARTHDATA_TOKEN",
        "NASA_EARTHDATA_USERNAME",
        "NASA_EARTHDATA_PASSWORD",
    ]
    return sum(p.exists() for p in files), sum(bool(os.environ.get(e)) for e in envs)


def check_jpl_cri() -> JplStatus:
    cred_files, cred_envs = detect_credentials()
    local = next((p for p in JPL_CANDIDATES if p.exists() and p.stat().st_size > 10_000_000), None)
    md5_text = ""
    data_status = ""
    s3_status = ""
    try:
        r = requests.get(JPL_MD5_URL, timeout=45)
        md5_text = r.text.strip() if r.ok else f"http_{r.status_code}"
    except Exception as exc:
        md5_text = f"md5_error={type(exc).__name__}"
    try:
        r = requests.get(JPL_DATA_URL, timeout=45, allow_redirects=False)
        data_status = f"http_{r.status_code}; location={r.headers.get('location', '')[:160]}"
    except Exception as exc:
        data_status = f"data_head_error={type(exc).__name__}"
    try:
        r = requests.get("https://archive.podaac.earthdata.nasa.gov/s3credentials", timeout=45, allow_redirects=False)
        s3_status = f"http_{r.status_code}; location={r.headers.get('location', '')[:160]}"
    except Exception as exc:
        s3_status = f"s3cred_error={type(exc).__name__}"

    if local is not None:
        run_status = "local_authenticated_netcdf_available"
        claim = "JPL CRI can be sampled by rerunning the local sampler; include only after trend tables are generated."
        action = "Run the sampler against the local NetCDF and rebuild the product matrix."
        local_rel = str(local.relative_to(ROOT))
        local_md5 = md5_file(local)
    elif cred_files or cred_envs:
        run_status = "credentials_detected_but_no_local_netcdf"
        claim = "Do not claim JPL robustness until authenticated download and sampling complete."
        action = (
            "Use podaac-data-downloader or earthaccess to download "
            "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc into data_raw/grace/jpl/."
        )
        local_rel = ""
        local_md5 = ""
    else:
        run_status = "earthdata_authentication_required_not_ingested"
        claim = "No JPL-based robustness claim; report as an access boundary."
        action = "Provide Earthdata credentials or the authenticated NetCDF before any JPL CRI result is used."
        local_rel = ""
        local_md5 = ""

    status = JplStatus(
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        short_name=JPL_SHORT,
        collection_id=JPL_COLLECTION,
        granule=JPL_GRANULE,
        data_url=JPL_DATA_URL,
        md5_url=JPL_MD5_URL,
        md5_text=md5_text,
        credential_files_detected=cred_files,
        credential_envs_detected=cred_envs,
        local_netcdf_detected=local_rel,
        local_netcdf_md5=local_md5,
        anonymous_data_status=data_status,
        anonymous_s3_status=s3_status,
        run_status=run_status,
        article_claim_use=claim,
        next_action=action,
    )
    pd.DataFrame([asdict(status)]).to_csv(DER / "jpl_cri_article_status_r39.csv", index=False)
    (DER / "jpl_cri_article_status_r39.json").write_text(json.dumps(asdict(status), indent=2), encoding="utf-8")
    return status


def load_frame() -> pd.DataFrame:
    results = pd.read_csv(DER / "city_results_v2.csv")
    inputs = pd.read_csv(DER / "city_inputs.csv")
    cols = ["name", "country", "lat", "lon", "pga_475_g", "vs30", "precip", "dw_km"]
    return results.merge(inputs[cols], on=["name", "country", "lat", "lon"], validate="one_to_one")


def classify_aquifer(row: pd.Series) -> str:
    name = str(row["name"])
    country = str(row["country"])
    if name in {"Beijing", "Tianjin"}:
        return "semi-confined basin-fill recovery"
    if name in {"Yokohama", "Tokyo", "Mumbai", "Bhayandar"}:
        return "coastal mixed/delta-reclaimed review"
    if name in {"Delhi", "New Delhi", "Lahore", "Ludhiana"} or country in {"PK"}:
        return "alluvial/basin-fill depletion"
    if float(row["vs30"]) <= 360 and float(row["dw_km"]) <= 5:
        return "alluvial-delta floodplain proxy"
    if float(row["vs30"]) > 500 or float(row["wtd"]) > 30 or float(row["dw_km"]) > 20:
        return "stiff/deep low-sensitivity control"
    return "mixed urban aquifer context"


def delta_p_for_sy(row: pd.Series, sy: float) -> float:
    pgv = 100.0 * float(row["pga_475_g"])
    p0 = p_liquefaction(pgv, row["vs30"], row["precip"], row["dw_km"], row["wtd"])
    delta_wtd = -(float(row["tws_cm_yr"]) * NYEARS / 100.0) / sy
    p1 = p_liquefaction(pgv, row["vs30"], row["precip"], row["dw_km"], max(float(row["wtd"]) + delta_wtd, 0.0))
    return float(p1 - p0)


def sy_threshold(row: pd.Series, lo: float = 0.03, hi: float = 0.25) -> float | None:
    if abs(delta_p_for_sy(row, lo)) < MATERIAL:
        return None
    if abs(delta_p_for_sy(row, hi)) >= MATERIAL:
        return hi
    a, b = lo, hi
    for _ in range(56):
        mid = (a + b) / 2.0
        if abs(delta_p_for_sy(row, mid)) >= MATERIAL:
            a = mid
        else:
            b = mid
    return a


def build_aquifer_products(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    priors = []
    for cls, vals in AQUIFER_PRIORS.items():
        priors.append({"aquifer_context_class": cls, **vals, "source_basis": "USGS WSP 1662-D; Lv et al. 2021; project proxy bins"})
    priors_df = pd.DataFrame(priors)
    priors_df.to_csv(DER / "aquifer_class_sy_priors_r39.csv", index=False)

    rows = []
    for _, row in frame.iterrows():
        cls = classify_aquifer(row)
        prior = AQUIFER_PRIORS[cls]
        d_low = delta_p_for_sy(row, prior["sy_low"])
        d_mid = delta_p_for_sy(row, prior["sy_mid"])
        d_high = delta_p_for_sy(row, prior["sy_high"])
        thr = sy_threshold(row)
        rows.append(
            {
                "name": row["name"],
                "country": row["country"],
                "lat": row["lat"],
                "lon": row["lon"],
                "population": row["population"],
                "aquifer_context_class": cls,
                "sy_low": prior["sy_low"],
                "sy_mid": prior["sy_mid"],
                "sy_high": prior["sy_high"],
                "class_basis": prior["basis"],
                "dP_sy_low": d_low,
                "dP_sy_mid": d_mid,
                "dP_sy_high": d_high,
                "material_at_sy_low": abs(d_low) >= MATERIAL,
                "material_at_sy_mid": abs(d_mid) >= MATERIAL,
                "material_at_sy_high": abs(d_high) >= MATERIAL,
                "sy_material_threshold_0p03_0p25": thr,
                "direction": "increase" if row["dP"] > 0 else "decrease",
                "class_prior_use": "review-prior only; replace with local hydrogeology before engineering use",
            }
        )
    city_df = pd.DataFrame(rows)
    city_df.to_csv(DER / "city_aquifer_class_sy_results_r39.csv", index=False)

    material = pd.read_csv(DER / "material_unit_gfz_gravis_stress_test_r37.csv")
    cards = city_df.merge(material[["name", "country", "gfz_dP_sy010", "gfz_leakage_corrected_dP_sy010"]], on=["name", "country"], how="inner")
    cards = cards[
        [
            "name",
            "country",
            "aquifer_context_class",
            "sy_low",
            "sy_mid",
            "sy_high",
            "dP_sy_low",
            "dP_sy_mid",
            "dP_sy_high",
            "material_at_sy_low",
            "material_at_sy_mid",
            "material_at_sy_high",
            "sy_material_threshold_0p03_0p25",
            "gfz_dP_sy010",
            "gfz_leakage_corrected_dP_sy010",
            "class_prior_use",
        ]
    ]
    cards.to_csv(DER / "material_unit_aquifer_class_phase_r39.csv", index=False)
    summary = {
        "n_cities": int(len(city_df)),
        "class_counts": city_df["aquifer_context_class"].value_counts().to_dict(),
        "n_material_at_class_mid": int(city_df["material_at_sy_mid"].sum()),
        "n_material_at_class_high": int(city_df["material_at_sy_high"].sum()),
        "material_units_at_class_mid": cards[["name", "country", "material_at_sy_mid"]].to_dict(orient="records"),
        "boundary": "Aquifer classes are review priors and do not replace local S_y or liquefiable-layer data.",
    }
    (DER / "aquifer_class_sy_summary_r39.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return priors_df, city_df, cards


def build_evidence_cards(jpl: JplStatus) -> pd.DataFrame:
    score = pd.read_csv(DER / "regional_evidence_scorecard_r37.csv")
    rows = []
    for _, r in score.iterrows():
        unit = r["regional_unit"]
        if "North China" in unit:
            card = "NCP-Beijing"
            article_class = "mechanism anchor"
            aquifer = "semi-confined basin-fill recovery"
            use = "Shows managed recovery can move the water-table term; not a material global-screen case."
        elif "Tokyo" in unit:
            card = "Tokyo Bay-Yokohama"
            article_class = "sign-supported coastal review case"
            aquifer = "coastal mixed/delta-reclaimed review"
            use = "Positive coastal case with local sign support; materiality remains product- and S_y-bounded."
        elif "Mumbai" in unit:
            card = "Mumbai-Bhayandar"
            article_class = "candidate-only contradiction boundary"
            aquifer = "coastal mixed/delta-reclaimed review"
            use = "Demonstrates why coastal positive screens need leakage and local-well checks."
        elif "Delhi" in unit:
            card = "Delhi"
            article_class = "product-material depletion case"
            aquifer = "alluvial/basin-fill depletion"
            use = "Strongest independent materiality case; depletion lowers one metric while worsening water/subsidence risk."
        else:
            card = "Lahore-Punjab"
            article_class = "depletion-side regional review case"
            aquifer = "alluvial/basin-fill depletion"
            use = "Borehole/GRACE/InSAR evidence supports depletion-subsidence coupling; materiality remains product-bounded."
        rows.append(
            {
                "card": card,
                "regional_unit": unit,
                "article_claim_class": article_class,
                "primary_exposure_names": r["primary_exposure_names"],
                "aquifer_context_class": aquifer,
                "csr_status": r["csr_screen_status"],
                "gsfc_status": r["gsfc_status"],
                "gfz_status": r["gfz_gravis_status"],
                "jpl_cri_status": jpl.run_status,
                "local_groundwater_or_insar_evidence": f"{r['direct_well_evidence']} | {r['insar_or_subsidence_evidence']}",
                "engineering_context": r["engineering_susceptibility_context"],
                "claim_boundary": r["claim_class"],
                "article_use": use,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(DER / "evidence_tier_cards_r39.csv", index=False)
    md = ["# Independent evidence-tier cards for regional sign and claim class", ""]
    for _, row in out.iterrows():
        md.extend(
            [
                f"## {row['card']}",
                "",
                f"- Claim class: {row['article_claim_class']}",
                f"- Aquifer context: {row['aquifer_context_class']}",
                f"- CSR: {row['csr_status']}",
                f"- GSFC: {row['gsfc_status']}",
                f"- GFZ: {row['gfz_status']}",
                f"- JPL CRI: {row['jpl_cri_status']}",
                f"- Local/InSAR evidence: {row['local_groundwater_or_insar_evidence']}",
                f"- Article use: {row['article_use']}",
                "",
            ]
        )
    (DER / "evidence_tier_cards_r39.md").write_text("\n".join(md), encoding="utf-8")
    return out


def configure_figure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
        }
    )


def make_aquifer_phase_figure(phase: pd.DataFrame) -> None:
    configure_figure_style()
    order = ["Yokohama", "Bhayandar", "Mumbai", "Delhi", "Lahore", "Ludhiana"]
    phase = phase.set_index("name").loc[order].reset_index()
    colors = {"increase": "#b65b2a", "decrease": "#2f6fb3"}
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 4.8), gridspec_kw={"width_ratios": [1.2, 1.1, 1.0]})

    ax = axes[0]
    y = np.arange(len(phase))
    for i, row in phase.iterrows():
        ax.plot([row["sy_low"], row["sy_high"]], [i, i], color="#8b949e", lw=5, alpha=0.35)
        ax.scatter([row["sy_mid"]], [i], color=colors["increase" if row["dP_sy_mid"] > 0 else "decrease"], s=45, zorder=3)
        ax.text(row["sy_high"] + 0.006, i, row["aquifer_context_class"].replace(" review", ""), va="center", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['name']} ({r['country']})" for _, r in phase.iterrows()])
    ax.invert_yaxis()
    ax.set_xlabel("Review-prior S_y range")
    ax.set_xlim(0.02, 0.28)
    ax.set_title("a  Aquifer-context review priors", loc="left", fontweight="bold")

    ax = axes[1]
    ax.axvspan(-MATERIAL, MATERIAL, color="#f1eee6", zorder=0)
    ax.axvline(0, color="#333333", lw=0.9)
    ax.axvline(MATERIAL, color="#9da4aa", ls="--", lw=0.8)
    ax.axvline(-MATERIAL, color="#9da4aa", ls="--", lw=0.8)
    for i, row in phase.iterrows():
        xs = [row["dP_sy_low"], row["dP_sy_mid"], row["dP_sy_high"]]
        c = colors["increase" if row["dP_sy_mid"] > 0 else "decrease"]
        ax.plot(xs, [i, i, i], color=c, lw=2.5, alpha=0.5)
        ax.scatter(xs, [i, i, i], color=c, s=[26, 48, 26], edgecolor="white", lw=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlabel("Delta P_liq under class S_y")
    ax.set_title("b  Product sign vs S_y materiality", loc="left", fontweight="bold")

    ax = axes[2]
    ax.axis("off")
    notes = [
        ("Sign", "constrained by CSR, GSFC and GFZ"),
        ("Materiality", "conditional on local S_y replacement"),
        ("JPL CRI", "Earthdata-bound unless authenticated"),
        ("Use", "review cue, not design threshold"),
    ]
    y0 = 0.88
    for i, (head, body) in enumerate(notes):
        box = FancyBboxPatch((0.05, y0 - i * 0.2), 0.90, 0.13, boxstyle="round,pad=0.02,rounding_size=0.02", fc="#eef3f2", ec="#9ca3a5", lw=0.8)
        ax.add_patch(box)
        ax.text(0.09, y0 + 0.045 - i * 0.2, head, fontweight="bold", fontsize=9, va="center")
        ax.text(0.09, y0 - 0.005 - i * 0.2, body, fontsize=7.5, va="center")
    ax.set_title("c  Local replacement rule", loc="left", fontweight="bold")
    fig.suptitle("Aquifer-class S_y phase diagram for screening materiality", x=0.03, ha="left", fontsize=12, fontweight="bold")
    out = FIG / "Fig5_aquifer_class_phase_article"
    for ext in [".svg", ".pdf", ".png"]:
        fig.savefig(out.with_suffix(ext), dpi=600 if ext == ".png" else None, bbox_inches="tight")
    plt.close(fig)


def make_evidence_cards_figure(cards: pd.DataFrame) -> None:
    configure_figure_style()
    fig, ax = plt.subplots(figsize=(13.2, 6.4))
    ax.axis("off")
    title = "Evidence-tier cards for regional sign and claim class"
    ax.text(0.01, 0.97, title, fontsize=13, fontweight="bold", ha="left", va="top")
    cards_compact = [
        (
            "NCP-\nBeijing",
            "#e7f0e6",
            [
                ("Class", "mechanism anchor"),
                ("Products", "positive sign; Beijing sub-material"),
                ("Local", ">2,000 wells + Beijing study"),
                ("S_y", "no material crossing in global screen"),
                ("Use", "recharge-side mechanism"),
            ],
        ),
        (
            "Tokyo Bay-\nYokohama",
            "#e7f1f6",
            [
                ("Class", "sign-supported coastal review"),
                ("Products", "CSR material; GSFC/GFZ sign"),
                ("Local", "Yokohama/Tokyo wells rising"),
                ("S_y", "material only at low-moderate S_y"),
                ("Use", "coastal follow-up case"),
            ],
        ),
        (
            "Mumbai-\nBhayandar",
            "#f7eee3",
            [
                ("Class", "candidate-only boundary"),
                ("Products", "CSR/GFZ positive; GSFC weak"),
                ("Local", "Mumbai wells indicate depletion"),
                ("Leakage", "GFZ land grid 70-80 km away"),
                ("Use", "overclaim guardrail"),
            ],
        ),
        (
            "Delhi",
            "#e8ecf6",
            [
                ("Class", "product-material depletion"),
                ("Products", "CSR + GSFC + GFZ support"),
                ("Local", "station groundwater decline"),
                ("Hazard", "subsidence/water stress worsen"),
                ("Use", "strongest depletion case"),
            ],
        ),
        (
            "Lahore-\nPunjab",
            "#e8ecf6",
            [
                ("Class", "regional depletion review"),
                ("Products", "CSR/GFZ material; GSFC near"),
                ("Local", "boreholes + GRACE + InSAR"),
                ("Hazard", "subsidence/water stress worsen"),
                ("Use", "depletion paradox"),
            ],
        ),
    ]
    x0s = np.linspace(0.02, 0.82, 5)
    for x0, (short, color, lines) in zip(x0s, cards_compact):
        box = FancyBboxPatch((x0, 0.12), 0.17, 0.75, boxstyle="round,pad=0.018,rounding_size=0.018", fc=color, ec="#80868b", lw=0.9)
        ax.add_patch(box)
        ax.text(x0 + 0.015, 0.82, short, fontsize=10, fontweight="bold", ha="left", va="top")
        y = 0.69
        for label, value in lines:
            ax.text(x0 + 0.015, y, label, fontsize=6.9, fontweight="bold", ha="left", va="top")
            ax.text(x0 + 0.015, y - 0.035, value, fontsize=6.9, ha="left", va="top")
            y -= 0.115
        ax.text(x0 + 0.015, 0.18, "JPL: Earthdata-bound", fontsize=6.8, color="#60666b", ha="left", va="top")
    ax.text(
        0.02,
        0.05,
        "Boundary: cards support regional sign and claim class only; they do not validate city magnitudes, shallow liquefiable-layer heads or site factor of safety.",
        fontsize=8,
        color="#555",
        ha="left",
    )
    out = FIG / "Fig4_evidence_tier_cards_article"
    for ext in [".svg", ".pdf", ".png"]:
        fig.savefig(out.with_suffix(ext), dpi=600 if ext == ".png" else None, bbox_inches="tight")
    plt.close(fig)


def build_release_package(jpl: JplStatus) -> Path:
    if REL.exists():
        shutil.rmtree(REL)
    (REL / "data").mkdir(parents=True)
    (REL / "figures").mkdir()
    (REL / "scripts").mkdir()
    files = [
        "city_results_v2.csv",
        "city_inputs.csv",
        "zero_aware_fdr_city_results_r27.csv",
        "static_observed_triage_tier_change_r31.csv",
        "independence_scale_counts_r33.csv",
        "product_support_table_r33.csv",
        "product_support_summary_r33.csv",
        "gfz_gravis_stress_summary_r37.csv",
        "gfz_gravis_city_trends_r37.csv",
        "material_unit_gfz_gravis_stress_test_r37.csv",
        "three_product_city_consensus_r37.csv",
        "engineering_susceptibility_enrichment_r37.csv",
        "ab_followup_engineering_profile_r37.csv",
        "aquifer_class_sy_priors_r39.csv",
        "city_aquifer_class_sy_results_r39.csv",
        "material_unit_aquifer_class_phase_r39.csv",
        "aquifer_class_sy_summary_r39.json",
        "evidence_tier_cards_r39.csv",
        "evidence_tier_cards_r39.md",
        "jpl_cri_article_status_r39.csv",
        "jpl_cri_article_status_r39.json",
        "regional_evidence_scorecard_r37.csv",
        "preimplementation_policy_protocol_r37.csv",
        "external_collaborator_role_matrix_r37.csv",
    ]
    copied = []
    for name in files:
        src = DER / name
        if src.exists():
            dst = REL / "data" / name
            shutil.copy2(src, dst)
            copied.append(dst)
    for stem in [
        "Fig1_mechanism",
        "Fig2_global_signresolved",
        "Fig3_regional",
        "Fig4_timeseries",
        "Fig4_evidence_tier_cards_article",
        "Fig5_aquifer_class_phase_article",
        "Fig6_evidence_boundary",
    ]:
        for ext in [".svg", ".pdf", ".png"]:
            src = FIG / f"{stem}{ext}"
            if src.exists():
                dst = REL / "figures" / src.name
                shutil.copy2(src, dst)
                copied.append(dst)
    for script in [
        "zhu2017.py",
        "r24_jpl_cri_and_local_groundwater_evidence.py",
        "r28_specific_yield_sensitivity.py",
        "r37_third_product_engineering_policy_protocol.py",
        "r39_article_dataset_release.py",
        "verify_derived_outputs.py",
    ]:
        src = ROOT / "scripts" / script
        if src.exists():
            dst = REL / "scripts" / script
            shutil.copy2(src, dst)
            copied.append(dst)
    readme = f"""# Dynamic Groundwater-Liquefaction Screening Dataset v1.0

Local release prepared: {datetime.now(timezone.utc).isoformat()}

This derived-data release supports the manuscript route "A dynamic groundwater screen for liquefaction review in seismic urban water management".

## Contents

- 444 city exposure units and modelled Delta P_liq outputs.
- Zero-aware FDR and static-counterfactual review tiers.
- 50 km / GHSL / 300 km independence-scale diagnostics.
- CSR, GSFC and GFZ product-support tables.
- JPL CRI access status: `{jpl.run_status}`. The protected NetCDF is not redistributed and is not used as a claim unless authenticated sampling is completed.
- Aquifer-context S_y review priors and phase calculations.
- Evidence-tier cards for regional sign and claim class.
- Engineering-context enrichment diagnostics and non-regulatory review protocol.

## Boundary

This is a derived screening dataset, not a hazard map, city ranking, regulatory threshold, damage forecast or engineering factor-of-safety dataset. GRACE/GRACE-FO products are regional storage drivers. Local wells, S_y, sediment and liquefaction records must replace review priors before site use.

## DOI

Zenodo DOI: to be minted by the author after repository upload/release approval.
"""
    (REL / "README.md").write_text(readme, encoding="utf-8")
    (REL / "DATASET_CITATION.txt").write_text(
        "Ren, L. Dynamic Groundwater-Liquefaction Screening Dataset v1.0. Zenodo DOI to be minted.\n",
        encoding="utf-8",
    )
    (REL / "zenodo.json").write_text(
        json.dumps(
            {
                "title": "Dynamic Groundwater-Liquefaction Screening Dataset v1.0",
                "upload_type": "dataset",
                "description": "Derived city, regional-group, product-consensus, aquifer-context and evidence-tier tables for a dynamic groundwater-liquefaction screening study.",
                "creators": [{"name": "Ren, Lijian", "affiliation": "Inner Mongolia University of Technology"}],
                "license": "cc-by-4.0",
                "keywords": ["GRACE", "groundwater", "liquefaction", "urban risk", "specific yield"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest_rows = []
    for p in sorted([x for x in REL.rglob("*") if x.is_file()]):
        if p.name in {"MANIFEST.csv", "CHECKSUMS_SHA256.txt"}:
            continue
        manifest_rows.append(
            {
                "relative_path": str(p.relative_to(REL)).replace("\\", "/"),
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
        )
    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(REL / "MANIFEST.csv", index=False)
    (REL / "CHECKSUMS_SHA256.txt").write_text(
        "\n".join(f"{r['sha256']}  {r['relative_path']}" for r in manifest_rows) + "\n",
        encoding="utf-8",
    )
    zip_path = REL.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(REL.rglob("*")):
            if p.is_file():
                zf.write(p, arcname=f"{REL.name}/{p.relative_to(REL)}")
    return zip_path


def main() -> None:
    DER.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    jpl = check_jpl_cri()
    frame = load_frame()
    priors, city_sy, phase = build_aquifer_products(frame)
    cards = build_evidence_cards(jpl)
    make_aquifer_phase_figure(phase)
    make_evidence_cards_figure(cards)
    zip_path = build_release_package(jpl)
    summary = {
        "jpl_status": jpl.run_status,
        "n_aquifer_prior_classes": int(len(priors)),
        "n_city_sy_rows": int(len(city_sy)),
        "n_evidence_cards": int(len(cards)),
        "dataset_release_dir": str(REL.relative_to(ROOT)),
        "dataset_release_zip": str(zip_path.relative_to(ROOT)),
        "zip_bytes": zip_path.stat().st_size,
        "boundary": "R39 completes local Article-facing products; Zenodo DOI and Earthdata-authenticated JPL ingestion remain human/auth boundaries unless credentials are provided.",
    }
    (DER / "r39_article_dataset_release_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
