"""Extra pages and files for the Arcana Library build.

Called from build.py after the main pages are written:
  themes/            one page per cross-cultural theme
  map.html           world map of the texts, with a time slider
  shelf.html         the reader's saved texts and reading progress (stored in the browser)
  contribute.html    how to help check translations; languages that need reviewers
  data.html + data/  downloadable dataset (JSON and CSV) and citation details
  research-feed.html new scholarship found by tools/track_scholarship.py
  manifest.webmanifest, sw.js, offline.html   installable, offline-capable app
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import date
from pathlib import Path

import yaml


def _parallel_blocks(body: str):
    """Return [{label, original, romanization, translation}] from ::: parallel blocks."""
    out = []
    for m in re.finditer(r"^:::[ \t]*parallel[ \t]*([^\n]*)\n(.*?)\n:::[ \t]*$", body, re.M | re.S):
        parts = re.split(r"^---[ \t]*$", m.group(2), flags=re.M)
        parts = [p.strip() for p in parts]
        if len(parts) == 2:
            o, rz, tr = parts[0], "", parts[1]
        elif len(parts) >= 3:
            o, rz, tr = parts[0], parts[1], parts[-1]
        else:
            continue
        out.append({"label": m.group(1).strip(), "original": o, "romanization": rz, "translation": tr})
    return out


def run(b, site, texts, works, libraries, secs):
    OUT, ROOT, esc, page = b.OUT, b.ROOT, b.esc, b.page
    THEMES, LANG_NAMES = b.THEMES, b.LANG_NAMES
    repo = site.get("repo_url", "")

    def card(t, r):
        return b.text_card(site, t, r)

    # ------------------------------------------------------------------ themes
    (OUT / "themes").mkdir(exist_ok=True)
    by_theme: dict[str, list] = {k: [] for k in THEMES}
    for t in texts:
        for th in t.get("themes", []):
            by_theme.setdefault(th, []).append(t)
    for key, info in THEMES.items():
        items = by_theme.get(key, [])
        cards = "".join(card(t, "../") for t in items)
        areas = sorted({t.get("area") for t in items if t.get("area")})
        body = f"""<nav class="crumbs"><a href="../index.html">Home</a> › <a href="index.html">Themes</a></nav>
<p class="kicker">Theme</p>
<h1>{esc(info['title'])}</h1>
<p class="lede">{esc(info.get('intro', ''))}</p>
<p class="muted">{len(items)} texts · {esc(', '.join(areas))} · <a href="../search.html?theme={esc(key)}">open in search with filters</a> · <a href="../map.html?theme={esc(key)}">show on the map</a></p>
<div class="cards">{cards}</div>"""
        (OUT / "themes" / f"{key}.html").write_text(
            page(site, title=info["title"], body=body, depth=1, description=info.get("intro")), encoding="utf-8")
    tl = "".join(
        f'<li><a href="{esc(k)}.html">{esc(v["title"])}</a> <span class="muted">{len(by_theme.get(k, []))} texts</span>'
        f'<br><span class="muted">{esc(v.get("intro", ""))}</span></li>'
        for k, v in sorted(THEMES.items(), key=lambda kv: -len(by_theme.get(kv[0], []))))
    body = f"""<nav class="crumbs"><a href="../index.html">Home</a></nav>
