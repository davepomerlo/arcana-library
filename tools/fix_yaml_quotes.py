"""Quote front-matter values that contain ': ' so YAML parses them. Safe to run repeatedly."""
import re, sys, json
from pathlib import Path
pat = re.compile(r'^(\s*(?:- )?[A-Za-z_]+): (.+)$')
for p in sorted(Path("content/texts").rglob("*.md")):
    raw = p.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        continue
    head, rest = raw[3:].split("\n---", 1)
    out = []
    for line in head.split("\n"):
        m = pat.match(line)
        if m:
            k, v = m.groups()
            if v[0] not in "\"'[>|{" and (": " in v or " #" in v):
                line = f'{k}: {json.dumps(v, ensure_ascii=False)}'
        out.append(line)
    new = "---" + "\n".join(out) + "\n---" + rest
    if new != raw:
        p.write_text(new, encoding="utf-8"); print("fixed", p)
