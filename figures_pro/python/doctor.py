"""Environment diagnostic for the Nature Water figure factory."""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "doctor_report.md"

PYTHON_MODULES = [
    "pandas",
    "numpy",
    "matplotlib",
    "PIL",
    "pptx",
    "fitz",
    "jinja2",
    "geopandas",
]

EXTERNAL_TOOLS = ["blender", "inkscape", "rsvg-convert", "gswin64c", "pdftotext"]


def tool_version(cmd: str) -> str:
    path = shutil.which(cmd)
    if not path:
        return "MISSING"
    probes = [[cmd, "--version"], [cmd, "-version"]]
    for probe in probes:
        try:
            result = subprocess.run(probe, capture_output=True, text=True, timeout=8)
            text = (result.stdout or result.stderr).strip().splitlines()
            if text:
                return f"{path} | {text[0]}"
        except Exception:
            continue
    return path


def main() -> None:
    lines = [
        "# Figure Factory Doctor Report",
        "",
        f"- Python: `{sys.version.split()[0]}`",
        f"- Root: `{ROOT}`",
        "",
        "## Python modules",
    ]
    ok = True
    for mod in PYTHON_MODULES:
        try:
            importlib.import_module(mod)
            status = "OK"
        except Exception as exc:
            status = f"MISSING ({type(exc).__name__}: {exc})"
            ok = False
        lines.append(f"- `{mod}`: {status}")
    lines += ["", "## External tools"]
    for tool in EXTERNAL_TOOLS:
        version = tool_version(tool)
        lines.append(f"- `{tool}`: {version}")
        if version == "MISSING" and tool == "blender":
            lines.append("  - Boundary: Blender `.blend` rendering is unavailable; use code-generated 3D fallback until Blender is installed.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
