"""Reconnaissance: confirm which REAL open-data sources are reachable without auth.

Run before building any dependency. Prints a status table; writes
data_derived/recon_report.json. Network calls use short timeouts and never raise.

Pillars probed:
  - World city cohort (GHS / simplemaps / github mirrors)
  - Seismic hazard PGA (GEM / USGS)
  - Vs30 (USGS global model)
  - GRACE-derived groundwater (nasagrace.unl.edu open GeoTIFF; PO.DAAC needs auth)
  - WorldPop population (direct, no auth)
  - OSM via osmnx (real networks)
"""
from __future__ import annotations
import json, ssl, time, urllib.request, socket, sys, io
from pathlib import Path
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

OUT = Path(__file__).resolve().parents[1] / "data_derived"
OUT.mkdir(parents=True, exist_ok=True)
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (research data recon; contact renlijian@imut.edu.cn)"}

CANDIDATES = {
    # name: (url, method)  -- HEAD where possible, else small GET
    "worldcities_github_dr5hn": ("https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/master/csv/cities.csv", "HEAD"),
    "geonames_cities15000":     ("https://download.geonames.org/export/dump/cities15000.zip", "HEAD"),
    "ghs_ucdb_jrc":             ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_STAT_UCDB2015MT_GLOBE_R2019A/GHS_STAT_UCDB2015MT_GLOBE_R2019A_V1_2.zip", "HEAD"),
    "usgs_base":                ("https://earthquake.usgs.gov/", "HEAD"),
    "usgs_vs30_global":         ("https://earthquake.usgs.gov/data/vs30/", "HEAD"),
    "gem_hazard_github":        ("https://raw.githubusercontent.com/GEMScienceTools/gmpe-smtk/master/README.md", "HEAD"),
    "gem_global_hazard_map":    ("https://maps.openquake.org/", "HEAD"),
    "nasagrace_unl":            ("https://nasagrace.unl.edu/globaldata/", "HEAD"),
    "worldpop_base":            ("https://data.worldpop.org/", "HEAD"),
    "fan2013_table_glowasis":   ("https://www.cybergis.illinois.edu/", "HEAD"),
    "zenodo_api":               ("https://zenodo.org/api/records/?q=global%20water%20table%20depth&size=3", "GET"),
    "figshare_api":             ("https://api.figshare.com/v2/articles/search", "HEAD"),
}

def probe(url, method, timeout=12):
    t = time.time()
    try:
        req = urllib.request.Request(url, headers=UA, method=method)
        r = urllib.request.urlopen(req, timeout=timeout, context=CTX)
        size = r.headers.get("Content-Length", "?")
        ctype = r.headers.get("Content-Type", "?")
        return {"ok": True, "status": r.status, "size": size, "ctype": ctype, "secs": round(time.time()-t, 1)}
    except urllib.error.HTTPError as e:
        return {"ok": e.code in (200, 301, 302, 403, 406), "status": e.code, "note": "HTTPError", "secs": round(time.time()-t, 1)}
    except Exception as e:
        return {"ok": False, "status": None, "note": f"{type(e).__name__}: {str(e)[:60]}", "secs": round(time.time()-t, 1)}

def main():
    socket.setdefaulttimeout(15)
    report = {}
    print(f"{'SOURCE':<28} {'OK':<4} {'STATUS':<7} {'SECS':<5} NOTE")
    print("-"*78)
    for name, (url, method) in CANDIDATES.items():
        res = probe(url, method)
        report[name] = {"url": url, **res}
        flag = "OK" if res["ok"] else "XX"
        note = res.get("note", res.get("ctype", ""))
        print(f"{name:<28} {flag:<4} {str(res['status']):<7} {res['secs']:<5} {note}")
    # osmnx real-network smoke test (small)
    try:
        import osmnx as ox
        t = time.time()
        G = ox.graph_from_point((35.68, 139.76), dist=300, network_type="drive")
        report["osmnx_tokyo_300m"] = {"ok": True, "n_nodes": G.number_of_nodes(), "n_edges": G.number_of_edges(), "secs": round(time.time()-t,1)}
        print(f"{'osmnx_tokyo_300m':<28} {'OK':<4} {'-':<7} {round(time.time()-t,1):<5} nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
    except Exception as e:
        report["osmnx_tokyo_300m"] = {"ok": False, "note": f"{type(e).__name__}: {str(e)[:80]}"}
        print(f"{'osmnx_tokyo_300m':<28} {'XX':<4} {'-':<7} {'-':<5} {type(e).__name__}: {str(e)[:60]}")
    (OUT / "recon_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nWrote", OUT / "recon_report.json")

if __name__ == "__main__":
    main()
