# Nature Water Figure Factory

This directory is the reproducible figure-production factory for the DGLS-v1
Nature Water Article package.

Principle: PPTX is a manual editing and presentation layer only. The primary
publication sources are deterministic scripts, Blender geometry, SVG layouts,
derived data tables and audit records.

## Build

```powershell
make doctor
make all
make audit
```

On Windows without GNU Make, use:

```powershell
python python\doctor.py
python python\build_svg_suite.py
python python\build_pptx_deck.py
python python\audit_figures.py
```

If Blender is installed and available as `blender`, run:

```powershell
make fig1-blender
```

If Blender is unavailable, the audit records the boundary and the code-generated
3D/SVG mechanism candidate remains the reviewer-safe fallback.

## Outputs

- `export/svg/`: editable SVG.
- `export/pdf/`: vector PDF.
- `export/png_600dpi/`: high-resolution PNG previews.
- `export/pptx/`: editable PowerPoint deck for manual micro-adjustment.
- `export/manifest_sha256.txt`: checksums.
- `audit_report.md`: build, provenance and figure-integrity audit.
- `journal_policy_note.md`: current Nature Water figure-format and AI-use
  boundary note.

## Guardrails

- No final generative-AI raster images.
- No invented numbers.
- All numerical labels come from `data/` tables that mirror `data_derived/`.
- Text remains editable in SVG/PPTX where possible.
- The scientific boundary remains: review cue, not hazard map, city ranking,
  event prediction, factor of safety or regulatory threshold.
