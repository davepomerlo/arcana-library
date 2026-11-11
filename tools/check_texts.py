#!/usr/bin/env python3
"""Check every text page for common mistakes before you publish.

Usage:  python tools/check_texts.py

Checks: front matter parses; required fields present; section and status values valid;
every ::: parallel block has a translation part; ::: blocks are closed.
Exits with code 1 if anything is wrong (the GitHub workflow runs this too).
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["title", "lang", "tradition", "summary", "translation"]
STATUSES = {"reviewed", "checked", "partly-checked", "unchecked"}
TYPES = {"ai-assisted", "public-domain", "open-licence", "original-research"}
SECTIONS = {"ancient-sacred", "philosophy", "esoteric", "paranormal"}

problems = 0


def warn(p, msg):
    global problems
    problems += 1
    print(f"  ✗ {p.relative_to(ROOT)}: {msg}")


for p in sorted((ROOT / "content" / "texts").rglob("*.md")):
    raw = p.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        warn(p, "no front matter (file must start with ---)")
        continue
    head, _, body = raw[3:].partition("\n---")
    try:
        meta = yaml.safe_load(head) or {}
    except yaml.YAMLError as e:
        warn(p, f"front matter does not parse — put values containing ': ' in quotes ({e.problem})")
        continue
    for k in REQUIRED:
        if not meta.get(k):
            warn(p, f"missing '{k}'")
    if p.parent.name not in SECTIONS:
        warn(p, f"folder '{p.parent.name}' is not a section")
    if meta.get("status") and meta["status"] not in STATUSES:
        warn(p, f"status must be one of {sorted(STATUSES)}")
    if meta.get("status") == "reviewed" and not (meta.get("reviewed_by") or {}).get("name"):
        warn(p, "status 'reviewed' needs reviewed_by: {name: ..., languages/affiliation/date}")
    tr = meta.get("translation") or {}
    if tr.get("type") not in TYPES:
        warn(p, f"translation.type must be one of {sorted(TYPES)}")
    opens = len(re.findall(r"^:::[ \t]*(parallel|note)", body, re.M))
    closes = len(re.findall(r"^:::[ \t]*$", body, re.M))
    if opens != closes:
        warn(p, f"{opens} ::: blocks opened but {closes} closed")
    for m in re.finditer(r"^:::[ \t]*parallel[^\n]*\n(.*?)\n:::[ \t]*$", body, re.M | re.S):
        if not re.search(r"^---[ \t]*$", m.group(1), re.M):
            line = body[: m.start()].count("\n") + 1
            warn(p, f"parallel block near body line {line} has no '---' separating original and translation")

if problems:
    print(f"\n{problems} problem(s) found.")
    sys.exit(1)
print("All texts look good.")
