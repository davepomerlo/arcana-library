"""Download selected public-domain books from sacred-texts.com, keeping their attribution.

Reads data/sacred-texts-mirror.yaml and saves each book to content/mirror/<id>/:
    meta.json         title, author, source pages, the attribution line found on each page
    pages/000.html    one cleaned HTML fragment per page of the book
    images/...        illustrations that belong to the book (scans of figures, plates)

It is meant to run on GitHub Actions (the build workflow runs it weekly and on manual runs).
Books already downloaded are skipped unless you pass --refresh, so normally it only fetches
books newly added to the YAML file.

Politeness: obeys https://sacred-texts.com/robots.txt, identifies itself, waits DELAY seconds
between requests and stops a book at MAX_PAGES. The archive's terms
(https://sacred-texts.com/tos.htm) allow non-commercial electronic copies provided the
attribution notice is left intact and a link back is given: every saved page keeps the
archive's own attribution line, and the reading pages link each page to its original.

Usage:
    python tools/mirror_sacred_texts.py                 # download books not yet mirrored
    python tools/mirror_sacred_texts.py --only report-on-ufos --refresh
    python tools/mirror_sacred_texts.py --base http://localhost:8000   # test against a local copy
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import yaml
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "data" / "sacred-texts-mirror.yaml"
OUT = ROOT / "content" / "mirror"
UA = "ArcanaLibraryMirror/1.0 (+https://github.com/davepomerlo/arcana-library; non-commercial archive)"
DELAY = 3.0
MAX_PAGES = 600
HOST = "https://sacred-texts.com"

NAV_WORDS = {"sacred texts", "index", "previous", "next", "contents", "home", "buy this book at amazon.com"}
ATTRIB_RX = re.compile(r"at sacred-texts\.com|sacred-texts\.com|Internet Sacred Text Archive", re.I)
PD_RX = re.compile(r"public domain[^.]{0,200}\.", re.I)


class Fetcher:
    def __init__(self, base: str | None):
        self.base = base.rstrip("/") if base else None
        self.last = 0.0
        self.robots = urllib.robotparser.RobotFileParser()
        self.robots_ok = True
        if not self.base:
            try:
                self.robots.set_url(HOST + "/robots.txt")
                self.robots.read()
            except Exception as e:  # unreachable robots.txt: be conservative and allow, as most crawlers do
                print(f"  (could not read robots.txt: {e}; continuing)")
                self.robots_ok = False

    def real(self, url: str) -> str:
        """Map a sacred-texts.com address to the test server when --base is given."""
        if self.base:
            p = urlparse(url)
            return self.base + p.path
        return url

    def allowed(self, url: str) -> bool:
        return self.base is not None or not self.robots_ok or self.robots.can_fetch(UA, url)

    def get(self, url: str, binary: bool = False):
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        wait = DELAY - (time.time() - self.last) if not self.base else 0
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(self.real(url), headers={"User-Agent": UA})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = r.read()
                    self.last = time.time()
                    if binary:
                        return data
                    charset = r.headers.get_content_charset()
                    return decode(data, charset)
            except urllib.error.HTTPError as e:
                self.last = time.time()
                if e.code in (404, 410, 403):
                    raise
                time.sleep(5 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError):
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"failed to fetch {url}")


def decode(data: bytes, charset: str | None) -> str:
    m = re.search(rb'charset=["\']?([\w-]+)', data[:2000])
    for cs in [charset, m.group(1).decode() if m else None, "utf-8", "windows-1252", "latin-1"]:
        if not cs:
            continue
        try:
            return data.decode(cs)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", "replace")


def book_dir(url: str) -> str:
    p = urlparse(url).path
    return p[: p.rfind("/") + 1]


def in_book(href: str, base_url: str, bdir: str) -> str | None:
    """Return the absolute URL if href points to another page of the same book."""
    if not href or href.startswith(("mailto:", "javascript:", "#")):
        return None
    absu = urljoin(base_url, href.split("#")[0])
    p = urlparse(absu)
    if p.netloc and p.netloc not in ("sacred-texts.com", "www.sacred-texts.com", urlparse(base_url).netloc):
        return None
    if not p.path.startswith(bdir) or "/" in p.path[len(bdir):]:
        return None
    name = p.path[len(bdir):]
    if not re.search(r"\.html?$", name, re.I) or name.lower() in ("pageidx.htm",):
        return None
    return HOST + p.path


def page_order(fetch: Fetcher, starts: list[str]) -> tuple[list[str], dict]:
    """Find the pages of the book: from a contents page, or by following 'Next' links."""
    html, start = None, None
    for s in starts:
        try:
            html = fetch.get(s)
            start = s
            break
        except Exception as e:
            print(f"  {s}: {e}")
    if html is None:
        raise RuntimeError("no start page could be fetched")
    cache = {start: html}
    bdir = book_dir(urlparse(start).path)
    soup = BeautifulSoup(html, "html.parser")
    order = [start]
    if start.lower().endswith("index.htm"):
        for a in soup.find_all("a", href=True):
            u = in_book(a["href"], start, bdir)
            if u and u not in order:
                order.append(u)
        if len(order) > 1:
            return order[:MAX_PAGES], cache
    # follow Next links
    cur, cur_html = start, html
    while len(order) < MAX_PAGES:
        s = BeautifulSoup(cur_html, "html.parser")
        nxt = None
        for a in s.find_all("a", href=True):
            if a.get_text(" ", strip=True).lower().startswith("next"):
                nxt = in_book(a["href"], cur, bdir)
                if nxt:
                    break
        if not nxt or nxt in order:
            break
        try:
            cur_html = fetch.get(nxt)
        except Exception as e:
            print(f"  stopped at {nxt}: {e}")
            break
        cache[nxt] = cur_html
        order.append(nxt)
        cur = nxt
    return order, cache


def clean(html: str, url: str, bdir: str, local: dict[str, str], fetch: Fetcher, imgdir: Path, rel_img: str):
    """Return (title, attribution line, public-domain statement, cleaned body HTML)."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "").strip()
    body = soup.body or soup
    for t in body.find_all(["script", "style", "form", "iframe", "noscript", "object", "embed", "input", "button", "select"]):
        t.decompose()
    for c in body.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()
    # navigation, shop and advertising links
    for a in body.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        href = a["href"].lower()
        if ("amazon." in href or "cdshop" in href or "feedblitz" in href or "facebook" in href or "twitter" in href
                or text in NAV_WORDS or text.startswith(("next:", "previous:", "next »", "« previous"))):
            a.decompose()
            continue
        # links to the archive's subject indexes (the "Sacred Texts › UFOs" trail)
        absu = urljoin(url, a["href"])
        if urlparse(absu).path.endswith("/index.htm") and not urlparse(absu).path.startswith(bdir) and len(text.split()) <= 4:
            par = a.parent
            if par is None or par.name == "center" or len(par.get_text(" ", strip=True)) < 40:
                a.decompose()   # part of the navigation trail
            # otherwise a real reference inside the text: keep it, pointing at sacred-texts.com
    for tag in body.find_all(["center", "p", "div", "font", "span"]):
        if not tag.get_text(strip=True) and not tag.find("img"):
            tag.decompose()
    for img in body.find_all("img"):
        src = img.get("src", "")
        absu = urljoin(url, src)
        p = urlparse(absu)
        if not p.path.startswith(bdir) or "cdshop" in p.path:
            img.decompose()
            continue
        name = p.path[len(bdir):].replace("/", "_")
        dest = imgdir / name
        try:
            if not dest.exists():
                data = fetch.get(HOST + p.path, binary=True)
                imgdir.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            img["src"] = f"{rel_img}/{name}"
            for k in list(img.attrs):
                if k not in ("src", "alt", "width", "height"):
                    del img.attrs[k]
        except Exception as e:
            print(f"    image {src}: {e}")
            img.decompose()
    for a in body.find_all("a", href=True):
        u = in_book(a["href"], url, bdir)
        frag = ("#" + a["href"].split("#", 1)[1]) if "#" in a["href"] else ""
        if u and u in local:
            a["href"] = local[u] + frag
        elif not a["href"].startswith("#"):
            a["href"] = urljoin(url, a["href"]) if not fetch.base else urljoin(HOST + urlparse(url).path, a["href"])
            a["rel"] = "noopener"
    text = body.get_text(" ", strip=True)
    attrib = ""
    for line in body.get_text("\n", strip=True).split("\n"):
        if re.search(r"at sacred-texts\.com", line, re.I):
            attrib = line.strip()
            break
    pd = ""
    node = body.find(string=re.compile(r"public domain", re.I))
    if node is not None:
        pd = re.sub(r"\s+", " ", node.parent.get_text(" ", strip=True))[:400]
    inner = "".join(str(c) for c in body.contents).strip()
    inner = re.sub(r"(<br\s*/?>\s*){3,}", "<br><br>", inner)
    inner = re.sub(r"(<hr\s*/?>\s*){2,}", "<hr>", inner)
    return title, attrib, pd, inner