<h1>Themes</h1>
<p class="lede">The same images recur in creation stories and sacred texts across the world: the cosmic egg, sky and earth pulled apart, the world made from a body, the clear rising and the heavy sinking. Each theme gathers the texts that share it, so you can read them side by side.</p>
<ul class="trad-list theme-list">{tl}</ul>"""
    (OUT / "themes" / "index.html").write_text(page(site, title="Themes", body=body, depth=1), encoding="utf-8")

    # ------------------------------------------------------------------ map
    land = (ROOT / "data" / "world-land-path.txt").read_text(encoding="utf-8")
    W, H = 1000, 500
    pins, rows = [], []
    area_colors = {"Africa": "#b5651d", "West Asia": "#8e3b2f", "South Asia": "#c08a00", "East Asia": "#2f6f8e",
                   "Southeast Asia": "#2f8e74", "Europe": "#5b4a8e", "Americas": "#7a8e2f", "Oceania": "#1f7a9a",
                   "Worldwide": "#666666"}
    for t in sorted(texts, key=lambda x: (x.get("year") if x.get("year") is not None else 9999)):
        g = t.get("geo") or {}
        if "lat" not in g:
            continue
        x = (g["lon"] + 180) / 360 * W
        y = (90 - g["lat"]) / 180 * H
        col = area_colors.get(t.get("area", ""), "#666")
        yr = t.get("year") if t.get("year") is not None else 0
        th = " ".join(t.get("themes", []))
        pins.append(f'<a href="texts/{esc(t["slug"])}.html" class="pin" data-y="{yr}" data-sec="{esc(t["section"])}" data-th="{esc(th)}">'
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{col}"><title>{esc(t["title"])} ({esc(b.year_label(t.get("year")))})</title></circle></a>')
        rows.append(f'<li class="map-row" data-y="{yr}" data-sec="{esc(t["section"])}" data-th="{esc(th)}">'
                    f'<span class="dot" style="background:{col}"></span><span class="tl-y">{esc(b.year_label(t.get("year")))}</span> '
                    f'<a href="texts/{esc(t["slug"])}.html">{esc(t["title"])}</a> <span class="muted">{esc(t.get("region", ""))}</span></li>')
    legend = "".join(f'<span><span class="dot" style="background:{c}"></span>{esc(a)}</span>' for a, c in area_colors.items())
    sec_opts = "".join(f'<option value="{esc(k)}">{esc(v["title"])}</option>' for k, v in secs.items())
    theme_opts = "".join(f'<option value="{esc(k)}">{esc(v["title"])}</option>' for k, v in THEMES.items())
    years = [t["year"] for t in texts if t.get("year") is not None]
    ymin, ymax = (min(years), max(years)) if years else (-3000, 2026)
    body = f"""<h1>Map</h1>
<p class="lede">Every text in the archive, placed where it was composed or recorded. Move the slider to travel through time: only texts written by the year shown appear.</p>
<div class="map-ctl filter">
  <label class="year-lab">Up to <strong id="map-year-out"></strong>
    <input type="range" id="map-year" min="{ymin}" max="{max(ymax, date.today().year)}" step="10" value="{max(ymax, date.today().year)}" aria-label="Show texts written up to this year"></label>
  <button type="button" id="map-play" aria-pressed="false">▶ Play through history</button>
  <label>Section <select id="map-sec"><option value="">All</option>{sec_opts}</select></label>
  <label>Theme <select id="map-theme"><option value="">All</option>{theme_opts}</select></label>
  <span class="muted" id="map-count"></span>
</div>
<figure class="worldmap">
<svg viewBox="0 0 {W} {H}" role="img" aria-label="World map of the texts in the archive">
<rect width="{W}" height="{H}" class="sea"/>
<path d="{land}" class="land"/>
{''.join(pins)}
</svg>
<figcaption class="legend">{legend}</figcaption>
</figure>
<p class="muted">Positions are approximate (the city, region or monastery associated with the text). Coastlines: Natural Earth, public domain.</p>
<h2>All places</h2>
<ol class="map-list">{''.join(rows)}</ol>"""
    (OUT / "map.html").write_text(page(site, title="Map", body=body, depth=0, body_class="map"), encoding="utf-8")

    # ------------------------------------------------------------------ shelf
    body = """<h1>My shelf</h1>
