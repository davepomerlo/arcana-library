#!/usr/bin/env python3
"""Fail if any page in _site links to a file that does not exist. Run after build.py."""
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "_site"
bad = []
for f in SITE.rglob("*.html"):
    for h in re.findall(r'(?:href|src)="([^"#:?]+)(?:[?#][^"]*)?"', f.read_text(encoding="utf-8")):
        if h.startswith(("http", "mailto", "data:")) or not h:
            continue
        if not (f.parent / h).resolve().exists():
            bad.append(f"{f.relative_to(SITE)} -> {h}")
for b in bad:
    print("  ✗", b)
print(f"{len(bad)} broken internal links")
sys.exit(1 if bad else 0)
