"""Track new L/L Research channelling transcripts.

L/L Research publishes new conscious-channelling transcripts at
https://www.llresearch.org/channeling/YYYY/MMDD, with a PDF at
https://assets.llresearch.org/transcripts/files/en/YYYY_MMDD.pdf.

The material is copyright L/L Research ("not in the public domain"; quotation and reuse need
their permission), so this script does NOT copy transcript text. For each new session it records:

  * date, title and L/L Research's own one-line description (from the page's meta tags,
    shortened to 300 characters),
  * links to the official page and PDF,
  * optionally (--wayback) a snapshot in the Internet Archive's Wayback Machine, so that a
    public, independent archived copy exists even if the original page moves.

The result is data/llresearch-index.json, which build.py turns into channelling-tracker.html.

Usage:
  python tools/track_llresearch.py              # check the "latest" and "updates" pages
  python tools/track_llresearch.py --wayback    # also request Wayback Machine snapshots
  python tools/track_llresearch.py --year 2025  # also scan that year's archive pages (backfill)

The GitHub Actions workflow runs it once a week. It obeys robots.txt and waits between requests.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "llresearch-index.json"
BASE = "https://www.llresearch.org"
PDF = "https://assets.llresearch.org/transcripts/files/en/{y}_{md}.pdf"
LISTING_PAGES = [f"{BASE}/channeling/transcripts", f"{BASE}/updates"]
UA = "ArcanaLibraryTracker/1.0 (+https://github.com/davepomerlo/arcana-library)"
DELAY = 3.0  # seconds between requests
LINK_RE = re.compile(r'href="(?:https?://(?:www\.)?llresearch\.org)?/channeling/(\d{4})/(\d{4}[a-z0-9_-]*)/?(?=["#?])', re.I)

_robots: urllib.robotparser.RobotFileParser | None = None


def allowed(url: str) -> bool:
    global _robots
    if _robots is None:
        _robots = urllib.robotparser.RobotFileParser(BASE + "/robots.txt")
        try:
            _robots.read()
        except Exception:  # no robots.txt reachable: proceed politely
            _robots = urllib.robotparser.RobotFileParser()
            _robots.parse([])
    return _robots.can_fetch(UA, url)


def fetch(url: str, method: str = "GET", timeout: int = 30) -> tuple[int, str, dict]:
    if url.startswith(BASE) and not allowed(url):
        print(f"  robots.txt disallows {url}; skipping")
        return 0, "", {}
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    time.sleep(DELAY)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace") if method == "GET" else ""
            return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", dict(e.headers or {})
    except Exception as e:  # network error
        print(f"  error fetching {url}: {e}")
        return 0, "", {}


def meta(page: str, name: str) -> str:
    for pat in (rf'<meta[^>]+(?:name|property)="{name}"[^>]+content="([^"]*)"',
                rf'<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="{name}"'):
        m = re.search(pat, page, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def clean_title(t: str) -> str:
    t = re.split(r"\s+[|–—-]\s+L/L Research", t)[0]
    return re.sub(r"\s+", " ", t).strip()


def shorten(s: str, n: int = 300) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def find_ids(page: str) -> set[tuple[str, str]]:
    return {(y, md.lower()) for y, md in LINK_RE.findall(page)}


def describe(y: str, md: str) -> dict:
    url = f"{BASE}/channeling/{y}/{md}"
    status, page, _ = fetch(url)
    entry = {"id": f"{y}/{md}", "url": url, "first_seen": date.today().isoformat()}
    try:
        entry["date"] = datetime.strptime(y + md[:4], "%Y%m%d").date().isoformat()
    except ValueError:
        entry["date"] = None
    if status == 200:
        title = meta(page, "og:title") or (re.search(r"<title>(.*?)</title>", page, re.S | re.I) or [None, ""])[1]
        entry["title"] = clean_title(html.unescape(title)) or "Transcript"
        entry["description"] = shorten(meta(page, "description") or meta(page, "og:description"))
    else:
        entry["title"], entry["description"] = "Transcript", ""
        entry["status"] = status
    pdf = PDF.format(y=y, md=md)
    s, _, _ = fetch(pdf, method="HEAD")
    if s == 200:
        entry["pdf"] = pdf
    return entry


def wayback(url: str) -> str | None:
    status, _, headers = fetch("https://web.archive.org/save/" + url, timeout=120)
    if status in (200, 302):
        loc = headers.get("Content-Location") or headers.get("Location") or ""
        return ("https://web.archive.org" + loc) if loc.startswith("/web/") else "https://web.archive.org/web/" + url
    print(f"  Wayback Machine returned {status} for {url}")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--wayback", action="store_true", help="request Wayback Machine snapshots of new pages")
    ap.add_argument("--year", type=int, action="append", default=[], help="also scan this year's archive pages")
    ap.add_argument("--max-new", type=int, default=40, help="stop after this many new sessions in one run")
    args = ap.parse_args()

    data = json.loads(INDEX.read_text("utf-8")) if INDEX.exists() else {"entries": []}
    known = {e["id"] for e in data["entries"]}

    pages = list(LISTING_PAGES)
    for y in args.year:
        pages += [f"{BASE}/channeling/{y}"] + [f"{BASE}/channeling/{y}/{n}" for n in range(1, 6)]

    found: set[tuple[str, str]] = set()
    for p in pages:
        status, body, _ = fetch(p)
        print(f"{status} {p}")
        if status == 200:
            found |= find_ids(body)

    new = sorted((i for i in found if f"{i[0]}/{i[1]}" not in known), reverse=True)[: args.max_new]
    print(f"{len(found)} session links found, {len(new)} new")
    for y, md in new:
        e = describe(y, md)
        if args.wayback:
            e["wayback"] = wayback(e["url"])
            if e.get("pdf"):
                e["wayback_pdf"] = wayback(e["pdf"])
        print(f"  + {e['date']}  {e['title']}")
        data["entries"].append(e)

    data["entries"].sort(key=lambda e: (e.get("date") or "", e["id"]), reverse=True)
    data["source"] = BASE + "/channeling/transcripts"
    data["copyright"] = "Transcripts © L/L Research. This index stores links and L/L Research's own short descriptions only."
    if new or not INDEX.exists():
        data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        INDEX.parent.mkdir(exist_ok=True)
        INDEX.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