def mirror_book(fetch: Fetcher, book: dict, refresh: bool) -> bool:
    bid = book["id"]
    dest = OUT / bid
    if (dest / "meta.json").exists() and not refresh:
        print(f"= {bid}: already mirrored")
        return False
    print(f"+ {bid}: {book['title']}")
    order, cache = page_order(fetch, book["start"])
    print(f"  {len(order)} pages")
    local = {u: f"{i:03d}.html" for i, u in enumerate(order)}
    bdir = book_dir(urlparse(order[0]).path)
    tmp = OUT / f".{bid}.tmp"
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp)
    (tmp / "pages").mkdir(parents=True)
    pages, pd_stmt, attrib_missing = [], "", 0
    for i, u in enumerate(order):
        html = cache.get(u)
        if html is None:
            try:
                html = fetch.get(u)
            except Exception as e:
                print(f"  skip {u}: {e}")
                continue
        title, attrib, pd, inner = clean(html, u, bdir, local, fetch, tmp / "images", "images")
        if not attrib:
            attrib_missing += 1
        if pd and not pd_stmt:
            pd_stmt = pd
        (tmp / "pages" / local[u]).write_text(inner, encoding="utf-8")
        pages.append({"file": local[u], "title": title, "source": u, "attribution": attrib})
        print(f"  {i + 1}/{len(order)} {u.rsplit('/', 1)[-1]}")
    meta = {k: book.get(k) for k in ("id", "title", "author", "year", "section", "basis")}
    meta |= {"start": order[0], "fetched": date.today().isoformat(), "pages": pages,
             "public_domain_statement": pd_stmt, "pages_without_attribution_line": attrib_missing,
             "terms": "https://sacred-texts.com/tos.htm"}
    (tmp / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    tmp.rename(dest)
    print(f"  saved {len(pages)} pages to {dest}"
          + (f" ({attrib_missing} without an 'at sacred-texts.com' line; the reading pages add one)" if attrib_missing else ""))
    return True


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="mirror just this book id")
    ap.add_argument("--refresh", action="store_true", help="download again even if already mirrored")
    ap.add_argument("--base", help="fetch from this server instead of sacred-texts.com (for testing)")
    ap.add_argument("--list", default=str(LIST), help="book list (YAML)")
    ap.add_argument("--out", default=str(OUT), help="output folder")
    args = ap.parse_args()
    OUT = Path(args.out)
    books = yaml.safe_load(Path(args.list).read_text("utf-8"))["books"]
    if args.only:
        books = [b for b in books if b["id"] == args.only]
    OUT.mkdir(parents=True, exist_ok=True)
    fetch = Fetcher(args.base)
    changed, failed = 0, []
    for b in books:
        try:
            changed += mirror_book(fetch, b, args.refresh)
        except Exception as e:
            print(f"! {b['id']}: {e}")
            failed.append(b["id"])
    print(f"{changed} book(s) downloaded; {len(failed)} failed{': ' + ', '.join(failed) if failed else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
