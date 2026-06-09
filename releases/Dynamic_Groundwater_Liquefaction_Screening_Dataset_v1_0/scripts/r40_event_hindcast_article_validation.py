"""R40 event-inventory benchmark for the Nature Water Article route.

This script adds an Article-facing historical-event benchmark without
overclaiming it as site-scale engineering validation.

Design:
1. Download public USGS ScienceBase liquefaction inventories for GRACE-era
   events with accessible observed features.
2. Download the corresponding USGS ground-failure Zhu et al. event rasters.
3. Treat the USGS Zhu raster as the static event screen.
4. Apply a pre-event CSR GRACE/GRACE-FO storage anomaly only through the
   Zhu water-table coefficient and compare static vs dynamic scores.

Controls:
- Puerto Rico uses the published null-points where available.
- Tohoku, Wenchuan and Nepal use clearly labelled pseudo-controls sampled from
  valid raster cells outside buffered observed liquefaction features.

The output is a benchmark/feasibility diagnostic for the Article claim that
dynamic groundwater information can be plugged into event screens. It is not
a complete liquefaction inventory validation, not a damage model and not an
engineering replacement for CPT/SPT or local groundwater data.
"""
from __future__ import annotations

import json
import math
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import requests
import xarray as xr
from rasterio.transform import xy as raster_xy
from shapely.geometry import Point
from sklearn.metrics import roc_auc_score


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw" / "event_hindcast_r40"
DER = ROOT / "data_derived"
FIG = ROOT / "figures"
CSR_PATH = ROOT / "data_raw" / "grace" / "CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc"
USGS_MODEL_DIR = RAW / "usgs_ground_failure_models"

WTD_COEF = -0.0333
SY_DEFAULT = 0.10
RNG = np.random.default_rng(20260609)


@dataclass(frozen=True)
class EventSpec:
    event_key: str
    event_title: str
    event_id: str
    event_date_utc: str
    inventory_item: str
    inventory_zip_name: str
    inventory_shp_rel: str
    inventory_url: str
    positive_mode: str
    null_item: str = ""
    null_zip_name: str = ""
    null_shp_rel: str = ""
    null_url: str = ""


EVENTS = [
    EventSpec(
        event_key="tohoku_2011",
        event_title="2011 Tohoku, Japan M9.1",
        event_id="official20110311054624120_30",
        event_date_utc="2011-03-11T05:46:24Z",
        inventory_item="5f3c2b5082ce8df5b6c647fe",
        inventory_zip_name="Tohoku_MLITT_2011.zip",
        inventory_shp_rel="Tohoku_MLITT_2011/MLITT_2011.shp",
        inventory_url="https://www.sciencebase.gov/catalog/file/get/5f3c2b5082ce8df5b6c647fe?name=MLITT_2011.zip",
        positive_mode="polygon_representative_points",
    ),
    EventSpec(
        event_key="wenchuan_2008",
        event_title="2008 Wenchuan, China M7.9",
        event_id="usp000g650",
        event_date_utc="2008-05-12T06:28:01Z",
        inventory_item="5f3c2a0082ce8df5b6c647ca",
        inventory_zip_name="Wenchuan_Cao_2010.zip",
        inventory_shp_rel="Wenchuan_Cao_2010/Cao_et_al_2010.shp",
        inventory_url="https://www.sciencebase.gov/catalog/file/get/5f3c2a0082ce8df5b6c647ca?name=Cao_et_al_2010.zip",
        positive_mode="points",
    ),
    EventSpec(
        event_key="nepal_2015",
        event_title="2015 Gorkha, Nepal M7.8",
        event_id="us20002926",
        event_date_utc="2015-04-25T06:11:25Z",
        inventory_item="5f3c2ce182ce8df5b6c64835",
        inventory_zip_name="Nepal_Moss_2015.zip",
        inventory_shp_rel="Nepal_Moss_2015/Moss_2015.shp",
        inventory_url="https://www.sciencebase.gov/catalog/file/get/5f3c2ce182ce8df5b6c64835?name=Moss_2015.zip",
        positive_mode="points",
    ),
    EventSpec(
        event_key="puerto_rico_2020",
        event_title="2020 Puerto Rico M6.4",
        event_id="us70006vll",
        event_date_utc="2020-01-07T08:24:26Z",
        inventory_item="61155d18d34ef38cf11d4ae7",
        inventory_zip_name="PR_liquefaction_points_20210913.zip",
        inventory_shp_rel="PR_liquefaction_points_20210913/liquefaction_points_20210913.shp",
        inventory_url="https://www.sciencebase.gov/catalog/file/get/61155d18d34ef38cf11d4ae7?name=liquefaction_points_20210913.zip",
        positive_mode="points",
        null_item="61155d18d34ef38cf11d4ae7",
        null_zip_name="PR_liquefaction_nullpoints_20210913.zip",
        null_shp_rel="PR_liquefaction_nullpoints_20210913/liquefaction_nullpoints_20210913.shp",
        null_url="https://www.sciencebase.gov/catalog/file/get/61155d18d34ef38cf11d4ae7?name=liquefaction_nullpoints_20210913.zip",
    ),
]


