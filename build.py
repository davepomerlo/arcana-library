#!/usr/bin/env python3
"""Build the Arcana Library static site.

Usage:
    python build.py            # builds into ./_site
    python build.py --serve    # builds, then serves on http://localhost:8000

Needs Python 3.9+ and two packages:  pip install markdown pyyaml
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = ROOT / "_site"

LANG_NAMES = {
    "lzh": "Classical Chinese", "zh": "Chinese", "ja": "Japanese", "ojp": "Old Japanese",
    "sa": "Sanskrit", "pi": "Pali", "la": "Latin", "grc": "Ancient Greek", "he": "Hebrew",
    "arc": "Aramaic", "fa": "Persian", "ar": "Arabic", "non": "Old Norse", "egy": "Egyptian",
    "akk": "Akkadian", "sux": "Sumerian", "cop": "Coptic", "de": "German", "fr": "French",
    "en": "English", "enm": "Middle English", "it": "Italian", "es": "Spanish",
}
RTL = {"he", "arc", "ar", "fa"}


# --------------------------------------------------------------------------- helpers

def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "x"


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def year_label(y: int | None) -> str:
    if y is None:
        return ""
    return f"{-y} BCE" if y < 0 else f"{y} CE"


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def read_front_matter(path: Path):
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("\n---", 1)
        meta = yaml.safe_load(parts[0][3:]) or {}
        body = parts[1].lstrip("-").lstrip("\n") if len(parts) > 1 else ""
        return meta, body
    return {}, raw


# --------------------------------------------------------------------------- markdown

PAR_RE = re.compile(r"^:::[ \t]*parallel[ \t]*(?P<label>[^\n]*)\n(?P<inner>.*?)\n:::[ \t]*$", re.M | re.S)
NOTE_RE = re.compile(r"^:::[ \t]*note[ \t]*(?P<label>[^\n]*)\n(?P<inner>.*?)\n:::[ \t]*$", re.M | re.S)


def md_block(text: str, verse: bool = True) -> str:
    exts = ["extra", "sane_lists", "smarty"] + (["nl2br"] if verse else [])
    return markdown.markdown(text.strip(), extensions=exts)


def render_body(body: str, lang: str):
    """Turn the Markdown body into HTML, handling ::: parallel and ::: note blocks."""
    blocks: dict[str, str] = {}

    def par(m):
        parts = re.split(r"^---[ \t]*$", m.group("inner"), flags=re.M)
        parts = [p.strip("\n") for p in parts]
        label = m.group("label").strip()
        orig = parts[0]
        roman = parts[1] if len(parts) == 3 else None
        trans = parts[-1] if len(parts) >= 2 else ""
        d = ' dir="rtl"' if lang in RTL else ""
        h = ['<div class="par">']
        if label:
            h.append(f'<div class="par-n" aria-hidden="true">{esc(label)}</div>')
        h.append(f'<div class="par-o" lang="{esc(lang)}"{d}>{md_block(orig)}</div>')
        if roman is not None:
            h.append(f'<div class="par-r">{md_block(roman)}</div>')
        h.append(f'<div class="par-t" lang="en">{md_block(trans)}</div>')
        h.append("</div>")
        key = f"BLOCKTOKEN{len(blocks):05d}"
        blocks[key] = "".join(h)
        return f"\n\n{key}\n\n"

    def note(m):
        label = m.group("label").strip() or "Note"
        key = f"BLOCKTOKEN{len(blocks):05d}"
        blocks[key] = (f'<aside class="note"><div class="note-h">{esc(label)}</div>'
                       f'{md_block(m.group("inner"), verse=False)}</aside>')
        return f"\n\n{key}\n\n"

    body = PAR_RE.sub(par, body)
    body = NOTE_RE.sub(note, body)
    md = markdown.Markdown(extensions=["extra", "sane_lists", "smarty", "toc"],
                           extension_configs={"toc": {"permalink": False}})
    out = md.convert(body)
    for k, v in blocks.items():
        out = out.replace(f"<p>{k}</p>", v).replace(k, v)
    toc = getattr(md, "toc_tokens", [])
    return out, toc


# --------------------------------------------------------------------------- loading

def load_site():
    return yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8"))


def load_texts(site):
    sec_slugs = {s["slug"] for s in site["sections"]}
    texts = []
    for p in sorted((CONTENT / "texts").rglob("*.md")):
        meta, body = read_front_matter(p)
        if meta.get("draft"):
            continue
        meta["slug"] = meta.get("slug") or p.stem
        meta.setdefault("section", p.parent.name)
        if meta["section"] not in sec_slugs:
            print(f"  ! {p.name}: unknown section '{meta['section']}'", file=sys.stderr)
            continue
        meta["traditions"] = as_list(meta.get("tradition"))
        meta["tags"] = as_list(meta.get("tags"))
        meta["lang"] = meta.get("lang", "en")
        meta["body_html"], meta["toc"] = render_body(body, meta["lang"])
        meta["kind"] = meta.get("kind", "text")
        meta["src_path"] = p.relative_to(ROOT).as_posix()
        texts.append(meta)
    texts.sort(key=lambda t: (t.get("year") if t.get("year") is not None else 9999, t["title"]))
    return texts


def load_catalog():
    works, libraries = [], []
    for p in sorted((CONTENT / "catalog").glob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for w in data.get("works", []) or []:
            w["traditions"] = as_list(w.get("tradition"))
            w["section"] = w.get("section") or data.get("section")
            works.append(w)
        libraries.extend(data.get("libraries", []) or [])
    return works, libraries


# --------------------------------------------------------------------------- templates

def page(site, *, title, body, depth, description=None, body_class=""):
    r = "../" * depth
    nav_secs = "".join(
        f'<a href="{r}sections/{s["slug"]}.html">{esc(s.get("short", s["title"]))}</a>' for s in site["sections"])
    full_title = esc(title) + (" · " + esc(site["name"]) if title != site["name"] else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{esc(description or site['description'])}">
<link rel="stylesheet" href="{r}assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>☉</text></svg>">
<script>try{{var t=localStorage.getItem('arc-theme');if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
</head>
<body class="{body_class}" data-root="{r}">
<a class="skip" href="#main">Skip to content</a>
<header class="site-h">
  <div class="wrap hbar">
    <a class="brand" href="{r}index.html"><span class="brand-g">☉</span> {esc(site['name'])}</a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav" type="button">Menu</button>
    <nav id="nav" class="nav">
      {nav_secs}
      <a href="{r}library.html">Library</a>
      <a href="{r}timeline.html">Timeline</a>
      <a href="{r}search.html">Search</a>
      <a href="{r}about.html">About</a>
      <button class="theme-btn" type="button" aria-label="Switch light or dark theme">☾</button>
    </nav>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer class="site-f">
  <div class="wrap">
    <p>{esc(site['name'])} · an open archive. Texts are public domain or newly translated for this site; each page states its sources.</p>
    <p><a href="{r}about.html">Sources &amp; translation policy</a> · <a href="{esc(site.get('repo_url', '#'))}">Source on GitHub</a> · Built {date.today().isoformat()}</p>
  </div>
</footer>
<script src="{r}assets/app.js"></script>
</body>
</html>"""


