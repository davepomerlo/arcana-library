# Contributing

Thank you for helping. These are the most useful contributions, roughly in order:

1. **Check an original text.** Pick a page marked *○ unchecked* or *≈ partly checked*, compare its original with the edition named on the page, and fix any differences. Then update `status` and `check_note`.
2. **Correct a translation.** If you read the language, improve accuracy. Keep the line-by-line layout so readers can compare.
3. **Add a text.** Start from `content/TEMPLATE.md` (see the README).
4. **Add Library entries.** Add reliable editions to `content/catalog/*.yaml`.

## Rules for new texts

- **Original first.** Give the original-language text from a named edition. If you cannot give the original, the page should be a *research article* (`translation.type: original-research`) and not a translation.
- **No copyrighted material.** Do not paste modern translations or articles, even short ones, unless their licence allows it. Link them in `compare` or the Library instead. Quotations in research articles should be short and attributed.
- **Label honestly.** Use `ai-assisted` for any translation made with AI help, `public-domain` only when the translator died long enough ago, or the work was published before 1930 (the US rule), and say which edition you used.
- **Mark checking status.** Use `checked` only when you have compared the original line by line with the edition.
- **Paranormal case files** set out what the primary sources say, where they disagree, the main interpretations, and an assessment. They do not take sides beyond what the evidence supports.

## Before submitting

```
python tools/check_texts.py
python build.py --serve
```
