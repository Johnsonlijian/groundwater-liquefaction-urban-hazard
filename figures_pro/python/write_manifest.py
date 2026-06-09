"""Write SHA-256 checksums for exported figure assets."""
from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "export"
MANIFEST = EXPORT / "manifest_sha256.txt"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    files = [
        p for p in EXPORT.rglob("*")
        if p.is_file() and p.name != MANIFEST.name
    ]
    lines = [f"{sha256(p)}  {p.relative_to(EXPORT).as_posix()}" for p in sorted(files)]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST} with {len(lines)} files")


if __name__ == "__main__":
    main()
