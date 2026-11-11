# Arcana Library

An open archive of **ancient and sacred texts, philosophy and metaphysics, the esoteric traditions and the paranormal**. Texts are shown **in the original language beside the translation**, and every page states its sources and how far it has been checked.

It is a static website: plain Markdown files go in, a fast, searchable site comes out. It is hosted free on GitHub Pages and works on phones and desktops.

## What's inside

| | |
|---|---|
| **50 texts** | Full or excerpted originals in 23 languages (Classical Chinese, Japanese, Sanskrit, Pali, Tibetan, Avestan, Coptic, Hebrew, Greek, Latin, Persian, Akkadian, Sumerian, Egyptian, Old Norse, Middle English, French, Finnish, Hawaiian, Māori, K'iche' Maya, Quechua and Zulu), each with a new line-by-line translation. Cosmogonies from Egypt, Sumer, China, Japan, Korea, India, Iran, Greece, Finland, southern Africa, the Andes, the Maya, Hawaiʻi and Aotearoa, plus Plotinus. Every page says which edition it was checked against: of all 64 pages, 30 are fully checked and 30 partly |
| **14 case files and guides** | Research articles on the Utsuro-bune (1803), the Nuremberg 1561 sky battle, the SPR Census of Hallucinations, the Green Children of Woolpit, Shiranui and the Hessdalen lights; the Ra Material (Law of One); and research guides to African creation traditions, ancient texts recovered since 1945, channelled literature, sex magic in history, shamanism, and breath and meditation science |
| **Library** | 151 reliable editions, translations, archives and university studies, and 49 digital libraries, with a note on what each is good for |
| **Channelling tracker** | A weekly GitHub Action records new L/L Research transcripts (links and Wayback Machine snapshots only, since the material is copyright) |
| **Features** | Side-by-side, translation-only or original-only reading; romanization toggle; full-text search in every language; timeline; tradition pages; light and dark themes |

## Put it online (one time, about 10 minutes)

1. **Create the repository.** On github.com, click **New repository**, name it `arcana-library` (or anything you like), make it **Public**, and click **Create repository**. Don't add a README.
2. **Upload the files.** On the new repository's page, click **uploading an existing file**. Drag in *everything inside* this folder, including the hidden `.github` folder. On Windows, turn on *View → Show → Hidden items* in File Explorer to see it. Click **Commit changes**.
   - Or, with Git installed: `git init && git add . && git commit -m "First version" && git branch -M main && git remote add origin https://github.com/YOUR-NAME/arcana-library.git && git push -u origin main`
3. **Turn on Pages.** Go to **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. Wait a minute or two. The **Actions** tab shows the build. Your site will be at `https://YOUR-NAME.github.io/arcana-library/`.

Every time you add or change a file on GitHub, the site rebuilds by itself.

> If you name the repository something else, change `repo_url` in `site.yaml` so the “Edit this page” links work.

## Add a text

1. Copy `content/TEMPLATE.md` into the right folder: `content/texts/ancient-sacred/`, `philosophy/`, `esoteric/` or `paranormal/`. Or run `python tools/new_text.py esoteric "Title of the text"`.
2. Fill in the details at the top (title, original title, date, language, sources, translation type, checking status).
3. Write the text in **parallel blocks**: the original, a line with `---`, then the translation.

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
site.yaml                 site name, sections, label wording
content/texts/<section>/  one Markdown file per text
content/catalog/*.yaml    Library entries and digital libraries
content/pages/about.md    About & sources policy page
content/TEMPLATE.md       starting point for a new text
assets/                   style.css and app.js
build.py                  turns content into the site in _site/
tools/                    new_text.py, check_texts.py
.github/workflows/        automatic build and publish to GitHub Pages
```

## Translation and copyright policy

- **AI-assisted translations** are labelled as such, sit beside the original and link to a published translation for comparison.
- Each page has a **checking status** (checked, partly checked or unchecked) saying how far the original-language text has been compared with a printed edition. Unchecked texts are where help is most needed.
- The archive does **not** copy copyrighted modern translations or articles. Those are linked in the Library.

## Licence

- Code (`build.py`, `assets/`, `tools/`): MIT.
- Translations, notes and case files written for this archive: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- Original ancient texts are in the public domain. Check each page for the edition used.
