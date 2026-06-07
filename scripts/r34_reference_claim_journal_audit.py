"""R34 reference, claim-evidence and journal-fit audit.

This author-side audit strengthens the submission package without changing the
scientific result. It creates:

- manuscript/Submit-NatureWater-2026/Reference_Audit_R34.csv
- manuscript/Submit-NatureWater-2026/Reference_Audit_R34.md
- 02_source_registry.md
- 03_claim_evidence_map.md
- manuscript/Target_Journal_Strategy_R34.md

The network checks are conservative: Crossref is used for DOI metadata where
available; doi.org GET is used for dataset and publisher records outside
Crossref; non-DOI URLs are checked for reachability only.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests


ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "manuscript"
OUT = MAN / "Submit-NatureWater-2026"
SOURCE = MAN / "manuscript_nature_water.md"

UA = "IMUT-reference-claim-audit/0.2 (mailto:renlijian@imut.edu.cn)"


@dataclass
class ReferenceRow:
    number: int
    entry: str
    doi: str
    url: str
    status: str
    status_detail: str
    checked_source: str
    title_check: str


def split_references(md: str) -> list[tuple[int, str]]:
    m = re.search(r"\n## References\s+(.*)$", md, flags=re.S)
    if not m:
        raise RuntimeError("No references section found.")
    refs = []
    for line in m.group(1).splitlines():
        line = line.strip()
        mm = re.match(r"^(\d+)\.\s+(.*)$", line)
        if mm:
            refs.append((int(mm.group(1)), mm.group(2)))
    return refs


def first_url(text: str) -> str:
    m = re.search(r"https?://[^\s\)]+", text)
    return m.group(0).rstrip(".,;") if m else ""


def first_doi(text: str) -> str:
    m = re.search(r"https://doi\.org/([^\s\)]+)", text)
    return m.group(1).rstrip(".,;") if m else ""


def check_doi(doi: str) -> tuple[str, str, str, str]:
    try:
        r = requests.get(
            f"https://api.crossref.org/works/{doi}",
            timeout=12,
            headers={"User-Agent": UA},
        )
        if r.status_code == 200:
            msg = r.json().get("message", {})
            title = "; ".join(msg.get("title") or [])[:240]
            container = "; ".join(msg.get("container-title") or [])[:120]
            return "verified_crossref", f"Crossref 200; {container}", "Crossref", title
        g = requests.get(
            f"https://doi.org/{doi}",
            timeout=16,
            allow_redirects=True,
            headers={"User-Agent": UA},
        )
        if g.status_code < 400:
            return "verified_doi_resolves", f"doi.org GET {g.status_code}; {g.url}", "doi.org", ""
        return "warning_doi_target", f"Crossref {r.status_code}; doi.org GET {g.status_code}; {g.url}", "Crossref/doi.org", ""
    except Exception as exc:  # pragma: no cover - audit resilience
        return "warning_network_error", f"{type(exc).__name__}: {exc}", "network", ""


def check_url(url: str) -> tuple[str, str, str, str]:
    if not url:
        return "no_url", "No DOI or URL found in entry.", "none", ""
    try:
        r = requests.get(url, timeout=16, allow_redirects=True, headers={"User-Agent": UA})
        if r.status_code < 400:
            return "verified_url_reachable", f"GET {r.status_code}; {r.url}", "URL", ""
        return "warning_url_status", f"GET {r.status_code}; {r.url}", "URL", ""
    except Exception as exc:  # pragma: no cover - audit resilience
        return "warning_network_error", f"{type(exc).__name__}: {exc}", "URL", ""


def build_reference_audit() -> list[ReferenceRow]:
    refs = split_references(SOURCE.read_text(encoding="utf-8"))
    rows: list[ReferenceRow] = []
    for number, entry in refs:
        doi = first_doi(entry)
        url = first_url(entry)
        if doi:
            status, detail, checked_source, title = check_doi(doi)
        else:
            status, detail, checked_source, title = check_url(url)
        rows.append(
            ReferenceRow(
                number=number,
                entry=entry,
                doi=doi,
                url=url,
                status=status,
                status_detail=detail,
                checked_source=checked_source,
                title_check=title,
            )
        )
    return rows


def write_reference_outputs(rows: list[ReferenceRow]) -> None:
    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "Reference_Audit_R34.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ReferenceRow.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    warnings = [row for row in rows if row.status.startswith("warning") or row.status == "no_url"]

    md = [
        "# R34 Reference Audit",
        "",
        "Date: 2026-06-08",
        "",
        f"References checked: {len(rows)}",
        "",
        "## Status counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        md.append(f"- `{status}`: {count}")
    md.extend(["", "## Warnings / Manual Follow-up", ""])
    if warnings:
        for row in warnings:
            md.append(f"- Ref. {row.number}: `{row.status}` - {row.status_detail}")
    else:
        md.append("- None.")
    md.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is an author-side audit. Crossref/doi.org/URL reachability supports reference authenticity, but final bibliography decisions still require author review for reports, official web pages and dataset landing pages.",
        ]
    )
    (OUT / "Reference_Audit_R34.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def source_registry_rows() -> list[dict[str, str]]:
    return [
        {
            "id": "SRC-GRACE-CSR",
            "source": "CSR GRACE/GRACE-FO RL06.3 mascon total-water-storage anomalies",
            "role": "Primary regional storage driver",
            "evidence_files": "data_derived/city_gws.csv; data_derived/city_results_v2.csv; data_derived/city_results_spatial_r20.csv",
            "claim_boundary": "Regional storage proxy at roughly 300 km scale; not a city well or shallow liquefiable-layer head.",
            "status": "verified source / derived data present",
        },
        {
            "id": "SRC-GSFC",
            "source": "NASA GSFC GRACE/GRACE-FO RL06v2.0 mascon product",
            "role": "Independent mascon sign and materiality guardrail",
            "evidence_files": "data_derived/gsfc_city_trends_r21.csv; data_derived/product_support_table_r33.csv",
            "claim_boundary": "Supports direction for 6/6 baseline units, p<0.05 sign support for 4/6 and materiality for Delhi only.",
            "status": "ingested",
        },
        {
            "id": "SRC-JPL-CRI",
            "source": "JPL GRACE/GRACE-FO CRI filtered mascon product",
            "role": "Candidate coastal sensitivity product",
            "evidence_files": "data_derived/r24_jpl_cri_access_status.csv; data_derived/jpl_cri_earthdata_runner_status_r25.csv",
            "claim_boundary": "Earthdata-authentication boundary; no JPL robustness claim is made.",
            "status": "verified collection / not ingested",
        },
        {
            "id": "SRC-ZHU2017",
            "source": "Zhu, Baise and Thompson global geospatial liquefaction model",
            "role": "Published liquefaction-screening model; water-table term perturbed only",
            "evidence_files": "scripts/zhu2017.py; data_derived/city_results_v2.csv",
            "claim_boundary": "Screening probability/index, not engineering factor of safety or damage prediction.",
            "status": "verified DOI / implemented",
        },
        {
            "id": "SRC-GHSL",
            "source": "GHSL R2024A urban-centre polygons",
            "role": "Exposure-unit deduplication and urban-centre aggregation",
            "evidence_files": "data_derived/ghsl_urban_centre_matches_r21.csv; data_derived/independence_scale_counts_r33.csv",
            "claim_boundary": "Used for exposure aggregation; does not change city-level model calculation.",
            "status": "verified dataset DOI / derived data present",
        },
        {
            "id": "SRC-TOKYO-YOKOHAMA",
            "source": "Yokohama municipal and Tokyo official groundwater records",
            "role": "Local sign support for Tokyo Bay/Yokohama",
            "evidence_files": "data_derived/yokohama_groundwater_trends_r24.csv; data_derived/tokyo_bay_groundwater_evidence_summary_r25.csv; data_derived/local_evidence_sign_tests_r33.csv",
            "claim_boundary": "Sign support only; not shallow liquefiable-layer calibration, management attribution or mascon materiality proof.",
            "status": "parsed / sign-tested",
        },
        {
            "id": "SRC-MUMBAI",
            "source": "DOI-verified Mumbai groundwater station evidence and CGWB access attempts",
            "role": "Guardrail against positive Mumbai-Bhayandar overclaim",
            "evidence_files": "data_derived/mumbai_bhayandar_evidence_boundary_r25.csv; data_derived/cgwb_access_retry_status_r25.csv",
            "claim_boundary": "Contradicts positive recovery attribution; Mumbai-Bhayandar remains candidate-only.",
            "status": "verified DOI / official raw access incomplete",
        },
        {
            "id": "SRC-NCP",
            "source": "North China Plain / Beijing aquifer recovery and Beijing liquefaction mechanism studies",
            "role": "Recharge-side mechanism anchor",
            "evidence_files": "data_derived/validation_evidence_matrix_v2.csv; data_derived/confidence_ledger_detail_r29.csv",
            "claim_boundary": "Supports recharge-side mechanism; Beijing is sub-material in global screen.",
            "status": "verified DOI / evidence registry present",
        },
        {
            "id": "SRC-PUNJAB",
            "source": "Delhi, Lahore and Punjab depletion evidence plus global subsidence literature",
            "role": "Depletion-side paradox anchor",
            "evidence_files": "data_derived/validation_evidence_matrix_v2.csv; data_derived/product_support_table_r33.csv",
            "claim_boundary": "Lower liquefaction-screening metric is not a safety benefit because subsidence/water security worsen.",
            "status": "verified DOI / evidence registry present",
        },
    ]


def write_markdown_table(path: Path, title: str, rows: Iterable[dict[str, str]]) -> None:
    rows = list(rows)
    headers = list(rows[0].keys())
    out = [f"# {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row[h]).replace("\n", " ") for h in headers) + " |")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def claim_map_rows() -> list[dict[str, str]]:
    return [
        {
            "claim_id": "C1",
            "main_claim": "The paper is not a diffuse global amplification story.",
            "support": "Mean Delta P_liq = +0.00042; geographic reassignment null p = 1.00.",
            "evidence_files": "data_derived/core_summary_v2.json; figures/Fig2_global_signresolved.*",
            "safe_wording": "The geographic-null test did not support diffuse global amplification.",
            "forbidden_wording": "Groundwater management globally increases liquefaction risk.",
        },
        {
            "claim_id": "C2",
            "main_claim": "Observed regional storage change creates a sign-resolved correction to static water-table screening.",
            "support": "Water-table term only is perturbed in the Zhu et al. model; all non-groundwater predictors fixed.",
            "evidence_files": "scripts/zhu2017.py; data_derived/city_results_v2.csv; figures/Fig1_mechanism.*",
            "safe_wording": "Regional correction to a managed water-table state variable.",
            "forbidden_wording": "New site-specific liquefaction hazard map or engineering design estimate.",
        },
        {
            "claim_id": "C3",
            "main_claim": "The operational payload is 28 A/B point-city follow-up units, not 28 independent hydrological discoveries.",
            "support": "R31 and R33 static-counterfactual audit; 28 point-city units collapse to 21 metro clusters, 22 GHSL centres and 10 regional groups.",
            "evidence_files": "data_derived/static_observed_triage_tier_summary_r31.json; data_derived/independence_scale_counts_r33.csv",
            "safe_wording": "Point-city exposure units requiring local follow-up.",
            "forbidden_wording": "28 independent groundwater hotspots.",
        },
        {
            "claim_id": "C4",
            "main_claim": "Six baseline CSR-material units are conditional screening units.",
            "support": "S_y=0.10 baseline; MC materiality probabilities 0.30-0.55; S_y* 0.108-0.160.",
            "evidence_files": "data_derived/materiality_uncertainty_table_r33.csv; data_derived/specific_yield_thresholds_r28.csv",
            "safe_wording": "Baseline CSR-material at S_y=0.10.",
            "forbidden_wording": "Robustly material under all plausible aquifer assumptions.",
        },
        {
            "claim_id": "C5",
            "main_claim": "GSFC supports signs but not most material magnitudes.",
            "support": "6/6 direction match, 4/6 p<0.05 sign support, 1/6 GSFC-material, 0/3 positive coastal GSFC-material.",
            "evidence_files": "data_derived/product_support_table_r33.csv; data_derived/product_support_summary_r33.csv; figures/Fig7_ghsl_gsfc_robustness.*",
            "safe_wording": "Independent product guardrail.",
            "forbidden_wording": "All six hotspots are independently reproduced as material by GSFC.",
        },
        {
            "claim_id": "C6",
            "main_claim": "Tokyo Bay/Yokohama has local sign support, not independent material proof.",
            "support": "Yokohama 20/23 rising; Tokyo official records 4/4, 78/90, 75/91 and 79/91 positive/rising.",
            "evidence_files": "data_derived/local_evidence_sign_tests_r33.csv; figures/FigS1_yokohama_local_groundwater_r24.*; figures/FigS2_tokyo_representative_groundwater_r25.*",
            "safe_wording": "Locally sign-supported positive screen.",
            "forbidden_wording": "Tokyo Bay proves CSR materiality or local shallow liquefiable heads.",
        },
        {
            "claim_id": "C7",
            "main_claim": "Mumbai-Bhayandar remains candidate-only.",
            "support": "DOI-verified Mumbai station evidence indicates increasing depth/depletion; no Bhayandar positive official trend extracted.",
            "evidence_files": "data_derived/mumbai_bhayandar_evidence_boundary_r25.csv; data_derived/local_groundwater_evidence_registry_r25.csv",
            "safe_wording": "CSR-positive candidate boundary with contradictory local evidence.",
            "forbidden_wording": "Positive Mumbai/Bhayandar groundwater recovery validation.",
        },
        {
            "claim_id": "C8",
            "main_claim": "North China Plain / Beijing anchors the recharge-side mechanism.",
            "support": "Independent well-based recovery evidence plus Beijing liquefaction mechanism study; Beijing sub-material in global screen.",
            "evidence_files": "data_derived/validation_evidence_matrix_v2.csv; data_derived/confidence_ledger_detail_r29.csv",
            "safe_wording": "Mechanism anchor, not one of the six material global-screen units.",
            "forbidden_wording": "Beijing is a material global hotspot in this screen.",
        },
        {
            "claim_id": "C9",
            "main_claim": "Punjab depletion lowers the liquefaction-screening metric but worsens other hazards.",
            "support": "Delhi/Lahore/Ludhiana depletion-side units; subsidence and water-security literature.",
            "evidence_files": "data_derived/product_support_table_r33.csv; data_derived/validation_evidence_matrix_v2.csv",
            "safe_wording": "Depletion-side paradox.",
            "forbidden_wording": "Groundwater depletion is a safety benefit.",
        },
        {
            "claim_id": "C10",
            "main_claim": "The policy output is a non-regulatory pre-implementation screen.",
            "support": "R31/R33 static-counterfactual tiers; Fig5 water-table-rise flag; Fig7 decision endpoint.",
            "evidence_files": "data_derived/policy_priority_table_v2.csv; data_derived/water_table_trigger_r20.csv; figures/Fig5_policy_robustness.*; figures/Fig7_ghsl_gsfc_robustness.*",
            "safe_wording": "Trigger local well, sediment and liquefaction review.",
            "forbidden_wording": "Regulatory threshold, damage forecast or engineering design standard.",
        },
    ]


def write_journal_strategy() -> None:
    text = """# R34 Target-Journal Strategy