<p class="lede">Texts you have saved, and how far you have read. This list is kept only in this browser, on this device; nothing is sent anywhere.</p>
<h2>Saved</h2>
<ul class="works" id="shelf-saved"><li class="muted">Nothing saved yet. Use “☆ Save to shelf” on any text.</li></ul>
<h2>Reading progress</h2>
<ul class="works" id="shelf-progress"><li class="muted">No reading progress yet.</li></ul>
<p><button type="button" id="shelf-export">Export my shelf (JSON)</button> <button type="button" id="shelf-clear">Clear everything</button></p>
<h2>Offline reading</h2>
<p>Install the Arcana Library as an app: in Chrome or Edge choose “Install app” (or “Add to Home screen” on Android); in Safari on iPhone use Share → “Add to Home Screen”. Once it has been opened online, the whole archive is stored on the device and can be read without a connection.</p>
<p class="muted" id="offline-state"></p>"""
    (OUT / "shelf.html").write_text(page(site, title="My shelf", body=body, depth=0, body_class="shelf"), encoding="utf-8")

    # ------------------------------------------------------------------ contribute / reviewers
    rv = yaml.safe_load((ROOT / "content" / "reviewers.yaml").read_text(encoding="utf-8")) or {}
    reviewers = rv.get("reviewers") or []
    per_lang: dict[str, dict] = {}
    for t in texts:
        if t["lang"] == "en":
            continue
        ln = LANG_NAMES.get(t["lang"], t["lang"])
        d = per_lang.setdefault(ln, {"pages": [], "reviewed": 0})
        d["pages"].append(t)
        if t.get("status") == "reviewed":
            d["reviewed"] += 1
    lang_rows = []
    for ln, d in sorted(per_lang.items(), key=lambda kv: -len(kv[1]["pages"])):
        names = [r["name"] for r in reviewers if ln in (r.get("languages") or [])]
        need = len(d["pages"]) - d["reviewed"]
        links = ", ".join(f'<a href="texts/{esc(t["slug"])}.html">{esc(t["title"])}</a>' for t in d["pages"][:6])
        more = f" and {len(d['pages']) - 6} more" if len(d["pages"]) > 6 else ""
        lang_rows.append(
            f'<tr><th scope="row">{esc(ln)}</th><td>{len(d["pages"])}</td><td>{need}</td>'
            f'<td>{esc(", ".join(names)) if names else "<em>wanted</em>"}</td><td class="muted">{links}{more}</td></tr>')
    rev_list = "".join(
        f'<li><strong>{esc(r["name"])}</strong>{(", " + esc(r["affiliation"])) if r.get("affiliation") else ""} — '
        f'{esc(", ".join(r.get("languages") or []))}</li>' for r in reviewers) or "<li class='muted'>No reviewers yet — be the first.</li>"
    body = f"""<h1>Help check the texts</h1>
<p class="lede">Every translation in this archive is new, and many were made with AI assistance. They become trustworthy when people who read the original languages check them. Here is how you can help.</p>
<h2>Report an error or suggest a source</h2>
<p>Every text page ends with a <strong>“Suggest a correction or source”</strong> link. It opens a short form on GitHub (a free account is needed) with the page already filled in. You can also <a href="{esc(b.issue_url(site, 'new-source.yml', 'Source suggestion: '))}" rel="noopener">suggest a new text or edition</a>.</p>
<h2>Become a language reviewer</h2>
<p>Reviewers are named on the pages they check, and those pages receive the <span class="badge s-reviewed">★ expert reviewed</span> badge, the highest level of checking on the site. To volunteer, <a href="{esc(b.issue_url(site, 'reviewer.yml', 'Reviewer: '))}" rel="noopener">fill in the reviewer form</a>.</p>
<h3>Languages and pages</h3>
<div class="table-wrap"><table class="lang-table"><thead><tr><th>Language</th><th>Pages</th><th>Still to review</th><th>Reviewers</th><th>Pages</th></tr></thead><tbody>{''.join(lang_rows)}</tbody></table></div>
<h3>Current reviewers</h3>
<ul>{rev_list}</ul>
<h2>The checking levels</h2>
<ul>
<li><span class="badge s-reviewed">★ expert reviewed</span> A named reviewer who reads the language has checked the original and the translation.</li>
<li><span class="badge s-checked">✓ checked</span> The original text has been compared with the published edition named on the page.</li>
<li><span class="badge s-partly-checked">≈ partly checked</span> Part of the original could be compared; the page says which part.</li>
<li><span class="badge s-unchecked">○ unchecked</span> Not yet compared with an edition.</li>
</ul>"""
    (OUT / "contribute.html").write_text(page(site, title="Help check the texts", body=body, depth=0), encoding="utf-8")

    # ------------------------------------------------------------------ sacred-texts.com catalogue
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools"))
    import sacred_texts as _st
    st_rows = _st.load()
    by_subj: dict[str, list] = {}
    for r_ in st_rows:
        by_subj.setdefault(r_["subject"], []).append(r_)
    order = [k for k in _st.SUBJECTS if k in by_subj]
    chips = " · ".join(f'<a href="#st-{b.slugify(k)}">{esc(k)} <span class="muted">{len(by_subj[k])}</span></a>' for k in order)
    groups = []
    for k in order:
        sec_slug, blurb, home = _st.SUBJECTS[k]
        sec_name = secs[sec_slug]["title"] if sec_slug in secs else "General"
        home_link = f' · <a href="{esc(home)}" rel="noopener">this subject at sacred-texts.com</a>' if home else ""
        lis = "".join(
            f'<li class="work" data-sec="{esc(sec_slug or "general")}"><a href="{esc(x["url"])}" rel="noopener">{esc(x["title"])}</a></li>'
            for x in by_subj[k])
        groups.append(f'<section class="lib-sec" id="st-{b.slugify(k)}"><h2 class="band">{esc(k)} <span class="muted">({len(by_subj[k])})</span></h2>'
                      f'<p class="muted">{esc(blurb)} Arcana section: {esc(sec_name)}{home_link}</p><ul class="works st-list">{lis}</ul></section>')
    sec_btns = "".join(f'<button type="button" data-filter="{s["slug"]}">{esc(s["title"])}</button>' for s in site["sections"])
    body = f"""<p class="kicker">Library · Partner collection</p>