def ensure_dirs() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    DER.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    USGS_MODEL_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, min_bytes: int = 100, attempts: int = 5) -> str:
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return "cached"
    session = requests.Session()
    session.headers.update({"User-Agent": "IMUT-Codex-R40-event-hindcast/1.0"})
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, timeout=120)
            if response.ok and len(response.content) >= min_bytes:
                dest.write_bytes(response.content)
                return f"downloaded_attempt_{attempt}"
            last_error = f"http_{response.status_code}_bytes_{len(response.content)}"
        except Exception as exc:  # pragma: no cover - network variability
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(1.5 * attempt)
    raise RuntimeError(f"failed to download {url}: {last_error}")


def unzip_if_needed(zip_path: Path, out_dir: Path) -> None:
    marker = out_dir / ".unzipped"
    if marker.exists():
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def event_product(event_id: str) -> dict:
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&eventid={event_id}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    products = response.json()["properties"]["products"].get("ground-failure", [])
    if not products:
        raise RuntimeError(f"no ground-failure product for {event_id}")
    # The first product is the preferred/current product in the USGS event feed.
    return products[0]


def ensure_event_inputs() -> list[dict]:
    registry = []
    for spec in EVENTS:
        zip_path = RAW / spec.inventory_zip_name
        status = download_file(spec.inventory_url, zip_path, min_bytes=500)
        if zip_path.read_bytes()[:2] != b"PK":
            raise RuntimeError(f"{zip_path} is not a zip file")
        unzip_if_needed(zip_path, RAW / spec.inventory_zip_name.replace(".zip", ""))

        null_status = ""
        if spec.null_url:
            null_zip = RAW / spec.null_zip_name
            null_status = download_file(spec.null_url, null_zip, min_bytes=500)
            if null_zip.read_bytes()[:2] != b"PK":
                raise RuntimeError(f"{null_zip} is not a zip file")
            unzip_if_needed(null_zip, RAW / spec.null_zip_name.replace(".zip", ""))

        product = event_product(spec.event_id)
        contents = product["contents"]
        model_url = contents["zhu_2017_general_model.tif"]["url"]
        model_path = USGS_MODEL_DIR / f"{spec.event_id}_zhu_2017_general_model.tif"
        model_status = download_file(
            model_url,
            model_path,
            min_bytes=int(contents["zhu_2017_general_model.tif"].get("length", 1000)),
        )
        info_url = contents["info.json"]["url"]
        info_path = USGS_MODEL_DIR / f"{spec.event_id}_info.json"
        info_status = download_file(info_url, info_path, min_bytes=200)
        registry.append(
            {
                "event_key": spec.event_key,
                "event_title": spec.event_title,
                "event_id": spec.event_id,
                "event_date_utc": spec.event_date_utc,
                "inventory_item": spec.inventory_item,
                "inventory_zip": str(zip_path.relative_to(ROOT)),
                "inventory_status": status,
                "null_zip": str((RAW / spec.null_zip_name).relative_to(ROOT)) if spec.null_zip_name else "",
                "null_status": null_status,
                "usgs_ground_failure_product_code": product.get("code", ""),
                "model_raster": str(model_path.relative_to(ROOT)),
                "model_status": model_status,
                "info_json": str(info_path.relative_to(ROOT)),
                "info_status": info_status,
                "control_design": "published_nullpoints" if spec.null_url else "pseudo-controls outside buffered inventory",
            }
        )
    return registry


