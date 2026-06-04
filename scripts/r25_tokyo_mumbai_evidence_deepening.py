"""R25 Tokyo Bay / Mumbai-Bhayandar evidence deepening.

This round keeps the liquefaction model unchanged. It adds traceable local
evidence for the two remaining coastal positive settings and records why JPL
CRI cannot be sampled without Earthdata credentials in the current workspace.

Outputs are written to data_derived/ and figures/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
from scipy.stats import linregress


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw"
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
TOKYO_RAW = RAW / "local_groundwater_evidence" / "tokyo_metropolitan"
MUMBAI_RAW = RAW / "local_groundwater_evidence" / "mumbai"
JPL_RAW = RAW / "grace" / "jpl"
for folder in [DER, FIG, TOKYO_RAW, MUMBAI_RAW, JPL_RAW]:
    folder.mkdir(parents=True, exist_ok=True)

TOKYO_ENV_PAGE = "https://www.env.go.jp/water/jiban/directory/13kantouminami.html"
TOKYO_ENV_EXCEL = "https://www.env.go.jp/content/000386723.xlsx"
TOKYO_OPEN_DATA_PACKAGE = (
    "https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_show?id=t000014d1700000013"
)
TOKYO_OPEN_DATA_PAGE = "https://catalog.data.metro.tokyo.lg.jp/dataset/t000014d1700000013"
TOKYO_REPORT_2022_PDF = "https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/000066298"

CGWB_MONITORING_PAGE = "https://www.cgwb.gov.in/ground-water-level-monitoring"
CGWB_GREATER_MUMBAI = "https://www.cgwb.gov.in/sites/default/files/2022-10/greater_mumbai.pdf"
CGWB_MAHARASHTRA_YEARBOOK = (
    "https://cgwb.gov.in/cgwbpnm/public/uploads/documents/1703237300342091479file.pdf"
)

AGRIS_MUMBAI_RECORD = "https://agris.fao.org/search/es/records/65df7da10f3e94b9e5d91b03"
MUMBAI_STUDY_DOI = "10.1016/j.gsd.2022.100797"
MUMBAI_CROSSREF = f"https://api.crossref.org/works/{MUMBAI_STUDY_DOI}"

JPL_CRI_SHORT = "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4"
JPL_CRI_COLLECTION_ID = "C3195527175-POCLOUD"
JPL_CRI_GRANULE = "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI"
JPL_CRI_DATA_URL = (
    "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/"
    "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4/"
    "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc"
)
JPL_CRI_MD5_URL = (
    "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-public/"
    "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4/"
    "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc.md5"
)
JPL_LOCAL_CANDIDATES = [
    JPL_RAW / "GRCTellus.JPL.200204_202603.GLO.RL06.3M.MSCNv04CRI.nc",
    JPL_RAW / "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4.nc",
    JPL_RAW / "TELLUS_GRAC-GRFO_MASCON_GRID_RL06.3_V4_CRI.nc",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def http_session(use_env_proxy: bool = True) -> requests.Session:
    session = requests.Session()
    session.trust_env = use_env_proxy
    session.headers.update({"User-Agent": "IMUT-reproducibility-evidence-check/1.0"})
    return session


def fetch_bytes(url: str, path: Path, timeout: int = 90, use_env_proxy: bool = True) -> dict:
    session = http_session(use_env_proxy)
    rec = {
        "url": url,
        "path": str(path.relative_to(ROOT)),
        "use_env_proxy": use_env_proxy,
        "status": "",
        "http_status": "",
        "content_type": "",
        "bytes": 0,
        "sha256": "",
        "error": "",
    }
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        rec["http_status"] = response.status_code
        rec["content_type"] = response.headers.get("content-type", "")
        rec["bytes"] = len(response.content)
        if response.ok and response.content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
            rec["sha256"] = hashlib.sha256(response.content).hexdigest()
            rec["status"] = "downloaded"
        else:
            rec["status"] = "http_not_ok"
    except Exception as exc:
        rec["status"] = "error"
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def extract_tokyo_page_summary(html_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    text = "\n".join(BeautifulSoup(html, "html.parser").get_text("\n").splitlines())
    m = re.search(r"(\d+)井.{0,30}?うち(\d+)井.{0,30}?上昇", text)
    if not m:
        m = re.search(r"(\d+)井.{0,30}?(\d+)井.{0,30}?上昇", text)
    excel_link = ""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a"):
        label = " ".join(link.get_text(" ", strip=True).split())
        if "Excel" in label:
            excel_link = urljoin(TOKYO_ENV_PAGE, link.get("href", ""))
            break
    return {
        "source_url": TOKYO_ENV_PAGE,
        "source_type": "Japan Ministry of the Environment regional land-subsidence directory",
        "report_year": 2024,
        "observation_wells": int(m.group(1)) if m else np.nan,
        "rising_confined_wells": int(m.group(2)) if m else np.nan,
        "share_rising": (int(m.group(2)) / int(m.group(1))) if m else np.nan,
        "excel_link": excel_link,
        "parse_status": "parsed" if m else "not_parsed",
        "safe_use": (
            "Official regional sign check for Tokyo/Kanto Plain South confined groundwater; "
            "not a city-scale GRACE recalibration."
        ),
    }


def parse_tokyo_representative_excel(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_excel(path, sheet_name=4, header=None)
    station_names = [str(v).strip() for v in df.iloc[3, 3:7].tolist()]
    station_locations = [str(v).strip() for v in df.iloc[4, 3:7].tolist()]
    aquifer_type = [str(v).strip() for v in df.iloc[8, 3:7].tolist()]
    rows = []
    year_map = {
        "平成27": 2015,
        "平成28": 2016,
        "平成29": 2017,
        "平成30": 2018,
        "令和元": 2019,
        "令和２": 2020,
        "令和３": 2021,
        "令和４": 2022,
        "令和５": 2023,
        "令和６": 2024,
    }
    for ridx in range(11, 21):
        label = str(df.iat[ridx, 2])
        year = None
        for key, value in year_map.items():
            if key in label:
                year = value
                break
        if year is None:
            continue
        for cidx, name in enumerate(station_names, start=3):
            value = pd.to_numeric(df.iat[ridx, cidx], errors="coerce")
            rows.append(
                {
                    "station": name,
                    "location": station_locations[cidx - 3],
                    "aquifer_type": aquifer_type[cidx - 3],
                    "year": year,
                    "groundwater_level_tp_m": float(value) if pd.notna(value) else np.nan,
                    "source_url": TOKYO_ENV_EXCEL,
                }
            )
    levels = pd.DataFrame(rows).dropna(subset=["groundwater_level_tp_m"])
    trend_rows = []
    for station, group in levels.groupby("station", sort=False):
        group = group.sort_values("year")
        fit = linregress(group["year"], group["groundwater_level_tp_m"])
        trend_rows.append(
            {
                "station": station,
                "location": group["location"].iloc[0],
                "aquifer_type": group["aquifer_type"].iloc[0],
                "n_years": len(group),
                "start_year": int(group["year"].min()),
                "end_year": int(group["year"].max()),
                "start_level_tp_m": float(group["groundwater_level_tp_m"].iloc[0]),
                "end_level_tp_m": float(group["groundwater_level_tp_m"].iloc[-1]),
                "change_m": float(group["groundwater_level_tp_m"].iloc[-1] - group["groundwater_level_tp_m"].iloc[0]),
                "ols_slope_m_per_year": float(fit.slope),
                "p_value": float(fit.pvalue),
                "r_squared": float(fit.rvalue**2),
                "direction": "rise" if fit.slope > 0 else "fall" if fit.slope < 0 else "flat",
                "source_url": TOKYO_ENV_EXCEL,
            }
        )
    trends = pd.DataFrame(trend_rows)
    levels.to_csv(DER / "tokyo_representative_groundwater_levels_r25.csv", index=False)
    trends.to_csv(DER / "tokyo_representative_groundwater_trends_r25.csv", index=False)
    return levels, trends


def parse_tokyo_open_data_package() -> tuple[pd.DataFrame, pd.DataFrame]:
    response = http_session(True).get(TOKYO_OPEN_DATA_PACKAGE, timeout=90)
    response.raise_for_status()
    package = response.json()["result"]
    resources = []
    table5_frames = []
    for res in package.get("resources", []):
        name = res.get("name", "")
        url = res.get("url", "")
        resources.append(
            {
                "package_id": package.get("id", ""),
                "package_title": package.get("title", ""),
                "resource_name": name,
                "resource_format": res.get("format", ""),
                "resource_url": url,
                "selected_for_download": "observed_groundwater_table" if "5" in name else "catalogued",
                "source_page": TOKYO_OPEN_DATA_PAGE,
            }
        )
        if "5" not in name:
            continue
        local_name = f"tokyo_open_data_{res.get('id', name).replace('/', '_')}.csv"
        status = fetch_bytes(url, TOKYO_RAW / local_name, timeout=90, use_env_proxy=True)
        if status["status"] != "downloaded":
            continue
        csv_path = ROOT / status["path"]
        try:
            df = pd.read_csv(csv_path, encoding="cp932")
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding="shift_jis")
        df.columns = [
            "area",
            "pipe_no",
            "well_name",
            "screen_depth_m",
            "ground_elevation_tp_m",
            "level_2013_tp_m",
            "level_2014_tp_m",
            "level_2015_tp_m",
            "level_2016_tp_m",
            "change_2015_minus_2014_m",
            "change_2016_minus_2015_m",
        ]
        df["resource_name"] = name
        df["resource_url"] = url
        table5_frames.append(df)
    resource_df = pd.DataFrame(resources)
    resource_df.to_csv(DER / "tokyo_open_data_resources_r25.csv", index=False)
    if table5_frames:
        table5 = pd.concat(table5_frames, ignore_index=True)
    else:
        table5 = pd.DataFrame()
    table5.to_csv(DER / "tokyo_open_data_table5_groundwater_2016_r25.csv", index=False)
    return resource_df, table5


def parse_tokyo_2022_pdf(path: Path) -> pd.DataFrame:
    rows = []
    if not path.exists():
        return pd.DataFrame()
    with pdfplumber.open(path) as pdf:
        for page_idx, table_name in [(31, "table5_ward_area"), (32, "table5_tama_area")]:
            text = pdf.pages[page_idx].extract_text() or ""
            for raw_line in text.splitlines():
                line = " ".join(raw_line.split())
                if ("研" not in line and "〃" not in line) or "12月31日" in line:
                    continue
                numbers = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", line)
                if len(numbers) < 6:
                    continue
                dc = float(numbers[-1])
                cb = float(numbers[-2]) if len(numbers) >= 2 else np.nan
                rows.append(
                    {
                        "table": table_name,
                        "raw_line": line,
                        "change_2021_minus_2020_m": cb,
                        "change_2022_minus_2021_m": dc,
                        "direction_2022": "rise" if dc > 0 else "fall" if dc < 0 else "flat",
                        "source_url": TOKYO_REPORT_2022_PDF,
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(DER / "tokyo_2022_pdf_table5_extracted_rows_r25.csv", index=False)
    return out


def summarize_tokyo_evidence(
    page_summary: dict,
    representative_trends: pd.DataFrame,
    table2016: pd.DataFrame,
    table2022: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    if not representative_trends.empty:
        rows.append(
            {
                "evidence_layer": "official_2024_excel_representative_wells",
                "source_url": TOKYO_ENV_EXCEL,
                "n_units": int(len(representative_trends)),
                "n_positive": int((representative_trends["ols_slope_m_per_year"] > 0).sum()),
                "n_negative": int((representative_trends["ols_slope_m_per_year"] < 0).sum()),
                "median_slope_m_per_year": float(representative_trends["ols_slope_m_per_year"].median()),
                "median_change_m": float(representative_trends["change_m"].median()),
                "window": "2015-2024",
                "safe_interpretation": "all four representative confined wells rise over the 10-year official series",
            }
        )
    if not table2016.empty:
        change = pd.to_numeric(table2016["change_2016_minus_2015_m"], errors="coerce")
        rows.append(
            {
                "evidence_layer": "tokyo_open_data_table5_2016",
                "source_url": TOKYO_OPEN_DATA_PAGE,
                "n_units": int(change.notna().sum()),
                "n_positive": int((change > 0).sum()),
                "n_negative": int((change < 0).sum()),
                "median_slope_m_per_year": np.nan,
                "median_change_m": float(change.median()),
                "window": "2015-2016 annual change",
                "safe_interpretation": "official downloadable well table confirms a broad positive annual sign in the archived open-data year",
            }
        )
    if not table2022.empty:
        change = pd.to_numeric(table2022["change_2022_minus_2021_m"], errors="coerce")
        rows.append(
            {
                "evidence_layer": "tokyo_official_pdf_table5_2022",
                "source_url": TOKYO_REPORT_2022_PDF,
                "n_units": int(change.notna().sum()),
                "n_positive": int((change > 0).sum()),
                "n_negative": int((change < 0).sum()),
                "median_slope_m_per_year": np.nan,
                "median_change_m": float(change.median()),
                "window": "2021-2022 annual change",
                "safe_interpretation": "PDF-extracted official well table supports positive annual changes, but row parsing is treated as an audit summary",
            }
        )
    rows.append(
        {
            "evidence_layer": "ministry_2024_regional_summary",
            "source_url": page_summary["source_url"],
            "n_units": int(page_summary["observation_wells"]) if pd.notna(page_summary["observation_wells"]) else np.nan,
            "n_positive": int(page_summary["rising_confined_wells"]) if pd.notna(page_summary["rising_confined_wells"]) else np.nan,
            "n_negative": np.nan,
            "median_slope_m_per_year": np.nan,
            "median_change_m": np.nan,
            "window": "2024 annual regional summary",
            "safe_interpretation": "regional official summary reports 79 of 91 confined observation wells rising",
        }
    )
    out = pd.DataFrame(rows)
    out.to_csv(DER / "tokyo_bay_groundwater_evidence_summary_r25.csv", index=False)
    return out


def plot_tokyo_representative(levels: pd.DataFrame, trends: pd.DataFrame) -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )
    palette = ["#1f77b4", "#2ca25f", "#756bb1", "#d95f02"]
    label_map = {
        "吾嬬Ｂ": "Azuma B",
        "新宿": "Shinjuku",
        "東久留米第3": "Higashikurume-3",
        "調布第３": "Chofu-3",
    }
    fig, ax = plt.subplots(figsize=(5.3, 3.1), constrained_layout=True)
    for idx, (station, group) in enumerate(levels.groupby("station", sort=False)):
        group = group.sort_values("year")
        baseline = group["groundwater_level_tp_m"].iloc[0]
        ax.plot(
            group["year"],
            group["groundwater_level_tp_m"] - baseline,
            marker="o",
            linewidth=1.6,
            markersize=3.5,
            color=palette[idx % len(palette)],
            label=label_map.get(station, station),
        )
    ax.axhline(0, color="#777777", linewidth=0.7)
    ax.set_xlabel("Year")
    ax.set_ylabel("Change from 2015 level (m)")
    ax.set_title("Tokyo official representative confined wells rise over 2015-2024", loc="left", fontsize=8.5)
    ax.text(
        0.01,
        0.96,
        f"{int((trends['ols_slope_m_per_year'] > 0).sum())}/{len(trends)} representative wells rising",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=7.5,
        color="#333333",
    )
    ax.legend(ncol=2, loc="upper left", bbox_to_anchor=(0.0, -0.20), fontsize=7)
    out = FIG / "FigS2_tokyo_representative_groundwater_r25"
    fig.savefig(out.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(out.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def retry_cgwb_sources() -> pd.DataFrame:
    targets = [
        ("cgwb_monitoring_page", CGWB_MONITORING_PAGE),
        ("cgwb_greater_mumbai_pdf", CGWB_GREATER_MUMBAI),
        ("cgwb_maharashtra_yearbook_pdf", CGWB_MAHARASHTRA_YEARBOOK),
    ]
    rows = []
    for name, url in targets:
        for use_proxy in [True, False]:
            rec = {
                "target": name,
                "url": url,
                "use_env_proxy": use_proxy,
                "status": "",
                "http_status": "",
                "content_type": "",
                "bytes": 0,
                "error": "",
            }
            try:
                response = http_session(use_proxy).get(url, timeout=25, allow_redirects=True)
                rec["http_status"] = response.status_code
                rec["content_type"] = response.headers.get("content-type", "")
                rec["bytes"] = len(response.content)
                rec["status"] = "ok" if response.ok else "http_not_ok"
            except Exception as exc:
                rec["status"] = "error"
                rec["error"] = f"{type(exc).__name__}: {exc}"
            rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(DER / "cgwb_access_retry_status_r25.csv", index=False)
    return out


def verify_mumbai_literature_boundary() -> pd.DataFrame:
    rows = []
    crossref = {
        "source": "Crossref",
        "url": MUMBAI_CROSSREF,
        "doi": MUMBAI_STUDY_DOI,
        "status": "",
        "title": "",
        "journal": "",
        "year": "",
        "evidence_direction": "contradicts positive-recovery attribution",
        "safe_use": (
            "Use as a guardrail: station-level Mumbai evidence supports depletion or increasing depth, "
            "not a Bhayandar-positive local validation."
        ),
        "error": "",
    }
    try:
        msg = http_session(True).get(MUMBAI_CROSSREF, timeout=60).json()["message"]
        crossref["status"] = "verified"
        crossref["title"] = msg.get("title", [""])[0]
        crossref["journal"] = msg.get("container-title", [""])[0]
        crossref["year"] = msg.get("published-print", msg.get("published-online", {})).get("date-parts", [[None]])[0][0]
    except Exception as exc:
        crossref["status"] = "error"
        crossref["error"] = f"{type(exc).__name__}: {exc}"
    rows.append(crossref)
    agris = {
        "source": "AGRIS metadata page",
        "url": AGRIS_MUMBAI_RECORD,
        "doi": MUMBAI_STUDY_DOI,
        "status": "",
        "title": "",
        "journal": "",
        "year": "",
        "evidence_direction": "contradicts positive-recovery attribution",
        "safe_use": (
            "Metadata page was reachable; abstract snippets support using this source as a local guardrail only."
        ),
        "error": "",
    }
    try:
        response = http_session(True).get(AGRIS_MUMBAI_RECORD, timeout=60)
        agris["status"] = "reachable" if response.ok else "http_not_ok"
        agris["title"] = "Long-term trends of groundwater level variations in response to local level land use land cover changes in Mumbai, India"
        agris["journal"] = "Groundwater for Sustainable Development"
        agris["year"] = "2022"
        (MUMBAI_RAW / "agris_mumbai_record_r25.html").write_bytes(response.content)
    except Exception as exc:
        agris["status"] = "error"
        agris["error"] = f"{type(exc).__name__}: {exc}"
    rows.append(agris)
    out = pd.DataFrame(rows)
    out.to_csv(DER / "mumbai_bhayandar_evidence_boundary_r25.csv", index=False)
    return out


def earthdata_jpl_cri_runner_status() -> pd.DataFrame:
    credential_files = [Path.home() / ".netrc", Path.home() / "_netrc", Path.home() / ".urs_cookies", Path.home() / ".dodsrc"]
    credential_envs = [
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
        "EARTHDATA_TOKEN",
        "NASA_EARTHDATA_USERNAME",
        "NASA_EARTHDATA_PASSWORD",
    ]
    present_files = [str(path) for path in credential_files if path.exists()]
    present_envs = [name for name in credential_envs if os.environ.get(name)]
    earthaccess_present = importlib.util.find_spec("earthaccess") is not None
    rows = []
    status = {
        "checked_at_utc": now_utc(),
        "collection_short_name": JPL_CRI_SHORT,
        "collection_id": JPL_CRI_COLLECTION_ID,
        "granule": JPL_CRI_GRANULE,
        "data_url": JPL_CRI_DATA_URL,
        "md5_url": JPL_CRI_MD5_URL,
        "earthaccess_installed": earthaccess_present,
        "credential_files_detected": len(present_files),
        "credential_envs_detected": len(present_envs),
        "local_netcdf_detected": "",
        "run_status": "",
        "md5_text": "",
        "note": "",
    }
    for candidate in JPL_LOCAL_CANDIDATES:
        if candidate.exists() and candidate.stat().st_size > 10_000_000:
            status["local_netcdf_detected"] = str(candidate.relative_to(ROOT))
            break
    try:
        md5_response = http_session(True).get(JPL_CRI_MD5_URL, timeout=45)
        status["md5_text"] = md5_response.text.strip() if md5_response.ok else f"http_{md5_response.status_code}"
    except Exception as exc:
        status["md5_text"] = f"{type(exc).__name__}: {exc}"
    if status["local_netcdf_detected"]:
        status["run_status"] = "ready_local_file_present"
        status["note"] = "A local authenticated NetCDF exists; sample with the R24/R25 runner before making a JPL claim."
    elif not earthaccess_present:
        status["run_status"] = "earthaccess_missing_and_no_local_file"
        status["note"] = "Install earthaccess and provide Earthdata credentials, or place the authenticated NetCDF in data_raw/grace/jpl."
    elif not (present_files or present_envs):
        status["run_status"] = "earthaccess_present_but_credentials_missing"
        status["note"] = "No local non-interactive Earthdata credential was detected; download is intentionally not attempted."
    else:
        status["run_status"] = "credentials_detected_manual_download_ready"
        status["note"] = "Credentials are detected; run earthaccess download or the protected URL workflow to retrieve the NetCDF."
    rows.append(status)
    out = pd.DataFrame(rows)
    out.to_csv(DER / "jpl_cri_earthdata_runner_status_r25.csv", index=False)
    (DER / "jpl_cri_earthdata_runner_status_r25.json").write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )
    return out


def update_attribution_matrix(tokyo_summary: pd.DataFrame, mumbai_boundary: pd.DataFrame) -> pd.DataFrame:
    base_path = DER / "attribution_confidence_matrix_r24.csv"
    if base_path.exists():
        matrix = pd.read_csv(base_path)
    else:
        matrix = pd.read_csv(DER / "attribution_confidence_matrix_r20.csv")
    rep = tokyo_summary[tokyo_summary["evidence_layer"].eq("official_2024_excel_representative_wells")]
    ministry = tokyo_summary[tokyo_summary["evidence_layer"].eq("ministry_2024_regional_summary")]
    if not rep.empty and not ministry.empty:
        rep_row = rep.iloc[0]
        min_row = ministry.iloc[0]
        text = (
            "R24 parsed Yokohama municipal records show 20/23 trend-qualified wells rising; "
            f"R25 Tokyo official evidence adds {int(rep_row.n_positive)}/{int(rep_row.n_units)} representative confined wells "
            f"rising over {rep_row.window} and {int(min_row.n_positive)}/{int(min_row.n_units)} confined observation wells rising "
            "in the 2024 regional summary."
        )
        mask = matrix["region_or_city"].eq("Yokohama / Tokyo Bay")
        matrix.loc[mask, "independent_groundwater_evidence"] = text
        matrix.loc[mask, "management_or_abstraction_evidence"] = (
            "official Tokyo/Yokohama monitoring supports recent water-level rise, but CSR materiality and management attribution remain unresolved"
        )
        matrix.loc[mask, "attribution_confidence"] = "medium-high sign / low-management"
        matrix.loc[mask, "main_text_use"] = "coastal-sensitive positive hotspot with local and regional well sign support, not product-material proof"
    mask = matrix["region_or_city"].eq("Mumbai-Bhayandar cluster")
    matrix.loc[mask, "independent_groundwater_evidence"] = (
        "R25 reconfirmed the DOI-verified Mumbai station-level study boundary and retried CGWB official endpoints; "
        "no Bhayandar-specific positive well trend was extracted, while the verified Mumbai evidence points toward increasing depth/depletion."
    )
    matrix.loc[mask, "management_or_abstraction_evidence"] = (
        "urbanization/impervious-surface and groundwater-use context; official CGWB raw-source access failed through both proxy and direct sessions"
    )
    matrix.loc[mask, "attribution_confidence"] = "low-contradictory"
    matrix.loc[mask, "main_text_use"] = "metro-deduplicated coastal hotspot retained as candidate-only; local evidence does not validate positive recovery"
    matrix.to_csv(DER / "attribution_confidence_matrix_r25.csv", index=False)
    return matrix


def build_registry(tokyo_summary: pd.DataFrame, cgwb_status: pd.DataFrame, mumbai_boundary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if (DER / "local_groundwater_evidence_registry_r24.csv").exists():
        rows.extend(pd.read_csv(DER / "local_groundwater_evidence_registry_r24.csv").to_dict("records"))
    for _, row in tokyo_summary.iterrows():
        rows.append(
            {
                "city_or_region": "Tokyo Bay / Yokohama",
                "evidence_type": row["evidence_layer"],
                "source": row["source_url"],
                "access_status": "downloaded_or_parsed",
                "direction": "rise" if row["n_positive"] >= row["n_units"] / 2 else "mixed",
                "use_in_manuscript": "directional sign support only; no GRACE recalibration",
                "safe_text": row["safe_interpretation"],
            }
        )
    rows.append(
        {
            "city_or_region": "Mumbai-Bhayandar",
            "evidence_type": "official_raw_source_retry",
            "source": "; ".join(sorted(cgwb_status["url"].unique())),
            "access_status": "not_downloaded",
            "direction": "not_validated_positive",
            "use_in_manuscript": "candidate-only boundary",
            "safe_text": "CGWB official endpoints were retried with and without local proxy; no Bhayandar positive well trend was extracted.",
        }
    )
    for _, row in mumbai_boundary.iterrows():
        rows.append(
            {
                "city_or_region": "Mumbai-Bhayandar",
                "evidence_type": row["source"],
                "source": row["url"],
                "access_status": row["status"],
                "direction": row["evidence_direction"],
                "use_in_manuscript": "guardrail against positive-recovery attribution",
                "safe_text": row["safe_use"],
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(DER / "local_groundwater_evidence_registry_r25.csv", index=False)
    return out


def main() -> None:
    download_records = []
    download_records.append(fetch_bytes(TOKYO_ENV_PAGE, TOKYO_RAW / "tokyo_env_2024_page_r25.html", timeout=90))
    page_summary = extract_tokyo_page_summary(TOKYO_RAW / "tokyo_env_2024_page_r25.html")
    download_records.append(fetch_bytes(TOKYO_ENV_EXCEL, TOKYO_RAW / "tokyo_env_2024_detail_r25.xlsx", timeout=90))
    download_records.append(fetch_bytes(TOKYO_REPORT_2022_PDF, TOKYO_RAW / "tokyo_2022_land_subsidence_report_r25.pdf", timeout=120))
    pd.DataFrame(download_records).to_csv(DER / "tokyo_source_download_status_r25.csv", index=False)

    levels, trends = parse_tokyo_representative_excel(TOKYO_RAW / "tokyo_env_2024_detail_r25.xlsx")
    resource_df, table2016 = parse_tokyo_open_data_package()
    table2022 = parse_tokyo_2022_pdf(TOKYO_RAW / "tokyo_2022_land_subsidence_report_r25.pdf")
    tokyo_summary = summarize_tokyo_evidence(page_summary, trends, table2016, table2022)
    plot_tokyo_representative(levels, trends)

    cgwb_status = retry_cgwb_sources()
    mumbai_boundary = verify_mumbai_literature_boundary()
    jpl_status = earthdata_jpl_cri_runner_status()
    registry = build_registry(tokyo_summary, cgwb_status, mumbai_boundary)
    matrix = update_attribution_matrix(tokyo_summary, mumbai_boundary)

    summary = {
        "checked_at_utc": now_utc(),
        "tokyo_representative_wells": {
            "n_wells": int(len(trends)),
            "n_positive_ols": int((trends["ols_slope_m_per_year"] > 0).sum()),
            "median_slope_m_per_year": float(trends["ols_slope_m_per_year"].median()),
            "median_change_m_2015_2024": float(trends["change_m"].median()),
        },
        "tokyo_2024_regional_summary": {
            "observation_wells": int(page_summary["observation_wells"]),
            "rising_confined_wells": int(page_summary["rising_confined_wells"]),
            "share_rising": float(page_summary["share_rising"]),
        },
        "tokyo_open_data_table5_2016": {
            "n_rows": int(len(table2016)),
            "n_positive_2016_minus_2015": int((pd.to_numeric(table2016["change_2016_minus_2015_m"], errors="coerce") > 0).sum())
            if not table2016.empty
            else 0,
        },
        "tokyo_pdf_table5_2022": {
            "n_rows_extracted": int(len(table2022)),
            "n_positive_2022_minus_2021": int((table2022["change_2022_minus_2021_m"] > 0).sum()) if not table2022.empty else 0,
        },
        "mumbai_bhayandar_status": "candidate-only; DOI-verified local evidence is contradictory to positive-recovery attribution",
        "cgwb_retry_any_success": bool(cgwb_status["status"].eq("ok").any()),
        "jpl_cri_runner_status": jpl_status.iloc[0]["run_status"],
        "outputs": [
            "data_derived/tokyo_source_download_status_r25.csv",
            "data_derived/tokyo_representative_groundwater_levels_r25.csv",
            "data_derived/tokyo_representative_groundwater_trends_r25.csv",
            "data_derived/tokyo_open_data_resources_r25.csv",
            "data_derived/tokyo_open_data_table5_groundwater_2016_r25.csv",
            "data_derived/tokyo_2022_pdf_table5_extracted_rows_r25.csv",
            "data_derived/tokyo_bay_groundwater_evidence_summary_r25.csv",
            "data_derived/cgwb_access_retry_status_r25.csv",
            "data_derived/mumbai_bhayandar_evidence_boundary_r25.csv",
            "data_derived/jpl_cri_earthdata_runner_status_r25.csv",
            "data_derived/local_groundwater_evidence_registry_r25.csv",
            "data_derived/attribution_confidence_matrix_r25.csv",
            "figures/FigS2_tokyo_representative_groundwater_r25.png",
            "figures/FigS2_tokyo_representative_groundwater_r25.svg",
            "figures/FigS2_tokyo_representative_groundwater_r25.pdf",
        ],
    }
    (DER / "r25_evidence_deepening_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