<h1>The sacred-texts.com collection, classified</h1>
<p class="lede">The Internet Sacred Text Archive, founded by John Bruno Hare, holds more than 1,700 public-domain books on religion, myth, folklore and the esoteric. This page sorts the {len(st_rows):,} titles in its index into {len(order)} subjects and the matching sections of this archive, so you can find them alongside our own texts.</p>
<div class="note"><p><strong>Linked, not copied.</strong> The books stay at sacred-texts.com. Each title opens a web search limited to that site, because its page addresses cannot be predicted from the title. The archive's texts are believed to be in the US public domain; its own etexts may be copied for non-commercial use only with their attribution notice intact and a link back, so we link rather than mirror them. The title list comes from the archive's <a href="https://sacred-texts.com/cdshop/dvd90/titl90.htm" rel="noopener">alphabetical index</a>; to support it, buy the archive on <a href="https://sacred-texts.com/cdshop/index.htm" rel="noopener">DVD or USB</a>. The subjects are assigned by keyword rules (<code>tools/sacred_texts.py</code>) and may misplace a few titles: corrections are welcome.</p></div>
<div class="filter">
  <input type="search" id="lib-q" placeholder="Filter titles…" aria-label="Filter the titles">
  <div class="filter-b" role="group" aria-label="Section"><button type="button" data-filter="" aria-pressed="true">All</button>{sec_btns}<button type="button" data-filter="general">General</button></div>
  <p class="muted" id="lib-count"></p>
