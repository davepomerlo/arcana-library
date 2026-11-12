# Arcana Library

An open archive of **ancient and sacred texts, philosophy and metaphysics, the esoteric traditions, the paranormal, and extraterrestrial life and UAP**. Texts are shown **in the original language beside the translation**, and every page states its sources and how far it has been checked.

It is a static website: plain Markdown files go in, a fast, searchable site comes out. It is hosted free on GitHub Pages and works on phones and desktops.

## What's inside

| | |
|---|---|
| **54 texts** | Full or excerpted originals in 23 languages (Classical Chinese, Japanese, Sanskrit, Pali, Tibetan, Avestan, Coptic, Hebrew, Greek, Latin, Persian, Akkadian, Sumerian, Egyptian, Old Norse, Middle English, French, Finnish, Hawaiian, Māori, K'iche' Maya, Quechua and Zulu), each with a new line-by-line translation. Cosmogonies from Egypt, Sumer, China, Japan, Korea, Vietnam, India, Iran, Greece, Finland, southern Africa, the Andes, the Maya, Hawaiʻi and Aotearoa, plus Plotinus, and the 'many worlds' of Epicurus, Lucretius and Bruno. Every page says which edition it was checked against: of all 72 pages, 36 are fully checked and 32 partly |
| **18 case files and guides** | Research articles on the Utsuro-bune (1803), the Nuremberg 1561 sky battle, the SPR Census of Hallucinations, the Green Children of Woolpit, Shiranui and the Hessdalen lights; the Ra Material (Law of One); and research guides to African creation traditions, creation sources from more regions (Haudenosaunee, Aztec, Ainu, Siberia, Southeast Asia, Aboriginal Australia), ancient texts recovered since 1945, channelled literature, sex magic in history, shamanism, breath and meditation science, the official UFO/UAP investigations (Blue Book to AARO and NASA), the scientific search for life (SETI to K2-18 b and 3I/ATLAS), and contact claims |
| **Library** | 178 reliable editions, translations, archives and university studies, and 49 digital libraries, with a note on what each is good for. A separate page sorts all 1,696 titles of [sacred-texts.com](https://sacred-texts.com) into 52 subjects and links to them (`tools/sacred_texts.py`, `data/sacred-texts-titles.txt`); selected public-domain books are mirrored in full, with their attribution kept, by `tools/mirror_sacred_texts.py` (list in `data/sacred-texts-mirror.yaml`, run by the build workflow) |
| **Channelling tracker** | A weekly GitHub Action records new L/L Research transcripts (links and Wayback Machine snapshots only, since the material is copyright) |
| **Reading** | Side-by-side, translation-only or original-only reading; romanization toggle; read-aloud with the device's own voice; save texts to “My shelf” and resume where you stopped; cuneiform and hieroglyph samples in bundled Noto fonts |
| **Finding** | Full-text search in every language with filters by section, language, region, era, theme and checking status; 22 cross-cultural theme pages (cosmic egg, sky and earth pulled apart, world from a body…); world map with a time slider; timeline; tradition pages |
| **App** | Installable on phones and computers and readable offline after the first visit (web app manifest and service worker) |
| **Open data** | `data/texts.json` and `.csv` (every text, its metadata and each original/translation passage), Library JSON/CSV, `CITATION.cff` and Zenodo metadata for a DOI |
| **Quality** | “Suggest a correction or source” form on every page (GitHub issue forms), named language reviewers and an “expert reviewed” level, weekly broken-link check that opens an issue, internal link check on every build |
| **Weekly trackers** | New L/L Research transcripts (links only) and new scholarship from OpenAlex on the archive's subjects (research-feed page) |

## Put it online (one time, about 10 minutes)

1. **Create the repository.** On github.com, click **New repository**, name it `arcana-library` (or anything you like), make it **Public**, and click **Create repository**. Don't add a README.
2. **Upload the files.** On the new repository's page, click **uploading an existing file**. Drag in *everything inside* this folder, including the hidden `.github` folder. On Windows, turn on *View → Show → Hidden items* in File Explorer to see it. Click **Commit changes**.
   - Or, with Git installed: `git init && git add . && git commit -m "First version" && git branch -M main && git remote add origin https://github.com/YOUR-NAME/arcana-library.git && git push -u origin main`
3. **Turn on Pages.** Go to **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. Wait a minute or two. The **Actions** tab shows the build. Your site will be at `https://YOUR-NAME.github.io/arcana-library/`.

Every time you add or change a file on GitHub, the site rebuilds by itself.

> If you name the repository something else, change `repo_url` and `site_url` in `site.yaml` so the correction forms and data links work.

### Optional: get a permanent DOI (Zenodo)

1. Sign in at [zenodo.org](https://zenodo.org) with your GitHub account, open **GitHub** in your Zenodo settings and switch the repository **on**.
2. On GitHub, create a release (**Releases → Draft a new release**, tag `v1.0`). Zenodo archives it and gives it a DOI, using the details in `.zenodo.json`.
3. Put the DOI in `site.yaml` (`doi: 10.5281/zenodo.…`); it then appears on the Download page.

### Optional: polite contact address for OpenAlex

The weekly scholarship tracker works without it, but OpenAlex prefers an address. Add a repository secret named `OPENALEX_MAILTO` (Settings → Secrets and variables → Actions); the workflow passes it on automatically.

## Add a text

1. Copy `content/TEMPLATE.md` into the right folder: `content/texts/ancient-sacred/`, `philosophy/`, `esoteric/`, `paranormal/` or `extraterrestrial/`. Or run `python tools/new_text.py esoteric "Title of the text"`.
2. Fill in the details at the top (title, original title, date, language, sources, translation type, checking status).
3. Add a line for it to `data/geo.yaml` (map position, region and themes). The build warns if you forget.
4. Write the text in **parallel blocks**: the original, a line with `---`, then the translation.

```
::: parallel 1
道可道，非常道。
---
The Dao that can be told is not the constant Dao.
:::
```

   A middle part becomes an optional romanization line, which readers can switch on:

```
::: parallel 1
ॐ पूर्णमदः पूर्णमिदं
---
oṃ pūrṇam adaḥ pūrṇam idam
---
Om. That is full; this is full.
:::
```

   Use `::: note Heading` … `:::` for boxed notes. Everything else is ordinary Markdown.

You can do all of this in the GitHub website: open a folder, then **Add file → Create new file**.

To add a link to the **Library**, add an entry to the right file in `content/catalog/`.

## Preview on your own computer (optional)

Requires Python 3.9+.

```
pip install -r requirements.txt
python tools/check_texts.py      # finds mistakes in text files
python build.py --serve          # then open http://localhost:8000
```

## Project layout

```
site.yaml                 site name, sections, label wording, site_url, DOI
content/texts/<section>/  one Markdown file per text
content/reviewers.yaml    named language reviewers
data/geo.yaml             map position, region and themes for each text
data/themes.yaml          the cross-cultural themes
data/*.json               tracker output (channelling index, new scholarship, link report)
content/catalog/*.yaml    Library entries and digital libraries
content/pages/about.md    About & sources policy page
content/TEMPLATE.md       starting point for a new text
assets/                   style.css, app.js, icons, Noto cuneiform/hieroglyph fonts (OFL)
build.py, extras.py       turn content into the site in _site/ (extras: map, themes, shelf, data, app files)
tools/                    new_text.py, check_texts.py, check_internal_links.py, check_links.py,
                          track_llresearch.py, track_scholarship.py, sw-template.js
.github/workflows/        automatic build and publish to GitHub Pages
```

## Translation and copyright policy

- **AI-assisted translations** are labelled as such, sit beside the original and link to a published translation for comparison.
- Each page has a **checking status** (expert reviewed, checked, partly checked or unchecked) saying how far the original-language text has been compared with a printed edition. Unchecked texts are where help is most needed.
- The archive does **not** copy copyrighted modern translations or articles. Those are linked in the Library.

## Licence

- Code (`build.py`, `assets/`, `tools/`): MIT.
- Translations, notes and case files written for this archive: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- Original ancient texts are in the public domain. Check each page for the edition used.