def read_positive_points(spec: EventSpec) -> gpd.GeoDataFrame:
    shp = RAW / spec.inventory_zip_name.replace(".zip", "") / Path(spec.inventory_shp_rel).name
    # Some archives extract files directly inside the output directory; fall back
    # to the declared relative path for future zip layouts.
    if not shp.exists():
        shp = RAW / spec.inventory_shp_rel
    gdf = gpd.read_file(shp)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs("EPSG:4326")
    if spec.positive_mode == "polygon_representative_points":
        geometry = gdf.geometry.representative_point()
    else:
        geometry = gdf.geometry
    out = gpd.GeoDataFrame(
        {
            "event_key": [spec.event_key] * len(gdf),
            "event_title": [spec.event_title] * len(gdf),
            "sample_role": ["observed_liquefaction"] * len(gdf),
            "label": [1] * len(gdf),
            "control_design": ["observed_inventory"] * len(gdf),
            "source_feature_count": [len(gdf)] * len(gdf),
        },
        geometry=geometry,
        crs="EPSG:4326",
    )
    return out


def read_null_points(spec: EventSpec) -> gpd.GeoDataFrame | None:
    if not spec.null_shp_rel:
        return None
    shp = RAW / spec.null_zip_name.replace(".zip", "") / Path(spec.null_shp_rel).name
    if not shp.exists():
        shp = RAW / spec.null_shp_rel
    gdf = gpd.read_file(shp)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    gdf = gdf.to_crs("EPSG:4326")
    return gpd.GeoDataFrame(
        {
            "event_key": [spec.event_key] * len(gdf),
            "event_title": [spec.event_title] * len(gdf),
            "sample_role": ["published_nullpoint"] * len(gdf),
            "label": [0] * len(gdf),
            "control_design": ["published_nullpoints"] * len(gdf),
            "source_feature_count": [len(gdf)] * len(gdf),
        },
        geometry=gdf.geometry,
        crs="EPSG:4326",
    )


def raster_static_values(tif_path: Path, points: gpd.GeoDataFrame) -> np.ndarray:
    with rasterio.open(tif_path) as src:
        coords = [(geom.x, geom.y) for geom in points.geometry]
        values = np.array([v[0] for v in src.sample(coords)], dtype=float)
        nodata = src.nodata
    if nodata is not None:
        values[values == nodata] = np.nan
    values[(values < 0) | (values > 1)] = np.nan
    return values


def pseudo_controls(spec: EventSpec, positives: gpd.GeoDataFrame, n_controls: int) -> gpd.GeoDataFrame:
    tif_path = USGS_MODEL_DIR / f"{spec.event_id}_zhu_2017_general_model.tif"
    with rasterio.open(tif_path) as src:
        arr = src.read(1, masked=True)
        data = np.asarray(arr.filled(np.nan), dtype=float)
        valid = np.isfinite(data) & (data >= 0) & (data <= 1)
        positive_values = data[valid & (data > 0)]
        if len(positive_values) > 100:
            hard_threshold = float(np.quantile(positive_values, 0.80))
            hard = valid & (data >= hard_threshold)
        else:
            hard = valid
        rows, cols = np.where(hard)
        if len(rows) < n_controls:
            rows, cols = np.where(valid)
        take = min(max(n_controls * 5, n_controls), len(rows))
        idx = RNG.choice(len(rows), size=take, replace=False)
        xs, ys = raster_xy(src.transform, rows[idx], cols[idx], offset="center")

    candidates = gpd.GeoDataFrame(
        {
            "static_candidate_pool": ["top_valid_model_cells"] * len(xs),
        },
        geometry=[Point(float(x), float(y)) for x, y in zip(xs, ys)],
        crs="EPSG:4326",
    )
    positives_m = positives.to_crs("EPSG:3857")
    candidates_m = candidates.to_crs("EPSG:3857")
    buffered = positives_m.geometry.buffer(10_000).union_all()
    keep = ~candidates_m.geometry.within(buffered)
    candidates = candidates.loc[keep.to_numpy()].copy()
    if len(candidates) < n_controls:
        candidates = candidates.copy()
    else:
        candidates = candidates.sample(n=n_controls, random_state=20260609)
    candidates["event_key"] = spec.event_key
    candidates["event_title"] = spec.event_title
    candidates["sample_role"] = "pseudo_control"
    candidates["label"] = 0
    candidates["control_design"] = "pseudo-controls outside buffered inventory; hard cells from upper static-probability background"
    candidates["source_feature_count"] = len(candidates)
    return candidates[["event_key", "event_title", "sample_role", "label", "control_design", "source_feature_count", "geometry"]]