</div>
<p class="st-chips">{chips}</p>
{''.join(groups)}"""
    (OUT / "sacred-texts.html").write_text(page(site, title="The sacred-texts.com collection, classified", body=body, depth=0, body_class="lib"), encoding="utf-8")
    # add to the search index
    si = OUT / "search-index.json"
    idx = json.loads(si.read_text("utf-8"))
    for x in st_rows:
        idx.append({"t": x["title"], "o": "", "u": x["url"], "s": f"sacred-texts.com · {x['subject']}",
                    "x": secs.get(x["section"], {}).get("title", ""), "k": "library", "g": x["subject"] + " sacred-texts",
                    "b": "", "l": "", "y": None, "a": "", "st": "", "th": [], "sc": x["section"]})
    si.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------ data exports
    ddir = OUT / "data"
    ddir.mkdir(exist_ok=True)
    base_url = site.get("site_url", "").rstrip("/")
    records = []
    for t in texts:
        raw = (ROOT / t["src_path"]).read_text(encoding="utf-8")
        body = raw[3:].partition("\n---")[2]
        g = t.get("geo") or {}
        tr = t.get("translation") or {}
        records.append({
            "slug": t["slug"], "title": t["title"], "original_title": t.get("original_title"),
            "section": t["section"], "author": t.get("author"), "date": t.get("date"), "year": t.get("year"),
            "lang": t["lang"], "language": t.get("language") or LANG_NAMES.get(t["lang"], t["lang"]),
            "region": t.get("region"), "area": t.get("area"), "lat": g.get("lat"), "lon": g.get("lon"),
            "traditions": t["traditions"], "themes": t.get("themes", []), "tags": t["tags"],
            "summary": (t.get("summary") or "").strip(),
            "translation_type": tr.get("type"), "translated_by": tr.get("by"), "translation_year": tr.get("year"),
            "status": t.get("status"), "check_note": (t.get("check_note") or "").strip(),
            "original_source": t.get("original_source"), "compare": t.get("compare"), "sources": t.get("sources"),
            "reviewed_by": t.get("reviewed_by"),
            "page": f"{base_url}/texts/{t['slug']}.html" if base_url else f"texts/{t['slug']}.html",
            "blocks": _parallel_blocks(body),
        })
    meta = {"name": site["name"], "generated": date.today().isoformat(), "licence": site.get("data_licence", ""),
            "repository": repo, "count": len(records)}
    (ddir / "texts.json").write_text(json.dumps({"meta": meta, "texts": records}, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["slug", "title", "original_title", "section", "author", "date", "year", "lang", "language", "region",
            "area", "lat", "lon", "traditions", "themes", "translation_type", "status", "page"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for rec in records:
        w.writerow(["; ".join(map(str, rec[c])) if isinstance(rec[c], list) else ("" if rec[c] is None else rec[c]) for c in cols])
    (ddir / "texts.csv").write_text(buf.getvalue(), encoding="utf-8")
    lib = [{k: v for k, v in x.items() if k != "traditions"} | {"traditions": x["traditions"]} for x in works]
    (ddir / "library.json").write_text(json.dumps({"meta": meta | {"count": len(lib)}, "works": lib, "libraries": libraries},
                                                  ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    lcols = ["title", "author", "date", "year", "language", "kind", "translator", "url", "section", "traditions", "note"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(lcols)
    for x in works:
        w.writerow(["; ".join(x[c]) if isinstance(x.get(c), list) else ("" if x.get(c) is None else x.get(c)) for c in lcols])
    (ddir / "library.csv").write_text(buf.getvalue(), encoding="utf-8")
    (ddir / "themes.json").write_text(json.dumps(THEMES, ensure_ascii=False, indent=1), encoding="utf-8")
    (ddir / "sacred-texts.json").write_text(json.dumps({"meta": meta | {"count": len(st_rows), "source": "https://sacred-texts.com/cdshop/dvd90/titl90.htm"},
                                                        "titles": st_rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    sizes = {f.name: f.stat().st_size for f in ddir.iterdir()}
    kb = lambda n: f"{n / 1024:.0f} KB"
    doi = site.get("doi")
    doi_html = (f'<p>DOI: <a href="https://doi.org/{esc(doi)}">{esc(doi)}</a></p>' if doi else
                '<p class="muted">A permanent DOI will be added once the repository is archived on Zenodo (see the repository README for the one-time setup). Until then, cite the GitHub repository and the date.</p>')
    body = f"""<h1>Download the data</h1>
<p class="lede">The whole archive is available as open data: every text with its metadata, the original-language passages and their translations, the Library catalogue and the themes.</p>
<ul class="works">
<li class="work"><a href="data/texts.json" download>texts.json</a><span class="w-meta">{kb(sizes['texts.json'])} · {len(records)} texts with metadata, sources, checking status and every original/translation passage</span></li>
<li class="work"><a href="data/texts.csv" download>texts.csv</a><span class="w-meta">{kb(sizes['texts.csv'])} · one row per text (metadata only), for spreadsheets</span></li>
<li class="work"><a href="data/library.json" download>library.json</a><span class="w-meta">{kb(sizes['library.json'])} · {len(works)} Library works and {len(libraries)} digital libraries</span></li>
<li class="work"><a href="data/library.csv" download>library.csv</a><span class="w-meta">{kb(sizes['library.csv'])} · the Library as a table</span></li>
<li class="work"><a href="data/sacred-texts.json" download>sacred-texts.json</a><span class="w-meta">{kb(sizes['sacred-texts.json'])} · {len(st_rows)} sacred-texts.com titles with subject and section</span></li>
<li class="work"><a href="data/themes.json" download>themes.json</a><span class="w-meta">{kb(sizes['themes.json'])} · the cross-cultural themes</span></li>
</ul>
<h2>Licence and reuse</h2>
<p>{esc(site.get('data_licence_note', ''))}</p>
<h2>How to cite</h2>
<p class="cite-box">{esc(site['name'])} ({date.today().year}). <em>{esc(site.get('tagline', ''))}</em>. {esc(repo)}</p>
{doi_html}
<p class="muted">Citation details are also in <a href="{esc(repo)}/blob/main/CITATION.cff" rel="noopener">CITATION.cff</a>, which GitHub and Zotero read automatically.</p>"""
    (OUT / "data.html").write_text(page(site, title="Download the data", body=body, depth=0), encoding="utf-8")

    # ------------------------------------------------------------------ research feed
    feed_p = ROOT / "data" / "new-scholarship.json"
    feed = json.loads(feed_p.read_text(encoding="utf-8")) if feed_p.exists() else {}
    items = feed.get("items") or []
    by_topic: dict[str, list] = {}
    for it in items:
        by_topic.setdefault(it.get("topic", "Other"), []).append(it)
    secs_html = []
    for topic, its in sorted(by_topic.items()):
        lis = "".join(
            f'<li class="work"><a href="{esc(i.get("url") or "")}" rel="noopener">{esc(i.get("title", ""))}</a>'
            f'<span class="w-meta">{esc(i.get("authors", ""))}{" · " if i.get("authors") else ""}{esc(i.get("venue") or "")} · {esc(str(i.get("date") or i.get("year") or ""))}'
            f'{" · open access" if i.get("open_access") else ""}</span></li>' for i in its[:15])
        secs_html.append(f'<h2>{esc(topic)}</h2><ul class="works">{lis}</ul>')
    body = f"""<h1>New research</h1>
