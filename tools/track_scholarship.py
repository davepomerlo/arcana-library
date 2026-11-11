#!/usr/bin/env python3
"""Find new scholarly publications on the archive's subjects and list them on research-feed.html.

Uses the OpenAlex API (https://openalex.org), a free, open index of research publications.
No API key is needed; OpenAlex asks polite users to send an e-mail address, which you can set
with the OPENALEX_MAILTO environment variable (for example as a GitHub Actions secret).

Usage:
  python tools/track_scholarship.py              # last 120 days
  python tools/track_scholarship.py --days 365   # longer window

Writes data/new-scholarship.json. Only titles, authors, venues and links are stored.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "new-scholarship.json"
UA = "ArcanaLibraryScholarshipTracker/1.0 (+https://github.com/davepomerlo/arcana-library)"

# Topic label -> OpenAlex search phrase. Edit freely.
TOPICS = {
    "Creation myths and cosmogony": '"creation myth" OR cosmogony',
    "Gnosticism and Nag Hammadi": 'gnosticism OR "Nag Hammadi"',
    "Hermeticism and Western esotericism": 'hermeticism OR "western esotericism"',
    "Neoplatonism": 'neoplatonism OR plotinus',
    "Daoism and early Chinese thought": 'daoism OR "early Chinese cosmology" OR guodian',
    "Buddhist and Tibetan texts": '"Tibetan Buddhism" OR "Buddhist manuscripts"',
    "Vedic and Sanskrit religious texts": 'Rigveda OR upanishad OR "Vedic religion"',
    "Ancient Egypt and Mesopotamia (religious texts)": '"Pyramid Texts" OR "Coffin Texts" OR "Sumerian literature" OR "Enuma Elish"',
    "Shamanism": 'shamanism',
    "Meditation and breathwork research": '"meditation" AND (breathing OR pranayama)',
    "Psychical research and anomalous experience": '"anomalous experience" OR parapsychology OR "psychical research"',
    "Indigenous oral traditions": '"oral tradition" AND (myth OR cosmology)',
}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def authors(work: dict) -> str:
    names = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])[:3]]
    more = " et al." if len(work.get("authorships", [])) > 3 else ""
    return ", ".join(n for n in names if n) + more


def item(work: dict, topic: str) -> dict:
    loc = work.get("primary_location") or {}
    src = (loc.get("source") or {}).get("display_name")
    oa = work.get("open_access") or {}
    doi = work.get("doi")
    return {
        "id": work.get("id"), "title": work.get("display_name") or "", "authors": authors(work),
        "venue": src, "date": work.get("publication_date"), "year": work.get("publication_year"),
        "type": work.get("type"), "url": doi or loc.get("landing_page_url") or work.get("id"),
        "open_access": bool(oa.get("is_oa")), "oa_url": oa.get("oa_url"), "topic": topic,
        "cited_by": work.get("cited_by_count", 0),
    }


def run(days: int, per_topic: int) -> dict:
    since = (date.today() - timedelta(days=days)).isoformat()
    mailto = os.environ.get("OPENALEX_MAILTO", "")
    seen, items = set(), []
    for topic, phrase in TOPICS.items():
        params = {
            "search": phrase,
            "filter": f"from_publication_date:{since},type:article|book|book-chapter|review",
            "sort": "cited_by_count:desc",
            "per-page": str(per_topic),
            "select": "id,doi,display_name,publication_date,publication_year,type,authorships,primary_location,open_access,cited_by_count",
        }
        if mailto:
            params["mailto"] = mailto
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        try:
            data = fetch(url)
        except Exception as e:  # network problems should not break the site build
            print(f"  ! {topic}: {e}", file=sys.stderr)
            continue
        for w in data.get("results", []):
            if w.get("id") in seen or not w.get("display_name"):
                continue
            seen.add(w["id"])
            items.append(item(w, topic))
        time.sleep(1)
    return {"updated": date.today().isoformat(), "window_days": days, "source": "https://openalex.org", "items": items}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--per-topic", type=int, default=10)
    a = ap.parse_args()
    feed = run(a.days, a.per_topic)
    if not feed["items"]:
        print("No results (network problem?); leaving the existing feed unchanged.")
        return
    OUT.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(feed['items'])} items to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