def decode_csr_time(ds: xr.Dataset) -> pd.DatetimeIndex:
    units = ds["time"].attrs.get("Units") or ds["time"].attrs.get("units")
    if not units or "days since 2002-01-01" not in units:
        raise RuntimeError(f"unexpected CSR time units: {units}")
    return pd.DatetimeIndex(pd.Timestamp("2002-01-01T00:00:00Z") + pd.to_timedelta(ds["time"].values, unit="D"))


def csr_anomaly_sampler(ds: xr.Dataset):
    lat_values = ds["lat"].values
    lon_values = ds["lon"].values
    data = ds["lwe_thickness"]
    dates = decode_csr_time(ds)
    cache: dict[tuple[str, int, int], tuple[float, float, float, int, int]] = {}

    def event_indices(event_date: str) -> tuple[np.ndarray, np.ndarray]:
        event_ts = pd.Timestamp(event_date)
        pre_mask = (dates < event_ts) & (dates >= event_ts - pd.Timedelta(days=150))
        pre_idx = np.where(pre_mask)[0][-3:]
        if len(pre_idx) == 0:
            pre_idx = np.where(dates < event_ts)[0][-3:]
        baseline_mask = (dates < dates[pre_idx[0]]) & (dates >= event_ts - pd.Timedelta(days=730))
        baseline_idx = np.where(baseline_mask)[0]
        if len(baseline_idx) < 6:
            baseline_idx = np.where(dates < event_ts)[0]
        return pre_idx, baseline_idx

    def nearest_indices(lon: float, lat: float) -> tuple[int, int]:
        lon360 = lon % 360
        lat_i = int(np.abs(lat_values - lat).argmin())
        lon_i = int(np.abs(lon_values - lon360).argmin())
        return lat_i, lon_i

    def sample(event_date: str, lon: float, lat: float) -> tuple[float, float, float, int, int]:
        lat_i, lon_i = nearest_indices(lon, lat)
        key = (event_date, lat_i, lon_i)
        if key in cache:
            return cache[key]
        pre_idx, base_idx = event_indices(event_date)
        pre = np.asarray(data.isel(time=pre_idx, lat=lat_i, lon=lon_i).values, dtype=float)
        base = np.asarray(data.isel(time=base_idx, lat=lat_i, lon=lon_i).values, dtype=float)
        pre_mean = float(np.nanmean(pre))
        baseline = float(np.nanmedian(base))
        anomaly = pre_mean - baseline
        value = (anomaly, pre_mean, baseline, int(len(pre_idx)), int(len(base_idx)))
        cache[key] = value
        return value

    return sample


def expit(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def dynamic_probability(static_p: np.ndarray, anomaly_cm: np.ndarray, sy: float = SY_DEFAULT) -> np.ndarray:
    clipped = np.clip(static_p, 1e-6, 1 - 1e-6)
    logit = np.log(clipped / (1 - clipped))
    delta_wtd_m = -(anomaly_cm / 100.0) / sy
    dynamic_logit = logit + (WTD_COEF * delta_wtd_m)
    # WTD_COEF is negative in the Zhu model. Positive storage anomaly gives
    # negative delta_wtd_m and therefore increases the logit.
    return expit(dynamic_logit)


def brier(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))


