# Changelog

## 0.5.0 — 24 November 2026

Pushed and deployed to the playground on 24 November 2026. Not released on PyPI.

### Added

- **Aksharas** (`aksharkit.akshara`): `aksharas` splits text into written
  syllables (`नमस्ते` → `न`, `म`, `स्ते`), keeping conjuncts, nukta, vowel signs,
  candrabindu / anusvara / visarga and ZWJ / ZWNJ forms whole.
  `akshara_spans` adds offsets, `akshara_count` counts, and `truncate`
  shortens text without cutting inside one. Text outside Devanagari falls
  back to one code point with its combining marks. Rules and limits:
  `docs/aksharas.md`.
- `aksharkit aksharas TEXT [--count] [--truncate N [--suffix S]] [--sep S] [--json]`.
- **Alphabetical order** (`aksharkit.collate`): `sort_key` and
  `sorted_nepali`. Vowels, consonants क to ह, then क्ष, त्र, ज्ञ (or, with
  `conjunct_letters=False`, those three under क, त, ज). Every choice is
  listed in `docs/sorting.md`. Dictionaries differ; the order is not claimed
  to match any of them.
- `aksharkit sort [--reverse] [--unique] [--conjuncts-under-first]`, lines in,
  lines out.
- **Date patterns**: `format_bs(date, "%-d %B %Y, %A")`. Tokens: `%Y %y %m
  %-m %B %d %-d %A %a %%` (`dates.PATTERN_TOKENS`); an unknown token raises.
  `aksharkit date --pattern`.
- **Month names in `parse_bs`**: `२०८३ मंसिर ८`, `8 Mangsir 2083`, with
  optional साल, गते and a weekday that is checked. Only the package's own
  month spellings; two-digit years, month-first order and unknown names
  raise. Range and disputed-month guards are unchanged.
- **Ordinals 1–100**: `ordinal_to_words` (पहिलो, दोस्रो, तेस्रो, चौथो, पाँचौँ …),
  `aksharkit words --ordinal`. One base form only. All 100 forms are listed
  in `docs/sources.md` for review.
- **Playground**: Aksharas and Sort tabs, an ordinal row under Numbers, a
  pattern row under Dates (which now also takes a BS date with a month
  name), each with examples, copy buttons and a place in the shared link.

### Fixed

- Normaliser: `र्इ` typed for `ई` is repaired (`र्इश्वर` → `ईश्वर`). It is left
  alone when the र ends a conjunct or a joiner follows the virama.
- Playground: after typing in one tab and clicking another, the address
  could go back to the first tab when the pending edit ran. An edit now
  rewrites the address only while its own tab is on screen.
- README, ROADMAP and known issues said the 0.4.0 page had not been checked
  in a real browser. It was, once, on a desktop on 24 November 2026; a
  phone is still untested.

### Not verified

- **The 0.5.0 playground has not been opened in any browser**, on any
  device, and not with real Pyodide. The Node tests drive `app.js` against
  a fake DOM with the Python side run by CPython. The layout of the new
  tabs and rows has not been seen at any width.
- The address fix was reproduced only in those Node tests, not in the
  browser where the problem was reported.
- **No native speaker has reviewed the ordinals or the sort order**, and
  neither was checked against a dictionary or any other source. The 32
  ordinals for 59–70 and 79–98 (साठीऔँ, असीऔँ, नब्बेऔँ …) are the least certain.
- The akshara rules are this project's reading of the Unicode Devanagari
  block. They were not compared with another segmenter or with Unicode's
  grapheme-cluster rules.
- The `र्इ` repair assumes that sequence is never intended in Nepali text;
  no corpus was checked.
- Tests were run locally on Python 3.12 only. GitHub CI has not run on this
  version.

## 0.4.0 — 24 November 2026

Pushed and deployed to the playground on 24 November 2026. Not released on PyPI.

### Fixed

- Playground: the built page now loads `app.js`, `style.css` and the package
  archive under a per-build `?v=` address. Before this, a browser that had
  visited the 0.3.0 page kept the old script and library for up to four hours
  and showed the new tabs with blank results.

### Added

- **Words to number**: `parse_words` reads what `number_to_words` and
  `currency_to_words` write, over the same range (up to 99,99,99,99,99,999):
  ऋण for negatives, दशमलव followed by digits, and रुपैयाँ / पैसा / मात्र. It
  returns an `int`, or a `Decimal` when there is a decimal part or paisa.
  It also accepts the 47 alternative spellings in `ALTERNATIVE_SPELLINGS`
  (the variants listed in `docs/sources.md`), माइनस, दशमलब, रुपियाँ, अरब and
  खरब, and the spoken shortcuts सय, हजार and पन्ध्र सय. Anything else raises
  `ValueError` naming the word.
- `aksharkit number TEXT [--devanagari] [--group]`.
- **Script detection** (`aksharkit.detect`): `char_script`, `script_counts`,
  `script_shares`, `detect_script`, `token_scripts`, by Unicode range. It
  does not identify the language.
- `looks_romanised_nepali` and `romanised_nepali_score`: a heuristic that
  counts matches against a hand-written list of 71 romanised words.
- `aksharkit detect TEXT [--tokens] [--json]`.
- **Date arithmetic** on the existing table: `add_days`, `add_months` (the
  day is clamped to the length of the target month), `days_between`,
  `difference` (`BSDifference` of years, months, days), `age`,
  `month_calendar` and `format_month_calendar`. Range and disputed-month
  guards are the same as for conversion.
- `aksharkit date --calendar YYYY-MM`, `--add-days N`, `--add-months N`,
  `--until BS_DATE`, `--age`.
- **Playground**: Words to number, Calendar, Date maths and Detect tabs; a
  Copy button on every result; examples to tap under every input; "Copy a
  link to this result", which keeps the tab and inputs in the address after
  `#`; a "Preeti: help wanted" link to the issue tracker.

### Changed

- Playground layout for phones: the tab strip scrolls sideways, buttons and
  inputs are at least 2.75rem (44px) tall, and the focus outline is more
  visible. Devanagari output is marked `lang="ne"`; Roman transliteration
  output is marked `ne-Latn`.
- README: CI badge, "Why aksharkit", new quick-start and command examples.

### Not verified

- The new playground has **not been opened with real Pyodide or on a real
  phone**. It was loaded in headless Chromium at 360px and 1280px with the
  Python side answered by local CPython: no sideways page scroll, no control
  under 44px, copy and link sharing worked, no console errors.
- No native speaker has reviewed the romanised word list, the rule-generated
  alternative spellings, or the calendar's weekday abbreviations.
- The accuracy of `looks_romanised_nepali` has not been measured.
- Tests were run on Python 3.12 only; GitHub CI has not run on this version.

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
