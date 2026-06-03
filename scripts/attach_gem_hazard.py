"""Download GEM Global Seismic Hazard Map v2023.1 (PGA 475-yr, rock) and attach
real PGA to each cohort city. Real, open data (CC-BY-NC-SA), Zenodo 10.5281/zenodo.8409647.

Output: data_derived/city_cohort_hazard.csv  (cohort + pga_475_g + seismic flag)
"""
from __future__ import annotations
import io, ssl, sys, urllib.request, zipfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw"; DER = ROOT / "data_derived"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
URL = "https://zenodo.org/api/records/8409647/files/GEM-GSHM_PGA-475y-rock_v2023.zip/content"
PGA_MIN = 0.05  # g; below this, liquefaction triggering is negligible

def fetch_zip():
    local = RAW / "GEM-GSHM_PGA-475y-rock_v2023.zip"
    if local.exists() and local.stat().st_size > 10_000_000:
        print("using cached", local); return local
    print("downloading GEM hazard map ...")
    req = urllib.request.Request(URL, headers={"User-Agent": "research/1.0"})
    data = urllib.request.urlopen(req, timeout=180, context=CTX).read()
    local.write_bytes(data); print(f"  {len(data)/1e6:.1f} MB -> {local}")
    return local

def extract_raster(zip_path: Path) -> Path:
    zf = zipfile.ZipFile(zip_path)
    names = zf.namelist()
    print("zip contents:", names)
    raster = [n for n in names if n.lower().endswith((".tif", ".tiff", ".geotiff"))]
    if not raster:
        raster = [n for n in names if n.lower().endswith((".asc", ".flt", ".vrt"))]
    if not raster:
        raise SystemExit(f"no raster found in zip: {names}")
    target = RAW / Path(raster[0]).name
    # extract all (some rasters need sidecar files)
    zf.extractall(RAW / "gem_hazard")
    found = list((RAW / "gem_hazard").rglob(Path(raster[0]).name))
    print("raster:", found[0])
    return found[0]

def main():
    import rasterio
    zip_path = fetch_zip()
    raster = extract_raster(zip_path)
    df = pd.read_csv(DER / "city_cohort_raw.csv")
    with rasterio.open(raster) as ds:
        print(f"raster CRS={ds.crs}, shape={ds.shape}, bounds={ds.bounds}, nodata={ds.nodata}")
        coords = list(zip(df["lon"].values, df["lat"].values))
        vals = [v[0] for v in ds.sample(coords)]
    df["pga_475_g"] = [float(v) if v is not None else float("nan") for v in vals]
    # clean nodata
    nod = []
    import numpy as np
    df["pga_475_g"] = df["pga_475_g"].replace([ -9999, -999, 1e20 ], np.nan)
    df.loc[df["pga_475_g"] < 0, "pga_475_g"] = np.nan
    df["seismic"] = df["pga_475_g"] >= PGA_MIN
    out = DER / "city_cohort_hazard.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    n_seis = int(df["seismic"].sum())
    print(f"\nAttached PGA to {len(df)} cities -> {out}")
    print(f"Seismically relevant (PGA_475 >= {PGA_MIN} g): {n_seis}/{len(df)}")
    print(f"PGA stats (g): min={df['pga_475_g'].min():.3f}, median={df['pga_475_g'].median():.3f}, "
          f"p90={df['pga_475_g'].quantile(0.9):.3f}, max={df['pga_475_g'].max():.3f}")
    top = df.sort_values("pga_475_g", ascending=False).head(12)
    print("\nHighest-hazard cohort cities:")
    for _, r in top.iterrows():
        print(f"  {r['name']:<18} {r['country']:<3} PGA_475={r['pga_475_g']:.3f} g  pop={int(r['population']):,}")

if __name__ == "__main__":
    main()