def build_samples() -> tuple[pd.DataFrame, pd.DataFrame]:
    ds = xr.open_dataset(CSR_PATH)
    sample_csr = csr_anomaly_sampler(ds)
    all_samples = []
    registry_rows = ensure_event_inputs()

    for spec in EVENTS:
        positives = read_positive_points(spec)
        nulls = read_null_points(spec)
        if nulls is None:
            controls = pseudo_controls(spec, positives, max(len(positives), 40))
        else:
            controls = nulls
        gdf = pd.concat([positives, controls], ignore_index=True)
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
        tif_path = USGS_MODEL_DIR / f"{spec.event_id}_zhu_2017_general_model.tif"
        gdf["static_p"] = raster_static_values(tif_path, gdf)
        gdf = gdf[np.isfinite(gdf["static_p"])].copy()
        gdf["lon"] = gdf.geometry.x
        gdf["lat"] = gdf.geometry.y

        anomalies = [
            sample_csr(spec.event_date_utc, float(row.lon), float(row.lat))
            for row in gdf[["lon", "lat"]].itertuples(index=False)
        ]
        gdf["csr_pre_event_anomaly_cm"] = [v[0] for v in anomalies]
        gdf["csr_pre_event_mean_cm"] = [v[1] for v in anomalies]
        gdf["csr_recent_baseline_cm"] = [v[2] for v in anomalies]
        gdf["csr_pre_month_count"] = [v[3] for v in anomalies]
        gdf["csr_baseline_month_count"] = [v[4] for v in anomalies]
        gdf["dynamic_p_sy010"] = dynamic_probability(
            gdf["static_p"].to_numpy(dtype=float),
            gdf["csr_pre_event_anomaly_cm"].to_numpy(dtype=float),
            SY_DEFAULT,
        )
        gdf["delta_p_dynamic_minus_static"] = gdf["dynamic_p_sy010"] - gdf["static_p"]
        all_samples.append(gdf.drop(columns="geometry"))

    samples = pd.concat(all_samples, ignore_index=True)
    registry = pd.DataFrame(registry_rows)
    return samples, registry


