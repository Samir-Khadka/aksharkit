# Changelog

## 0.3.0 — 23 November 2026

### Added

- **Transliteration** (`aksharkit.translit`): `to_roman` and `to_devanagari`
  with two schemes.
  - `iast` — Roman letters with diacritics, IAST with ISO 15919 where IAST
    has no letter. Reversible: converting back gives the original text
    (conditions in `docs/transliteration.md`). Covers conjuncts, halant,
    anusvara, candrabindu, visarga, avagraha, nukta letters, digits and danda.
  - `simple` — plain ASCII as Nepali is typed in chat. Rule-based and
    approximate; documented rules decide when the final inherent `a` is
    dropped. Roman → Devanagari in this scheme is best effort only.
- `aksharkit translit --to roman|devanagari --scheme iast|simple [--keep-digits]`.
- `tests/golden/translit_words.tsv`: 109 hand-written words and place names
  with their expected output; 37 are marked for native-speaker review.
- **Browser playground** in `site/` (static, no build step, no framework, no
  external fonts or trackers): Normalise, Numbers, Dates, Tokenise and
  Transliterate tabs, with Preeti shown as coming soon. It runs this package
  in the browser through Pyodide 0.29.5 (Python 3.13.2) from the jsDelivr CDN.
- `scripts/build_site.py`, which assembles the site and packs `src/aksharkit`
  into `pkg/aksharkit.zip` for the page to unpack.
- `.github/workflows/pages.yml`, which builds and deploys the site to GitHub
  Pages on a push to `main`.
- Tests for the playground's Python entry points, the archive, the page's
  HTML/JS/CSS consistency, and `site/app.js` run in Node against a fake DOM.

### Not verified

- The playground has **not been opened in a real browser**, and the Pages
  workflow has not run. See `docs/known-issues.md`.

## 0.2.0 — 23 November 2026

### Added

- **BS ↔ AD dates** (`aksharkit.dates`): `bs_to_ad`, `ad_to_bs`, `BSDate`,
  `parse_bs`, `format_bs` (ISO, long and full styles, optional Devanagari
  digits and names), `fiscal_year` (starts 1 Shrawan), `today_bs`,
  `days_in_month`, `days_in_year`, `is_valid_bs`, `supported_range`,
  `month_name`, `weekday_name`.
- Calendar table for **BS 2000–2083** (14 April 1943 to 13 April 2027), built
  by comparing five published tables. Sources, licences and disagreements are
  in `docs/sources.md`.
- `DateRangeError` for dates outside the table or that do not exist, and
  `DisputedDateError` for 14 May to 14 June 2005 (31 Baishakh to 32 Jestha
  2062), where the published tables differ by one day. `allow_disputed=True`
  uses the majority reading.
- `aksharkit date` command: AD → BS by default, `--to ad`, `--style`,
  `--devanagari`, `--fiscal-year`, `--allow-disputed`.
- `scripts/compare_bs_sources.py`, which repeats the table comparison.
- Preeti source research in `docs/sources.md`. No Preeti table was added.

### Changed

- `aksharkit date` used to exit with code 3 ("not available yet"); it now
  converts dates and exits with code 2 on a bad or out-of-range date.

### Not included

- BS years before 2000 and after 2083: the published tables disagree.
- Preeti conversion: still raises `DataNotVerifiedError`.

## 0.1.0 — 23 November 2026

First public commit (the package version was `0.1.0.dev0`). Unicode
normaliser, digit conversion and number formatting, numbers to words, word
tokeniser and sentence splitter, stopwords, command-line tool. Preeti
conversion and BS dates were stubs.