Date: 2026-06-08

## Independent target decision

Primary stretch target: **Nature Water, Analysis**.

Reason: the paper's strongest defensible novelty is not a new liquefaction model; it is a water-management screening blind spot. Nature Water's current scope covers natural sciences, engineering and social-science dimensions of water, with interest in interdisciplinary work, and its Analysis format accepts existing-data/model analyses that lead to novel and broad conclusions.

## Why not a broader Nature-branded first target

- **Nature Sustainability** is broader and more policy/solutions-driven. The manuscript has a strong cross-sector implication, but it does not evaluate policy adoption, equity, finance, behavioural response or sustainability outcomes directly enough for first-shot fit.
- **Nature Cities** or **npj Urban Sustainability** could fit the urban-resilience angle, but the manuscript's evidence base is water-storage and liquefaction screening rather than urban planning or implemented urban transitions.
- **Communications Earth & Environment** remains the best transfer/second target because the Earth/environmental modelling and hazard-screening contribution fits more directly.

## Reframing rule for Nature Water

Lead with: water-management decisions move a monitored state variable that static seismic screens treat as fixed.

Do not lead with: a new global liquefaction hazard map, climate-driven global increase, or earthquake causation.

## Recommended Nature Water title

Regional water-storage change creates bidirectional liquefaction-screening priorities in seismic cities

## Transfer titles

- Communications Earth & Environment: Regional storage trends correct static water-table assumptions in urban liquefaction screening
- Engineering Geology / Natural Hazards fallback: Regional groundwater trends update urban liquefaction-screening priorities under water-table change

## Hard upload blockers

Nature Water remains the strongest target only after the authors complete author metadata, declarations, suggested reviewers, repository/Zenodo release and final AI-use disclosure.
"""
    (MAN / "Target_Journal_Strategy_R34.md").write_text(text, encoding="utf-8")


def main() -> None:
    rows = build_reference_audit()
    write_reference_outputs(rows)
    write_markdown_table(ROOT / "02_source_registry.md", "R34 Source Registry", source_registry_rows())
    write_markdown_table(ROOT / "03_claim_evidence_map.md", "R34 Claim-Evidence Map", claim_map_rows())
    write_journal_strategy()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    print(json.dumps({"references": len(rows), "status_counts": counts}, indent=2, ensure_ascii=False))
    print("Wrote R34 reference audit, source registry, claim-evidence map and journal strategy.")


if __name__ == "__main__":
    main()
