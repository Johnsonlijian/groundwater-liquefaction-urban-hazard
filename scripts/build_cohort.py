"""Build the global city cohort from GeoNames cities15000 (real, open, no auth).

GeoNames cities15000.txt is tab-separated, no header. Columns (0-indexed):
 1 name, 4 lat, 5 lon, 8 country, 14 population, 16 dem(elevation m), 17 tz
We keep populated places with population >= POP_MIN.

Output: data_derived/city_cohort_raw.csv  (name,country,lat,lon,population,elev_m)
"""
from __future__ import annotations
import csv, io, ssl, sys, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_raw"; DER = ROOT / "data_derived"
RAW.mkdir(exist_ok=True); DER.mkdir(exist_ok=True)
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
URL = "https://download.geonames.org/export/dump/cities15000.zip"
POP_MIN = 750_000

def fetch():
    local = RAW / "cities15000.zip"
    if local.exists() and local.stat().st_size > 1_000_000:
        print("using cached", local); return local.read_bytes()
    print("downloading", URL)
    req = urllib.request.Request(URL, headers={"User-Agent": "research/1.0"})
    data = urllib.request.urlopen(req, timeout=60, context=CTX).read()
    local.write_bytes(data)
    print(f"  {len(data)/1e6:.1f} MB -> {local}")
    return data

def main():
    data = fetch()
    zf = zipfile.ZipFile(io.BytesIO(data))
    txt = zf.read("cities15000.txt").decode("utf-8")
    rows = []
    for line in txt.splitlines():
        f = line.split("\t")
        if len(f) < 18:
            continue
        try:
            pop = int(f[14] or 0)
        except ValueError:
            pop = 0
        if pop < POP_MIN:
            continue
        if f[6] != "P":  # feature class P = populated place
            continue
        try:
            elev = int(f[16]) if f[16] not in ("", None) else ""
        except ValueError:
            elev = ""
        rows.append({
            "name": f[1], "country": f[8],
            "lat": round(float(f[4]), 5), "lon": round(float(f[5]), 5),
            "population": pop, "elev_m": elev,
        })
    rows.sort(key=lambda r: r["population"], reverse=True)
    out = DER / "city_cohort_raw.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "country", "lat", "lon", "population", "elev_m"])
        w.writeheader(); w.writerows(rows)
    print(f"\nWrote {len(rows)} cities (pop >= {POP_MIN:,}) -> {out}")
    print("Top 12:")
    for r in rows[:12]:
        print(f"  {r['name']:<18} {r['country']:<3} pop={r['population']:>10,}  ({r['lat']},{r['lon']})  {r['elev_m']}m")
    # quick continent-ish country spread
    from collections import Counter
    c = Counter(r["country"] for r in rows)
    print(f"\nCountries represented: {len(c)}; top: {c.most_common(8)}")

if __name__ == "__main__":
    main()
