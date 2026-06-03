"""Generic cached downloader for named real-data layers. Usage:
    python scripts/fetch.py <layer>
Layers: vs30 | worldclim_bio | dist2coast
Caches into data_raw/. Safe to re-run (skips if already present & nonempty).
"""
from __future__ import annotations
import ssl, sys, urllib.request, time
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data_raw"
RAW.mkdir(exist_ok=True)
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

LAYERS = {
    # name: (url, local_filename, min_expected_bytes)
    "vs30":          ("https://apps.usgs.gov/shakemap_geodata/vs30/global_vs30.grd", "global_vs30_grd.zip", 100_000_000),
    "worldclim_bio": ("https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_bio.zip", "wc2.1_10m_bio.zip", 5_000_000),
    "dist2coast":    ("https://oceancolor.gsfc.nasa.gov/images/dist2coast/dist2coast_4deg_v2.txt", "dist2coast_4deg.txt", 1_000_000),
}

def fetch(layer: str):
    if layer not in LAYERS:
        raise SystemExit(f"unknown layer {layer}; choices: {list(LAYERS)}")
    url, fn, minb = LAYERS[layer]
    local = RAW / fn
    if local.exists() and local.stat().st_size >= minb:
        print(f"[{layer}] cached {local} ({local.stat().st_size/1e6:.1f} MB)"); return local
    print(f"[{layer}] downloading {url}")
    t = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0 (academic; renlijian@imut.edu.cn)"})
    with urllib.request.urlopen(req, timeout=600, context=CTX) as r, local.open("wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk); total += len(chunk)
            if total % (50 << 20) < (1 << 20):
                print(f"   ... {total/1e6:.0f} MB", flush=True)
    print(f"[{layer}] done {total/1e6:.1f} MB in {time.time()-t:.0f}s -> {local}")
    return local

if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else "vs30")
