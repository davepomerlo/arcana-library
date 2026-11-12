"""Reading pages for books mirrored from sacred-texts.com (content/mirror/<id>/).

The pages were downloaded by tools/mirror_sacred_texts.py. Here they are sanitised again
(only safe tags and attributes survive), wrapped in the site's layout with the archive's
attribution notice and a link to each original page, and written to _site/mirror/.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, Comment

ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "center", "cite", "code", "dd", "div", "dl", "dt", "em",
    "font", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "q", "s", "small",
    "span", "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
ALLOWED_ATTRS = {"href", "src", "alt", "id", "name", "title", "colspan", "rowspan", "width", "height", "lang", "dir", "rel"}

TERMS_NOTE = (
    "Reproduced from the Internet Sacred Text Archive (sacred-texts.com) with its attribution notice intact, "
    "under the archive's terms, which allow non-commercial electronic copies. This page is <strong>not</strong> "
    "covered by the Arcana Library's CC BY-SA licence and may not be used commercially."
)


def sanitise(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()
    for t in soup.find_all(True):
        if t.name not in ALLOWED_TAGS:
            if t.name in ("script", "style", "iframe", "object", "embed", "form", "noscript", "svg", "math"):
                t.decompose()
            else:
                t.unwrap()
            continue
        for k in list(t.attrs):
            v = t.attrs[k]
            v = " ".join(v) if isinstance(v, list) else str(v)
            if k not in ALLOWED_ATTRS or (k in ("href", "src") and re.match(r"\s*(javascript|data|vbscript):", v, re.I)):
                del t.attrs[k]
        if t.name == "a" and str(t.get("href", "")).startswith("http"):
            t["rel"] = "noopener"
    return str(soup)


def load(root: Path) -> list[dict]:
    books = []
    for meta_path in sorted((root / "content" / "mirror").glob("*/meta.json")):
        meta = json.loads(meta_path.read_text("utf-8"))
        meta["_dir"] = meta_path.parent
        books.append(meta)
    return books


def run(b, site, secs) -> list[dict]:
    OUT, ROOT, esc, page = b.OUT, b.ROOT, b.esc, b.page
    books = load(ROOT)
    planned = yaml.safe_load((ROOT / "data" / "sacred-texts-mirror.yaml").read_text("utf-8")).get("books", [])
    done_ids = {m["id"] for m in books}
    mdir = OUT / "mirror"
    mdir.mkdir(exist_ok=True)

    for m in books:
        bid = m["id"]
        bout = mdir / bid
        bout.mkdir(parents=True, exist_ok=True)
        if (m["_dir"] / "images").is_dir():
            shutil.copytree(m["_dir"] / "images", bout / "images", dirs_exist_ok=True)
        pages = m.get("pages", [])
        book_attrib = next((p["attribution"] for p in pages if p.get("attribution")), "")
        head = f'<nav class="crumbs"><a href="../../index.html">Home</a> › <a href="../../sacred-texts.html">sacred-texts.com collection</a> › <a href="../index.html">Mirrored books</a></nav>'
        for i, p in enumerate(pages):
            inner = sanitise((m["_dir"] / "pages" / p["file"]).read_text("utf-8"))
            prev_l = f'<a href="{pages[i - 1]["file"]}">← Previous</a>' if i else ""
            next_l = f'<a href="{pages[i + 1]["file"]}">Next →</a>' if i + 1 < len(pages) else ""
            nav = f'<p class="mirror-nav">{prev_l} <a href="index.html">Contents</a> {next_l}</p>'
            attrib = p.get("attribution") or book_attrib or f"{m['title']}, at sacred-texts.com"
            missing = "" if p.get("attribution") else f'<p class="muted">Attribution: {esc(attrib)}</p>'
            note = (f'<div class="note mirror-note"><p>{TERMS_NOTE} Original page: '
                    f'<a href="{esc(p["source"])}" rel="noopener">{esc(p["source"])}</a>.</p>{missing}</div>')
            body = f'{head}{note}{nav}<article class="mirror-text">{inner}</article>{nav}'
            title = p.get("title") or m["title"]
            (bout / p["file"]).write_text(page(site, title=f"{title} — {m['title']}", body=body, depth=2, body_class="mirror"), encoding="utf-8")
        toc = "".join(f'<li><a href="{esc(p["file"])}">{esc(p.get("title") or p["file"])}</a></li>' for p in pages)
        pd = f'<p><strong>Copyright status:</strong> {esc(m.get("basis") or "")}' + (
            f' The archive says: “{esc(m["public_domain_statement"])}”' if m.get("public_domain_statement") else "") + "</p>"
        sec = secs.get(m.get("section"), {})
        body = f"""{head}
<p class="kicker">Mirrored from sacred-texts.com{(' · ' + esc(sec['title'])) if sec else ''}</p>
<h1>{esc(m['title'])}</h1>
<p class="lede">{esc(m.get('author') or '')}{(' · ' + esc(str(m['year']))) if m.get('year') else ''}</p>
<div class="note mirror-note"><p>{TERMS_NOTE}</p><p>Attribution: {esc(book_attrib or m['title'] + ', at sacred-texts.com')} · original: <a href="{esc(m['start'])}" rel="noopener">{esc(m['start'])}</a> · downloaded {esc(m.get('fetched', ''))}.</p>{pd}</div>
<h2>Contents</h2>
<ol class="mirror-toc">{toc}</ol>"""
        (bout / "index.html").write_text(page(site, title=m["title"], body=body, depth=2, body_class="mirror"), encoding="utf-8")

    rows = "".join(
        f'<li class="work"><a href="{esc(m["id"])}/index.html">{esc(m["title"])}</a>'
        f'<span class="w-meta">{esc(m.get("author") or "")} · {len(m.get("pages", []))} pages · downloaded {esc(m.get("fetched", ""))}</span></li>'
        for m in books)
    waiting = [x for x in planned if x["id"] not in done_ids]
    wait_html = ("<h2>Queued</h2><p class=\"muted\">Listed in <code>data/sacred-texts-mirror.yaml</code> and downloaded on the next run of the site's build workflow.</p><ul class=\"works\">"
                 + "".join(f'<li class="work">{esc(x["title"])}<span class="w-meta">{esc(x.get("author") or "")}</span></li>' for x in waiting)
                 + "</ul>") if waiting else ""
    body = f"""<nav class="crumbs"><a href="../index.html">Home</a> › <a href="../sacred-texts.html">sacred-texts.com collection</a></nav>
<h1>Books mirrored from sacred-texts.com</h1>
<p class="lede">Full copies of selected public-domain books from the Internet Sacred Text Archive, kept here so they can be read beside the archive's own texts.</p>
<div class="note"><p>{TERMS_NOTE.replace("This page is", "These copies are")} Each page keeps the archive's attribution line and links to its original. To support the archive, buy it on <a href="https://sacred-texts.com/cdshop/index.htm" rel="noopener">DVD or USB</a>.</p></div>
{('<ul class="works">' + rows + '</ul>') if rows else '<p class="muted">No books have been downloaded yet.</p>'}
{wait_html}"""
    (mdir / "index.html").write_text(page(site, title="Books mirrored from sacred-texts.com", body=body, depth=1), encoding="utf-8")
    return books
