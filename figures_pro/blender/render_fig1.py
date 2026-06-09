"""Render the DGLS Figure 1 Blender scene."""
from __future__ import annotations

from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "export" / "blender"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))

from fig1_cutaway_scene import make_scene  # noqa: E402

import bpy  # noqa: E402


def main():
    make_scene()
    bpy.context.scene.render.filepath = str(OUT / "Fig1_DGLS_cutaway_render_alpha.png")
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Fig1_DGLS_cutaway_scene.blend"))


if __name__ == "__main__":
    main()