def badges(site, t):
    out = []
    tr = (t.get("translation") or {}).get("type")
    if tr:
        lab = site["translation_labels"].get(tr, {}).get("label", tr)
        out.append(f'<span class="badge b-{esc(tr)}">{esc(lab)}</span>')
    st = t.get("status")
    if st:
        out.append(f'<span class="badge s-{esc(st)}" title="{esc(site["status_labels"].get(st, st))}">'
                   f'{ {"checked": "✓ checked", "partly-checked": "≈ partly checked", "unchecked": "○ unchecked"}.get(st, st) }</span>')
    return "".join(out)


def text_card(site, t, r):
    orig = f'<span class="card-orig" lang="{esc(t["lang"])}">{esc(t["original_title"])}</span>' if t.get("original_title") else ""
    trad = " · ".join(esc(x) for x in t["traditions"])
    return f"""<article class="card">
  <h3><a href="{r}texts/{esc(t['slug'])}.html">{esc(t['title'])}</a> {orig}</h3>
  <p class="card-meta">{esc(t.get('date', ''))}{' · ' if t.get('date') and trad else ''}{trad}</p>
  <p>{esc(t.get('summary', ''))}</p>
  <p class="card-b">{badges(site, t)}</p>
</article>"""


def work_row(w):
    kinds = {"primary": "Original text", "translation": "Translation", "edition": "Critical edition",
             "study": "Study", "collection": "Collection", "archive": "Archive", "report": "Report"}
    k = kinds.get(w.get("kind", ""), w.get("kind", ""))
    meta = " · ".join(x for x in [esc(w.get("author", "")), esc(w.get("date", "")),
                                   esc(w.get("language", "")), esc(k)] if x)
    trans = f'<span class="w-tr">Translation: {esc(w["translator"])}</span>' if w.get("translator") else ""
    note = f'<p class="w-note">{esc(w["note"])}</p>' if w.get("note") else ""
    trad = " ".join(esc(x) for x in w["traditions"])
    hay = " ".join(str(w.get(k_, "")) for k_ in ("title", "author", "note", "translator", "language")) + " " + trad
    return f"""<li class="work" data-sec="{esc(w.get('section', ''))}" data-hay="{esc(hay.lower())}">
  <a href="{esc(w['url'])}" rel="noopener">{esc(w['title'])}</a>
  <span class="w-meta">{meta}</span>{trans}{note}
</li>"""