def metrics_by_event(samples: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event_key, group in samples.groupby("event_key", sort=False):
        y = group["label"].to_numpy(dtype=int)
        static = group["static_p"].to_numpy(dtype=float)
        dynamic = group["dynamic_p_sy010"].to_numpy(dtype=float)
        control_design = "; ".join(sorted(set(group.loc[group["label"] == 0, "control_design"].astype(str))))
        if len(set(y)) < 2:
            static_auc = math.nan
            dynamic_auc = math.nan
        else:
            static_auc = float(roc_auc_score(y, static))
            dynamic_auc = float(roc_auc_score(y, dynamic))
        rows.append(
            {
                "event_key": event_key,
                "event_title": group["event_title"].iloc[0],
                "n_observed_liquefaction": int((group["label"] == 1).sum()),
                "n_controls": int((group["label"] == 0).sum()),
                "control_design": control_design,
                "static_auc": static_auc,
                "dynamic_auc_sy010": dynamic_auc,
                "delta_auc_dynamic_minus_static": dynamic_auc - static_auc
                if np.isfinite(dynamic_auc) and np.isfinite(static_auc)
                else math.nan,
                "static_brier": brier(y, static),
                "dynamic_brier_sy010": brier(y, dynamic),
                "delta_brier_dynamic_minus_static": brier(y, dynamic) - brier(y, static),
                "median_positive_storage_anomaly_cm": float(group.loc[group["label"] == 1, "csr_pre_event_anomaly_cm"].median()),
                "median_control_storage_anomaly_cm": float(group.loc[group["label"] == 0, "csr_pre_event_anomaly_cm"].median()),
                "median_positive_delta_p": float(group.loc[group["label"] == 1, "delta_p_dynamic_minus_static"].median()),
                "median_control_delta_p": float(group.loc[group["label"] == 0, "delta_p_dynamic_minus_static"].median()),
            }
        )
    return pd.DataFrame(rows)


def make_figure(metrics: pd.DataFrame, samples: pd.DataFrame) -> None:
    plot_metrics = metrics.copy()
    labels = [k.replace("_", " ").title().replace("Puerto Rico", "Puerto Rico") for k in plot_metrics["event_key"]]
    y = np.arange(len(plot_metrics))

    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.5), constrained_layout=True)
    ax = axes[0, 0]
    ax.barh(y - 0.17, plot_metrics["static_auc"], height=0.32, color="#7f8c8d", label="Static event screen")
    ax.barh(y + 0.17, plot_metrics["dynamic_auc_sy010"], height=0.32, color="#1f77b4", label="Dynamic groundwater update")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Case-control AUC")
    ax.set_title("a. Event-inventory discrimination")
    ax.legend(frameon=False, fontsize=8, loc="lower right")

    ax = axes[0, 1]
    colors = ["#2ca25f" if v >= 0 else "#de2d26" for v in plot_metrics["delta_auc_dynamic_minus_static"]]
    ax.barh(y, plot_metrics["delta_auc_dynamic_minus_static"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Dynamic - static AUC")
    ax.set_title("b. AUC change")

    ax = axes[1, 0]
    colors = ["#2ca25f" if v <= 0 else "#de2d26" for v in plot_metrics["delta_brier_dynamic_minus_static"]]
    ax.barh(y, plot_metrics["delta_brier_dynamic_minus_static"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Dynamic - static Brier score")
    ax.set_title("c. Calibration-loss change")

    ax = axes[1, 1]
    box_data = []
    box_labels = []
    for event_key, group in samples.groupby("event_key", sort=False):
        pos = group.loc[group["label"] == 1, "csr_pre_event_anomaly_cm"].dropna().to_numpy()
        con = group.loc[group["label"] == 0, "csr_pre_event_anomaly_cm"].dropna().to_numpy()
        box_data.extend([pos, con])
        box_labels.extend([event_key.split("_")[0] + "\nliq", event_key.split("_")[0] + "\nctrl"])
    bp = ax.boxplot(box_data, patch_artist=True, showfliers=False)
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor("#9ecae1" if i % 2 == 0 else "#fdd0a2")
        patch.set_edgecolor("#555555")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticklabels(box_labels, rotation=0, fontsize=7)
    ax.set_ylabel("Pre-event CSR storage anomaly (cm)")
    ax.set_title("d. Groundwater-state update used")

    fig.suptitle("Event-inventory benchmark for the dynamic groundwater update", fontsize=12, fontweight="bold")
    note = (
        "Positive points are public liquefaction inventories. Controls are published Puerto Rico nullpoints or labelled pseudo-controls for other events."
    )
    fig.text(0.01, -0.01, note, fontsize=7, color="#555555")

    for ext in ["png", "svg", "pdf"]:
        fig.savefig(FIG / f"Fig2_event_hindcast_article.{ext}", dpi=300 if ext == "png" else None)
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    samples, registry = build_samples()
    metrics = metrics_by_event(samples)

    samples.to_csv(DER / "event_hindcast_samples_r40.csv", index=False)
    registry.to_csv(DER / "event_hindcast_inventory_registry_r40.csv", index=False)
    metrics.to_csv(DER / "event_hindcast_metrics_r40.csv", index=False)

    summary = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_events_attempted": len(EVENTS),
        "n_events_with_metrics": int(metrics["static_auc"].notna().sum()),
        "n_total_positive_samples": int((samples["label"] == 1).sum()),
        "n_total_control_samples": int((samples["label"] == 0).sum()),
        "events": metrics[
            [
                "event_key",
                "n_observed_liquefaction",
                "n_controls",
                "control_design",
                "static_auc",
                "dynamic_auc_sy010",
                "delta_auc_dynamic_minus_static",
                "delta_brier_dynamic_minus_static",
            ]
        ].to_dict(orient="records"),
        "claim_boundary": (
            "R40 is an event-inventory benchmark using public observed liquefaction features, "
            "USGS Zhu event rasters and a CSR pre-event storage anomaly update. It is not "
            "site-specific engineering validation and pseudo-controls are labelled."
        ),
    }
    (DER / "event_hindcast_summary_r40.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    make_figure(metrics, samples)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
