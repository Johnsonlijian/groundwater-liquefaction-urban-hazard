"""Rebuild the editable PPTX deck for manual micro-adjustment."""
from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build_svg_suite.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("build_svg_suite", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build_pptx()
    print(mod.PPT_DIR / "NatureWater_Editable_Figure_Upgrade_Pack.pptx")


if __name__ == "__main__":
    main()