def text_page(site, t, sec, works_by_trad):
    r = "../"
    tr = t.get("translation") or {}
    tr_type = tr.get("type")
    tr_info = site["translation_labels"].get(tr_type, {})
    langname = LANG_NAMES.get(t["lang"], t["lang"])
    rows = []
    for label, val in [("Author", t.get("author")),
                       ("Date", t.get("date")), ("Language", t.get("language") or langname),
                       ("Region", t.get("region")),
                       ("Tradition", ", ".join(t["traditions"]))]:
        if val:
            v = esc(val)
            if label == "Original title":
                v = f'<span lang="{esc(t["lang"])}">{v}</span>'
            if label == "Tradition":
                v = ", ".join(f'<a href="{r}traditions/{slugify(x)}.html">{esc(x)}</a>' for x in t["traditions"])
            rows.append(f"<dt>{label}</dt><dd>{v}</dd>")

    src = t.get("original_source") or {}
    src_html = ""
    if src:
        link = f' — <a href="{esc(src["url"])}" rel="noopener">view source</a>' if src.get("url") else ""
        src_html = f'<p><strong>Original text:</strong> {esc(src.get("edition", ""))}{link}</p>'
    compare = ""
    if t.get("compare"):
        items = "".join(f'<li><a href="{esc(c["url"])}" rel="noopener">{esc(c["label"])}</a></li>' for c in t["compare"])
        compare = f'<p><strong>Compare with:</strong></p><ul class="compare">{items}</ul>'
    status = t.get("status")
    status_html = f'<p><strong>Checking:</strong> {esc(site["status_labels"].get(status, status))}.</p>' if status else ""
    check_note = f'<p class="muted">{esc(t["check_note"])}</p>' if t.get("check_note") else ""
    prov = f"""<aside class="prov">
  <div class="prov-h">{badges(site, t)}</div>
  <p><strong>{esc(tr_info.get('label', 'Translation'))}</strong>{(' by ' + esc(tr['by'])) if tr.get('by') else ''}. {esc(tr.get('note') or tr_info.get('note', ''))}</p>
  {src_html}{status_html}{check_note}{compare}
</aside>"""

    has_par = 'class="par"' in t["body_html"]
    has_roman = 'class="par-r"' in t["body_html"]
    controls = ""
    if has_par:
        rb = '<button type="button" data-roman>Romanization</button>' if has_roman else ""
        controls = f"""<div class="view-ctl" role="group" aria-label="Reading view">
  <button type="button" data-view="both" aria-pressed="true">Side by side</button>
  <button type="button" data-view="trans">Translation</button>
  <button type="button" data-view="orig">Original</button>{rb}
</div>"""

    toc_html = ""
    flat = []
    for tok in t["toc"]:
        flat.append(tok)
    if len(flat) >= 3:
        items = "".join(f'<li><a href="#{esc(x["id"])}">{esc(strip_tags(x["name"]))}</a></li>' for x in flat)
        toc_html = f'<details class="toc"><summary>Contents ({len(flat)})</summary><ol>{items}</ol></details>'

    sources = ""
    if t.get("sources"):
        items = "".join(
            f'<li>{esc(s["label"])}' + (f' — <a href="{esc(s["url"])}" rel="noopener">link</a>' if s.get("url") else "") + "</li>"
            for s in t["sources"])
        sources = f'<section class="srcs"><h2>Sources &amp; further reading</h2><ul>{items}</ul></section>'

    related = []
    for trad in t["traditions"]:
        related.extend(works_by_trad.get(trad, []))
    seen, rel_items = set(), []
    for w in related:
        if w["url"] in seen:
            continue
        seen.add(w["url"])
        rel_items.append(work_row(w))
    rel_html = ""
    if rel_items:
        rel_html = (f'<section class="srcs"><h2>More from the Library</h2>'
                    f'<ul class="works">{"".join(rel_items[:8])}</ul></section>')

    cite = (f'<section class="srcs"><h2>Cite this page</h2><p class="muted">“{esc(t["title"])}”, '
            f'{esc(site["name"])}, {esc(tr.get("by", ""))} {esc(tr.get("year", ""))}. '
            f'Translation type: {esc(tr_info.get("label", ""))}.</p>'
            f'<p class="muted">Spotted an error? <a href="{esc(site.get("repo_url", "#"))}/blob/main/{esc(t["src_path"])}">Edit this page on GitHub</a>.</p></section>')

    body = f"""<nav class="crumbs"><a href="{r}index.html">Home</a> › <a href="{r}sections/{sec['slug']}.html">{esc(sec['title'])}</a></nav>
<article class="text">
<header class="text-h">
  <h1>{esc(t['title'])}</h1>
  {f'<p class="orig-title" lang="{esc(t["lang"])}">{esc(t["original_title"])}</p>' if t.get('original_title') else ''}
  <p class="lede">{esc(t.get('summary', ''))}</p>
  <dl class="meta">{''.join(rows)}</dl>
</header>
{prov}
{t.get('intro_html', '')}
{controls}
{toc_html}
<div class="text-body">
{t['body_html']}
</div>
{sources}
{rel_html}
{cite}
</article>"""
    return page(site, title=t["title"], body=body, depth=1, description=t.get("summary"), body_class="view-both")