<p class="lede">Recent scholarly articles and books on the subjects of this archive, found automatically each week in OpenAlex, the open index of research publications. They are listed, not reviewed: inclusion is not an endorsement.</p>
<p class="muted">{len(items)} items · last updated {esc(feed.get('updated', 'not yet run'))} · topics and search terms are set in <a href="{esc(repo)}/blob/main/tools/track_scholarship.py" rel="noopener">tools/track_scholarship.py</a></p>
{''.join(secs_html) or '<p>The first weekly check has not run yet. It runs automatically on GitHub every Monday.</p>'}"""
    (OUT / "research-feed.html").write_text(page(site, title="New research", body=body, depth=0), encoding="utf-8")

    # ------------------------------------------------------------------ fonts: keep only the glyphs actually used
    used = {"Xsux": set(), "Egyp": set()}
    for t in texts:
        for x in t.get("script") or []:
            for k in used:
                if x.get("lang", "").endswith(k):
                    used[k].update(ch for ch in x["text"] if not ch.isspace())
    fonts = {"Xsux": "NotoSansCuneiform-Regular.ttf", "Egyp": "NotoSansEgyptianHieroglyphs-Regular.ttf"}
    for k, fname in fonts.items():
        dst = OUT / "assets" / "fonts" / fname
        if not dst.exists():
            continue
        try:
            from fontTools import subset
            opts = subset.Options()
            opts.layout_features = ["*"]
            font = subset.load_font(str(dst), opts)
            sub = subset.Subsetter(opts)
            sub.populate(unicodes=[ord(c) for c in used[k]] or [0x20])
            sub.subset(font)
            subset.save_font(font, str(dst), opts)
        except ImportError:
            pass  # keep the full font

    # ------------------------------------------------------------------ offline page, manifest, service worker
    body = """<h1>You are offline</h1>
<p class="lede">This page has not been saved on this device yet. Pages you have opened before, and the whole archive once the app has finished installing, can be read without a connection.</p>
<p><a href="index.html">Go to the home page</a> · <a href="shelf.html">My shelf</a></p>"""
    (OUT / "offline.html").write_text(page(site, title="Offline", body=body, depth=0), encoding="utf-8")
    manifest = {
        "name": site["name"], "short_name": site.get("short_name", "Arcana"),
        "description": " ".join(site["description"].split()),
        "start_url": "./index.html", "scope": "./", "display": "standalone",
        "background_color": "#f5efe3", "theme_color": "#f5efe3", "lang": "en",
        "icons": [
            {"src": "assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "assets/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (OUT / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*")
                   if p.is_file() and p.name not in (".nojekyll", "sw.js") and not p.name.endswith(".csv"))
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode())
        h.update((OUT / f).read_bytes())
    version = h.hexdigest()[:12]
    sw = (ROOT / "tools" / "sw-template.js").read_text(encoding="utf-8")
    sw = sw.replace("__VERSION__", version).replace("__FILES__", json.dumps(["./"] + files))
    (OUT / "sw.js").write_text(sw, encoding="utf-8")
