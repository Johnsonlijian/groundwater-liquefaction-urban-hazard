"""Audit figure factory outputs for provenance, completeness and basic quality."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from write_manifest import main as write_manifest


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXPORT = ROOT / "export"
SVG = EXPORT / "svg"
PDF = EXPORT / "pdf"
PNG = EXPORT / "png_600dpi"
PPTX = EXPORT / "pptx" / "NatureWater_Editable_Figure_Upgrade_Pack.pptx"
REPORT = ROOT / "audit_report.md"

EXPECTED = [
    "Fig1_3D_DGLS_mechanism_upgrade",
    "Fig2_global_null_regional_payload_upgrade",
    "Fig3_regional_evidence_arena_upgrade",
    "Fig4_product_evidence_ladder_upgrade",
    "Fig5_aquifer_sy_phase_arena_upgrade",
    "Fig6_engineering_event_protocol_arena_upgrade",
    "Box1_review_protocol",
]


def run_pdftotext(pdf: Path) -> str:
    if not shutil.which("pdftotext"):
        return ""
    result = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return result.stdout


def check_svg_text(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    return "<text" in text and "<image" not in text


def main() -> None:
    display = json.loads((DATA / "display_summary.json").read_text(encoding="utf-8"))
    counts = display["global_payload_counts"]
    lines = ["# Nature Water Figure Factory Audit", ""]
    passed = True

    lines += ["## File completeness"]
    for stem in EXPECTED:
        for folder, ext in [(SVG, "svg"), (PDF, "pdf"), (PNG, "png")]:
            path = folder / f"{stem}.{ext}"
            ok = path.exists() and path.stat().st_size > 0
            lines.append(f"- `{path.relative_to(ROOT)}`: {'PASS' if ok else 'FAIL'}")
            passed = passed and ok
    ok_pptx = PPTX.exists() and PPTX.stat().st_size > 0
    lines.append(f"- `{PPTX.relative_to(ROOT)}`: {'PASS' if ok_pptx else 'FAIL'}")
    passed = passed and ok_pptx

    lines += ["", "## SVG provenance"]
    for stem in EXPECTED:
        path = SVG / f"{stem}.svg"
        ok = path.exists() and check_svg_text(path)
        lines.append(f"- `{path.name}` live text/no embedded raster: {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

    lines += ["", "## Numeric label checks"]
    fig2 = (SVG / "Fig2_global_null_regional_payload_upgrade.svg").read_text(encoding="utf-8", errors="replace")
    checks = {
        "444 city count": str(counts["n_cities"]) in fig2,
        "311 detectable count": str(counts["detectable"]) in fig2,
        "28 A/B count": str(counts["ab"]) in fig2,
        "10 regional groups": str(counts["regional"]) in fig2,
        "global mean": f"{counts['mean_dp']:+.5f}" in fig2,
    }
    for label, ok in checks.items():
        lines.append(f"- {label}: {'PASS' if ok else 'FAIL'}")
        passed = passed and ok

    lines += ["", "## PNG preview size"]
    for stem in EXPECTED:
        path = PNG / f"{stem}.png"
        if path.exists():
            with Image.open(path) as img:
                ok = img.width >= 3000
                lines.append(f"- `{path.name}`: {img.width}x{img.height} {'PASS' if ok else 'FAIL'}")
                passed = passed and ok

    lines += ["", "## Placeholder and identity scan"]
    banned = ["TODO", "[to verify]", "AI-generated final", "DALL", "Midjourney", "Stable Diffusion"]
    for folder in [SVG, PDF]:
        for path in folder.glob("*.*"):
            text = path.read_text(encoding="utf-8", errors="replace") if path.suffix == ".svg" else run_pdftotext(path)
            hits = [b for b in banned if b in text]
            ok = not hits
            lines.append(f"- `{path.relative_to(ROOT)}`: {'PASS' if ok else 'HITS ' + ', '.join(hits)}")
            passed = passed and ok

    blender_ok = shutil.which("blender") is not None
    lines += ["", "## Blender boundary", f"- `blender` available: {'YES' if blender_ok else 'NO'}"]
    if not blender_ok:
        lines.append("- Boundary recorded: `.blend` rendering was not executed in this environment; Blender source scripts are provided and code-generated 3D/SVG fallback was built.")

    write_manifest()
    manifest_ok = (EXPORT / "manifest_sha256.txt").exists()
    passed = passed and manifest_ok
    lines += ["", "## Manifest", f"- `export/manifest_sha256.txt`: {'PASS' if manifest_ok else 'FAIL'}"]
    lines += ["", f"## Overall\n\n{'PASS' if passed else 'FAIL'}"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
