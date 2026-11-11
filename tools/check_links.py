#!/usr/bin/env python3
"""Check every external link in the archive and report the broken ones.

Collects URLs from the text pages (front matter and body) and the Library catalogue, requests
each one politely (HEAD, then GET if needed; one request per host at a time; a short pause
between requests to the same host) and writes data/link-report.json and data/link-report.md.

Usage:
  python tools/check_links.py            # check everything
  python tools/check_links.py --limit 50 # quick test

Exit code is 0 even when links are broken (the workflow opens an issue instead).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UA = "ArcanaLibraryLinkChecker/1.0 (+https://github.com/davepomerlo/arcana-library)"
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")
# Sites that block automated checks; reported as "unverifiable", not broken.
BOT_WALLS = ("thesaurus-linguae-aegyptiae.de", "repository.up.ac.za", "books.google", "jstor.org", "cambridge.org")


def collect() -> dict[str, set[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    for p in (ROOT / "content").rglob("*"):
        if p.suffix not in (".md", ".yaml"):
            continue
        for u in URL_RE.findall(p.read_text(encoding="utf-8")):
            found[u.rstrip(".,;:")].add(p.relative_to(ROOT).as_posix())
    return found


def check(url: str) -> tuple[str, int | None, str]:
    ctx = ssl.create_default_context()
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
                return url, r.status, "ok"
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 400, 429, 501):
                continue
            return url, e.code, "http-error"
        except Exception as e:  # DNS, timeout, TLS
            if method == "HEAD":
                continue
            return url, None, type(e).__name__
    return url, None, "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    found = collect()
    urls = sorted(found)
    if a.limit:
        urls = urls[: a.limit]
    by_host: dict[str, list[str]] = defaultdict(list)
    for u in urls:
        by_host[u.split("/")[2]].append(u)

    results = []

    def run_host(host_urls):
        out = []
        for u in host_urls:
            out.append(check(u))
            time.sleep(1.0)
        return out

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for chunk in ex.map(run_host, by_host.values()):
            results.extend(chunk)

    broken, walled = [], []
    for url, code, kind in results:
        if kind == "ok" and code and code < 400:
            continue
        host = url.split("/")[2]
        rec = {"url": url, "status": code, "error": kind, "files": sorted(found[url])}
        (walled if any(h in host for h in BOT_WALLS) or code in (401, 403, 429) else broken).append(rec)
    report = {"checked": len(results), "date": date.today().isoformat(), "broken": broken, "unverifiable": walled}
    (ROOT / "data" / "link-report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    lines = [f"# Link check, {report['date']}", "", f"Checked {len(results)} links: {len(broken)} broken, "
             f"{len(walled)} could not be verified automatically (the site blocks bots).", ""]
    for r in broken:
        lines.append(f"- [ ] {r['url']} — {r['status'] or r['error']} — in {', '.join(r['files'])}")
    (ROOT / "data" / "link-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Checked {len(results)} links; {len(broken)} broken; {len(walled)} unverifiable.")


if __name__ == "__main__":
    main()
