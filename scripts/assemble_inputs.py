"""Assemble Zhu-2017 input layers at each cohort city (real data only).

For every city in city_cohort_hazard.csv attach:
  vs30   (m/s)  - USGS global slope-based Vs30 (Wald & Allen 2007)
  precip (mm/yr)- WorldClim 2.1 bio12 annual precipitation
  wtd    (m)    - Fan, Li & Miguez-Macho 2013 baseline water-table depth
  dw     (km)   - min geodesic distance to coastline / major river (Natural Earth 10m)
  pgv    (cm/s) - from GEM PGA_475 via documented conversion (zhu2017.pga_to_pgv)

Output: data_derived/city_inputs.csv  (+ coverage report).
Provenance for every field is in docs/00_DESIGN_BRIEF_v2.md §5.
"""
from __future__ import annotations
import sys, zipfile, glob
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw"; DER = ROOT / "data_derived"
sys.path.insert(0, str(ROOT / "scripts"))
from zhu2017 import pga_to_pgv

R_EARTH_KM = 6371.0

def lonlat_to_xyz(lon, lat):
    lon = np.radians(np.asarray(lon, float)); lat = np.radians(np.asarray(lat, float))
    return np.column_stack([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])

def sample_raster(path, lons, lats, band=1):
    import rasterio
    with rasterio.open(path) as ds:
        nod = ds.nodata
        vals = np.array([v[band-1] for v in ds.sample(list(zip(lons, lats)), indexes=[band])], float)
    if nod is not None:
        vals = np.where(vals == nod, np.nan, vals)
    return vals

def find_vs30_raster():
    z = RAW / "global_vs30.grd.zip"
    direct = list(RAW.glob("global_vs30*.grd")) + list(RAW.glob("*vs30*.tif"))
    if direct:
        return direct[0]
    if z.exists():
        # is it a zip or a raw grd mislabeled?
        with open(z, "rb") as fh:
            magic = fh.read(4)
        if magic[:2] == b"PK":
            zipfile.ZipFile(z).extractall(RAW / "vs30")
            cand = list((RAW / "vs30").rglob("*.grd")) + list((RAW / "vs30").rglob("*.tif"))
            return cand[0] if cand else None
        else:
            g = RAW / "global_vs30.grd"
            if not g.exists():
                g.write_bytes(z.read_bytes())
            return g
    return None

def sample_wtd(lons, lats):
    """Fan, Li & Miguez-Macho (2013) annual-mean water-table depth.
    Files store variable 'WTD' (3D, time=1) in metres as NEGATIVE depth below
    surface (e.g. -2.5 = 2.5 m deep); -1000 = ocean/out-of-domain fill, with a
    companion 'mask' (1=valid). We return wtd in POSITIVE metres (Zhu convention)."""
    import xarray as xr
    lons = np.asarray(lons, float); lats = np.asarray(lats, float)
    files = sorted((RAW / "fan2013").glob("*_WTD_annualmean.nc"))
    out = np.full(len(lons), np.nan)
    for f in files:
        ds = xr.open_dataset(f, decode_times=False)
        wtd = ds["WTD"].squeeze(drop=True)        # (lat, lon), negative metres
        msk = ds["mask"].squeeze(drop=True)        # 1 = modelled domain, 0 = fill
        lo = ds["lon"].values; la = ds["lat"].values
        lo_min, lo_max, la_min, la_max = lo.min(), lo.max(), la.min(), la.max()
        inb = np.where(np.isnan(out) & (lons >= lo_min) & (lons <= lo_max)
                       & (lats >= la_min) & (lats <= la_max))[0]
        if inb.size == 0:
            ds.close(); continue
        xp = xr.DataArray(lons[inb], dims="pts"); yp = xr.DataArray(lats[inb], dims="pts")
        sel = np.asarray(wtd.sel(lon=xp, lat=yp, method="nearest").values, float)
        mval = np.asarray(msk.sel(lon=xp, lat=yp, method="nearest").values, float)
        valid = (mval > 0.5) & (sel > -999)        # modelled AND not ocean/fill
        out[inb] = np.where(valid, np.clip(-sel, 0.0, None), np.nan)  # flip sign -> positive depth
        ds.close()
    return out

def distance_to_water_km(lons, lats):
    import geopandas as gpd
    from scipy.spatial import cKDTree
    verts = []
    for name in ("ne_10m_coastline.zip", "ne_10m_rivers_lake_centerlines.zip"):
        p = RAW / "naturalearth" / name
        if not p.exists():
            continue
        g = gpd.read_file(f"zip://{p}")
        for geom in g.geometry:
            if geom is None:
                continue
            if geom.geom_type == "LineString":
                verts.extend(list(geom.coords))
            elif geom.geom_type == "MultiLineString":
                for ls in geom.geoms:
                    verts.extend(list(ls.coords))
    if not verts:
        return np.full(len(lons), np.nan)
    verts = np.array(verts)[:, :2]
    tree = cKDTree(lonlat_to_xyz(verts[:, 0], verts[:, 1]))
    cd, _ = tree.query(lonlat_to_xyz(lons, lats), k=1)  # chord distance on unit sphere
    arc = 2 * np.arcsin(np.clip(cd / 2, 0, 1))           # chord -> arc (radians)
    return arc * R_EARTH_KM

def main():
    df = pd.read_csv(DER / "city_cohort_hazard.csv")
    lons = df["lon"].values; lats = df["lat"].values
    report = {}

    vs30_path = find_vs30_raster()
    if vs30_path:
        print("Vs30 raster:", vs30_path)
        df["vs30"] = sample_raster(vs30_path, lons, lats)
    else:
        print("WARN: Vs30 not available yet"); df["vs30"] = np.nan
    report["vs30"] = int(df["vs30"].notna().sum())

    bio12 = RAW / "wc2.1_10m_bio" / "wc2.1_10m_bio_12.tif"
    if not bio12.exists():
        zf = RAW / "wc2.1_10m_bio.zip"
        if zf.exists():
            zipfile.ZipFile(zf).extractall(RAW / "wc2.1_10m_bio")
    if bio12.exists():
        df["precip"] = sample_raster(bio12, lons, lats)
    else:
        print("WARN: precip not available"); df["precip"] = np.nan
    report["precip"] = int(df["precip"].notna().sum())

    df["wtd"] = sample_wtd(lons, lats)
    report["wtd"] = int(df["wtd"].notna().sum())

    df["dw_km"] = distance_to_water_km(lons, lats)
    report["dw_km"] = int(df["dw_km"].notna().sum())

    df["pgv"] = pga_to_pgv(df["pga_475_g"].values)  # default k=100 cm/s per g

    out = DER / "city_inputs.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"\nWrote {out}  ({len(df)} cities)")
    print("Coverage (non-NaN):", report, f"of {len(df)}")
    for col in ["vs30", "precip", "wtd", "dw_km", "pgv"]:
        s = df[col].dropna()
        if len(s):
            print(f"  {col:<8} min={s.min():.2f} med={s.median():.2f} max={s.max():.2f}")

if __name__ == "__main__":
    main()
