#!/usr/bin/env python3
"""Create a new text page from the template.

Usage:
    python tools/new_text.py esoteric "Corpus Hermeticum I: Poimandres"

Creates content/texts/esoteric/corpus-hermeticum-i-poimandres.md, ready to fill in.
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import yaml as _y
from pathlib import Path as _P
SECTIONS = [s["slug"] for s in _y.safe_load(open(_P(__file__).resolve().parent.parent / "site.yaml", encoding="utf-8"))["sections"]]


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "new-text"


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in SECTIONS:
        print(__doc__)
        print("Sections:", ", ".join(SECTIONS))
        sys.exit(1)
    section, title = sys.argv[1], " ".join(sys.argv[2:])
    dest = ROOT / "content" / "texts" / section / f"{slugify(title)}.md"
    if dest.exists():
        sys.exit(f"Already exists: {dest}")
    tpl = (ROOT / "content" / "TEMPLATE.md").read_text(encoding="utf-8")
    tpl = tpl.replace("title: The English title", f'title: "{title}"', 1)
    dest.write_text(tpl, encoding="utf-8")
    print(f"Created {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