# --------------------------------------------------------------------------- build

def build():
    site = load_site()
    texts = load_texts(site)
    works, libraries = load_catalog()
    secs = {s["slug"]: s for s in site["sections"]}

    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ("texts", "sections", "traditions", "assets"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "assets").iterdir():
        shutil.copy(f, OUT / "assets" / f.name)
    (OUT / ".nojekyll").write_text("")

    works_by_trad: dict[str, list] = {}
    for w in works:
        for tr in w["traditions"]:
            works_by_trad.setdefault(tr, []).append(w)

    # text pages
    for t in texts:
        (OUT / "texts" / f"{t['slug']}.html").write_text(
            text_page(site, t, secs[t["section"]], works_by_trad), encoding="utf-8")

    # section pages
    for s in site["sections"]:
        r = "../"
        st = [t for t in texts if t["section"] == s["slug"]]
        sw = [w for w in works if w.get("section") == s["slug"]]
        groups: dict[str, list] = {}
        for t in st:
            groups.setdefault(t["traditions"][0] if t["traditions"] else "Other", []).append(t)
        g_html = "".join(
            f'<h2 id="{slugify(g)}">{esc(g)}</h2><div class="cards">{"".join(text_card(site, t, r) for t in items)}</div>'
            for g, items in sorted(groups.items()))
        wg: dict[str, list] = {}
        for w in sw:
            wg.setdefault(w["traditions"][0] if w["traditions"] else "Other", []).append(w)
        w_html = "".join(
            f'<h3>{esc(g)}</h3><ul class="works">{"".join(work_row(w) for w in items)}</ul>'
            for g, items in sorted(wg.items()))
        body = f"""<nav class="crumbs"><a href="{r}index.html">Home</a></nav>
<header class="sec-h"><span class="sec-g">{esc(s['glyph'])}</span><h1>{esc(s['title'])}</h1><p class="lede">{esc(s['blurb'])}</p>
<p class="muted">{len(st)} texts in the archive · {len(sw)} works in the Library</p></header>
<h2 class="band">In the archive</h2>
{g_html or '<p class="muted">Nothing here yet.</p>'}
<h2 class="band">In the Library <span class="muted">(external, reliable editions)</span></h2>
{w_html or '<p class="muted">Nothing here yet.</p>'}"""
        (OUT / "sections" / f"{s['slug']}.html").write_text(
            page(site, title=s["title"], body=body, depth=1, description=s["blurb"]), encoding="utf-8")

    # tradition pages
    all_trads = sorted({x for t in texts for x in t["traditions"]} | set(works_by_trad))
    for trad in all_trads:
        r = "../"
        tt = [t for t in texts if trad in t["traditions"]]
        ww = works_by_trad.get(trad, [])
        body = f"""<nav class="crumbs"><a href="{r}index.html">Home</a> › <a href="{r}traditions/index.html">Traditions</a></nav>
<h1>{esc(trad)}</h1>
{'<h2 class="band">In the archive</h2><div class="cards">' + ''.join(text_card(site, t, r) for t in tt) + '</div>' if tt else ''}
{'<h2 class="band">In the Library</h2><ul class="works">' + ''.join(work_row(w) for w in ww) + '</ul>' if ww else ''}"""
        (OUT / "traditions" / f"{slugify(trad)}.html").write_text(
            page(site, title=trad, body=body, depth=1), encoding="utf-8")
    counts = {trad: (sum(trad in t["traditions"] for t in texts), len(works_by_trad.get(trad, []))) for trad in all_trads}
    trad_list = "".join(
        f'<li><a href="{slugify(trad)}.html">{esc(trad)}</a> <span class="muted">{a} texts · {b} library</span></li>'
        for trad, (a, b) in counts.items())
    (OUT / "traditions" / "index.html").write_text(
        page(site, title="Traditions", depth=1,
             body=f'<nav class="crumbs"><a href="../index.html">Home</a></nav><h1>Traditions</h1><ul class="trad-list">{trad_list}</ul>'),
        encoding="utf-8")

    # library page
    lib_secs = []
    for s in site["sections"]:
        sw = [w for w in works if w.get("section") == s["slug"]]
        wg: dict[str, list] = {}
        for w in sw:
            wg.setdefault(w["traditions"][0] if w["traditions"] else "Other", []).append(w)
        inner = "".join(f'<h3>{esc(g)}</h3><ul class="works">{"".join(work_row(w) for w in items)}</ul>'
                        for g, items in sorted(wg.items()))
        lib_secs.append(f'<section class="lib-sec" data-sec="{s["slug"]}"><h2 class="band">{esc(s["glyph"])} {esc(s["title"])}</h2>{inner}</section>')
    lib_items = "".join(
        f'<li class="work" data-hay="{esc((l["name"] + " " + l.get("note", "") + " " + " ".join(as_list(l.get("covers")))).lower())}">'
        f'<a href="{esc(l["url"])}" rel="noopener">{esc(l["name"])}</a>'
        f'<span class="w-meta">{esc(", ".join(as_list(l.get("covers"))))}</span>'
        f'<p class="w-note">{esc(l.get("note", ""))}</p></li>' for l in libraries)
    sec_btns = "".join(f'<button type="button" data-filter="{s["slug"]}">{esc(s["title"])}</button>' for s in site["sections"])
    body = f"""<h1>Library</h1>
<p class="lede">Reliable editions and translations held elsewhere: university projects, national libraries and long-running scholarly archives. Everything here is free to read online.</p>
<div class="filter">
  <input type="search" id="lib-q" placeholder="Filter by title, author, tradition, language…" aria-label="Filter the library">
  <div class="filter-b" role="group" aria-label="Section"><button type="button" data-filter="" aria-pressed="true">All</button>{sec_btns}</div>
  <p class="muted" id="lib-count"></p>
</div>
{''.join(lib_secs)}
<section class="lib-sec" data-sec="libraries"><h2 class="band">Digital libraries &amp; reference sites</h2>
<p class="muted">The collections the Library draws on, with a note on what each is good for and how far to trust it.</p>
<ul class="works">{lib_items}</ul></section>"""
    (OUT / "library.html").write_text(page(site, title="Library", body=body, depth=0, body_class="lib"), encoding="utf-8")

    # timeline
    events = [(t["year"], "text", t) for t in texts if t.get("year") is not None]
    events += [(w["year"], "work", w) for w in works if w.get("year") is not None]
    events.sort(key=lambda e: e[0])
    rows = []
    for y, kind, x in events:
        if kind == "text":
            link = f'<a href="texts/{esc(x["slug"])}.html">{esc(x["title"])}</a> <span class="badge">in archive</span>'
            sub = esc(x.get("date", ""))
        else:
            link = f'<a href="{esc(x["url"])}" rel="noopener">{esc(x["title"])}</a>'
            sub = esc(x.get("date", ""))
        trad = ", ".join(esc(z) for z in x["traditions"])
        rows.append(f'<li data-sec="{esc(x.get("section", ""))}"><span class="tl-y">{year_label(y)}</span>'
                    f'<div>{link}<br><span class="muted">{sub}{" · " if sub and trad else ""}{trad}</span></div></li>')
    body = f"""<h1>Timeline</h1>
<p class="lede">Archive texts and Library works placed by their approximate date of composition. Ancient dates are often disputed; the page for each text gives the range.</p>
<div class="filter"><div class="filter-b" role="group" aria-label="Section"><button type="button" data-filter="" aria-pressed="true">All</button>{sec_btns}</div></div>
<ol class="timeline">{''.join(rows)}</ol>"""
    (OUT / "timeline.html").write_text(page(site, title="Timeline", body=body, depth=0, body_class="tl"), encoding="utf-8")

    # search index + page
    index = []
    for t in texts:
        index.append({"t": t["title"], "o": t.get("original_title", ""), "u": f"texts/{t['slug']}.html",
                      "s": t.get("summary", ""), "x": secs[t["section"]]["title"], "k": "archive",
                      "g": " ".join(str(x) for x in t["traditions"] + t["tags"] + [t.get("author") or "", t.get("date") or ""]),
                      "b": strip_tags(t["body_html"])[:6000]})
    for w in works:
        index.append({"t": w["title"], "o": "", "u": w["url"], "s": w.get("note", ""),
                      "x": secs.get(w.get("section"), {}).get("title", ""), "k": "library",
                      "g": " ".join(w["traditions"] + [w.get("author", ""), w.get("translator", ""), w.get("language", "")]),
                      "b": ""})
    (OUT / "search-index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    body = """<h1>Search</h1>
<div class="filter"><input type="search" id="q" placeholder="Search titles, traditions, words in the texts (any language)…" aria-label="Search" autofocus>
<p class="muted" id="q-count"></p></div>
<ol class="results" id="results"></ol>"""
    (OUT / "search.html").write_text(page(site, title="Search", body=body, depth=0, body_class="search"), encoding="utf-8")

    # simple pages from content/pages
    for p in sorted((CONTENT / "pages").glob("*.md")):
        meta, body_md = read_front_matter(p)
        h, _ = render_body(body_md, "en")
        (OUT / f"{p.stem}.html").write_text(
            page(site, title=meta.get("title", p.stem.title()), body=f'<article class="prose">{h}</article>', depth=0),
            encoding="utf-8")

    # home
    r = ""
    sec_cards = "".join(
        f"""<a class="sec-card" href="sections/{s['slug']}.html"><span class="sec-g">{esc(s['glyph'])}</span>
<h2>{esc(s['title'])}</h2><p>{esc(s['blurb'])}</p>
<p class="muted">{sum(t['section'] == s['slug'] for t in texts)} texts · {sum(w.get('section') == s['slug'] for w in works)} library works</p></a>"""
        for s in site["sections"])
    featured = [t for t in texts if t.get("featured")][:6] or texts[:6]
    langs = sorted({LANG_NAMES.get(t["lang"], t["lang"]) for t in texts if t["lang"] != "en"})
    body = f"""<section class="hero">
<p class="hero-k">{esc(site['name'])}</p>
<h1>{esc(site['tagline'])}</h1>
<p class="lede">{esc(site['description'])}</p>
<form class="hero-s" action="search.html" method="get" role="search"><input type="search" name="q" placeholder="Search the archive…" aria-label="Search the archive"><button type="submit">Search</button></form>
<p class="muted">{len(texts)} texts in {len(langs)} original languages · {len(works)} works in the Library · {len(all_trads)} traditions · <a href="#" id="random-text">open a random text</a></p>
</section>
<div class="sec-grid">{sec_cards}</div>
<h2 class="band">Start here</h2>
<div class="cards">{''.join(text_card(site, t, r) for t in featured)}</div>
<h2 class="band">How to read this archive</h2>
<div class="how">
<p><span class="badge b-ai-assisted">AI-assisted translation</span> New translations made for this archive. They sit beside the original so you can check them, and every page links to a published scholarly translation for comparison.</p>
<p><span class="badge b-public-domain">Public-domain translation</span> Published translations whose copyright has expired.</p>
<p><span class="badge s-checked">✓ checked</span> <span class="badge s-partly-checked">≈ partly checked</span> <span class="badge s-unchecked">○ unchecked</span> How far the original-language text has been compared with a published edition.</p>
<p><a href="about.html">Read the full sources &amp; translation policy →</a></p>
</div>"""
    (OUT / "index.html").write_text(page(site, title=site["name"], body=body, depth=0, body_class="home"), encoding="utf-8")

    nf = '<h1>Page not found</h1><p>Try the <a href="search.html">search</a> or go back to the <a href="index.html">home page</a>.</p>'
    (OUT / "404.html").write_text(page(site, title="Not found", body=nf, depth=0), encoding="utf-8")

    print(f"Built {len(texts)} texts, {len(works)} library works, {len(libraries)} libraries, "
          f"{len(all_trads)} traditions → {OUT}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server
        import functools
        import socketserver
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        with socketserver.TCPServer(("", 8000), handler) as httpd:
            print("Serving on http://localhost:8000  (Ctrl+C to stop)")
            httpd.serve_forever()
