# Changelog

## 0.8.0 — 24 November 2026

Pushed and deployed to the playground on 24 November 2026. Not released on PyPI.

This release works on Unicode → Preeti: what it can write is now measured,
more of it can be written, and it works on files. **The key table is still
the 0.6 table and still experimental**: unchecked against real Preeti
documents, by a native reader, or by anyone looking at the Preeti font.
Every number below is this package reading its own output back.

### Added

- **Coverage audit**: `scripts/preeti_coverage.py` writes 5,300 forms
  (consonants, vowel signs, nasal signs, every two-consonant conjunct, longer
  conjuncts, reph and ra forms, vowels, digits, punctuation, joiner forms,
  nukta letters, ॐ ऽ) and reads each back. **5,236 are written as keys and
  read back exactly** (5,241 with single-table keys, 5,235 in strict mode).
  It lists every form it cannot write and why; `--json`, `--markdown`,
  `--check`. The table and the list are in `docs/preeti.md`.
- **A hand-written word list and sentences**:
  `tests/golden/preeti_wordlist.txt` (2,639 different words) and
  `tests/golden/preeti_sentences.txt` (62 sentences). **2,638 words (99.96%)
  and 61 sentences are written wholly as keys and read back exactly**; the
  two exceptions hold the zero-width-joiner ra (भर्‍याङ, गर्‍यो). The files
  hold no Preeti keys: only the round trip is tested, not made-up outputs.
- **Cross-check**: `tests/golden/preeti_crosscheck.tsv`, 14 example pairs
  shown on two other converters' pages, labelled by page. All 14 agree in
  both directions, with identical key strings. They are worked examples,
  not ground truth; `preeti_samples.tsv` stays reserved for real samples.
- **Word files, Unicode → Preeti**: `encode_docx(src, dst, *, font="Preeti",
  overwrite=False, strict=False, include_unconfirmed=False, digits="keep",
  ...)` and `encode_docx_bytes(data, ...)` return a `DocxEncodeReport`.
  Devanagari becomes keys in runs whose font is set to the name Preeti (no
  font is supplied); runs without Devanagari are untouched; mixed runs are
  cut; a Nepali word that cannot be written stays whole in Unicode in its
  own font and is listed in `report.left` (`DocxLeft`). Converting the
  result back with `convert_docx` gives the same text.
- `aksharkit convert preeti --to preeti --docx in.docx -o out.docx`, and
  `--to preeti` with `-i`, `-o`, `--out-dir` as before.
- `encode_preeti` options: `include_unconfirmed` (single-table keys for ड़
  ढ़ ॅ ×, off by default; `--include-unconfirmed`), `digits="devanagari"`
  (`--digits devanagari`), `mark_kept=(open, close)` (`--mark-kept OPEN
  CLOSE`: mark what was left alone so that plain text converts back
  exactly), `whole_words`.
- `PreetiEncodeResult.foreign` (`ForeignSpan`), `.segments`
  (`PreetiSegment`: every stretch in order with its kind) and `.stats`
  (`PreetiEncodeStats`: words, words written, characters, shares).
- **Playground** (local only): Unicode → Preeti opens `.txt` and `.docx`
  files and downloads the result, has five examples of its own, the
  single-table option, whole words that could not be written highlighted, a
  coverage line, and a notice that the result is key codes that read as
  Nepali only in the Preeti font. No new CDN resource; asset stamping
  unchanged; a file's text still never goes into the address.

### Changed

- **Unicode → Preeti leaves text with no Devanagari alone** and lists it in
  `result.foreign`. 0.7 reported every Latin letter and ASCII digit as
  unmapped, and `complete` was false for any text with English in it.
- ्र after ङ छ ट ठ ड ढ is written with `«` (ट्रक `6«s`); 0.7 wrote `|`.
- ॥ is written as `..`, and a colon that does not follow a letter as `M`;
  0.7 reported both as having no key.
- **Preeti → Unicode**: `..` reads as ॥ (0.7: ।।); `M` with no letter
  before it reads as a colon (0.7: ः); a reph key after a half letter is
  placed (0.7: reported as unmapped).
- `--report` for `--to preeti` prints words written and left, and the
  stretches left alone. `--include-unconfirmed` with `--to preeti` is no
  longer an error. `--font` defaults to Preeti with `--to preeti`.
- `encode_preeti(...).as_dict()` has four more keys: `stats`, `foreign`,
  `segments`, `mark_kept`.

### Cannot be written (reported, never guessed)

The hyphen, en and em dash, `…`, straight quotes, `[ ] { }`, `*`, `&`,
`#`, `@`, `÷`, `॰`, `’` (disputed key); a colon straight after a letter;
forms with a zero-width joiner or non-joiner; nukta letters (ड़ ढ़ with the
single-table option only); ॉ ऍ ऑ ॠ ॄ ऌ ॢ; ॅ and `×` with the single-table
option only.

### Not verified

- **No real Preeti document** has been converted in either direction.
- **Nobody has looked at any key in the Preeti font.** The audit, the word
  list and the sentences prove only that the two directions agree with each
  other. `«` for ्र, `..` for ॥ and `M` for a colon are rule choices.
- **No native reader** has reviewed the table, the word list, the sentences
  or any output.
- The 14 cross-check pairs come from other converters, which may share
  table lineage with the sources already compared.
- **Microsoft Word**: no output was opened in it, and no input came from
  it. One output was read with python-docx and by LibreOffice only.
- Whether Preeti or Kalimati is installed anywhere is not checked.
- **The 0.8 playground has not been opened in any browser.** The 0.7.0
  Preeti tab was checked once in a desktop browser on 24 November 2026,
  including a .docx open and download; a phone is untested for every
  version.
- Plain text Preeti → Unicode still cannot tell English from Preeti.
- Where the four tables came from is still unknown.

## 0.7.0 — 24 November 2026

Pushed and deployed to the playground on 24 November 2026. Not released on PyPI.

Everything below makes the Preeti converter more usable. **None of it makes
it more verified**: the key table is the 0.6 table, still experimental and
still unchecked against real Preeti documents or by a native reader.

### Added

- **Word files** (`aksharkit.legacy_docx`, standard library only):
  `convert_docx(src, dst, *, font="Kalimati", source_fonts=("Preeti",),
  overwrite=False, ...)` and `convert_docx_bytes(data, ...)` convert only the
  runs set in the Preeti font and return a `DocxReport` (runs converted and
  left alone, paragraphs changed, fonts found, unmapped characters with their
  part and paragraph, key statistics). The font is taken from the run, its
  character style, the paragraph style, the styles they are based on, the
  document defaults and the theme. Body, tables, headers, footers, footnotes,
  endnotes and comments are read. Converted runs get the Unicode font name
  on `w:ascii`, `w:hAnsi` and `w:cs`, and their complex-script bold, italic
  and size are made to match the ordinary ones. Everything else in the file
  is copied byte for byte. Words cut across several runs are converted as
  one stretch and shared back out. The input is never written to.
- `aksharkit convert preeti --docx in.docx -o out.docx [--font NAME]
  [--source-font NAME] [--report]`.
- **Text files and batches**: `-i/--input FILE` (repeatable, `-` for standard
  input), `-o/--output FILE`, `--out-dir DIR`, `--force`, `--encoding`.
  Line endings, tabs and blank lines are kept exactly; a UTF-8 byte-order
  mark is accepted; an existing output is refused without `--force`, and the
  output may never be the input.
- **Leaving parts alone**: web and e-mail addresses in plain text are kept
  automatically (`keep_links`, `--no-keep-links`); `keep=` / `--keep REGEX`,
  `keep_words=` / `--keep-word WORD` and `markers=` / `--markers OPEN CLOSE`
  protect whatever you name. Protected stretches are listed in
  `PreetiResult.protected`.
- **Unicode → Preeti**: `encode_preeti(text)` returns a `PreetiEncodeResult`
  (`.text`, `.unmapped`, `.skipped`, `.complete`); `unicode_to_preeti(text)`
  returns the text; `--to preeti` on the command line. A word is written as
  keys only if converting it back gives the normalised input; otherwise it
  is left in Unicode and reported. Characters with no key are reported, never
  guessed.
- **Fuller reports**: every `UnmappedChar` has `.line`, `.column` and
  `.output_offset`; `PreetiResult.stats` (`PreetiStats`) counts characters
  converted by agreed, majority and one-family keys and gives their shares;
  `.as_dict()` on every result; `--json`; `--fail-on-unmapped`.
- **Playground, Preeti tab**: open a `.txt` or `.docx` file and download the
  result, all inside the browser; direction switch; characters left alone
  are highlighted; a line saying how well-attested the keys used were; input
  and output side by side on wide screens and stacked on narrow ones; text
  over 20,000 characters waits for a Convert button. A file's text is never
  put in the address.
- The playground archive now carries `LICENSE` and `NOTICE`.
- TEXT may come before or after the options of `aksharkit convert`.

### Changed

- `legacy.unicode_to_preeti` converts instead of raising
  `NotImplementedError`.
- A character with no agreed letter is copied through exactly. In 0.6 it
  went through Unicode normalisation with the rest of the text.
- `--report` prints `line L, column C` for each unmapped character instead of
  `position N`, and adds a summary line.
- Old shared links to the Preeti tab still open; new ones also carry the
  direction (`to=unicode`).
- Docs: the 0.6 Preeti tab was checked once in a desktop browser on
  24 November 2026 (after 0.6.0 was written up); README, ROADMAP and known
  issues now say so.

### Left out on purpose

- **An automatic "skip English words" option.** Preeti words are plain ASCII
  letters (`dfof`, `sdn`, `gfd`) and English words convert to
  plausible-looking Devanagari, so no rule without a dictionary can tell
  them apart, and its mistakes would be silent.
- No Preeti font is bundled, loaded or linked, and no Unicode font either.
- No new dependency. Nothing was taken from GPL or non-commercial sources.

### Not verified

- **No real Preeti document has been converted**, as in 0.6: no real Preeti
  text file, and **no Word file written by Microsoft Word**. Every .docx in
  the tests is built by the tests. No output has been opened in Microsoft
  Word. On the build machine python-docx 1.1.0 and LibreOffice opened the
  output of one mixed test document; that shows the file is well formed,
  not that Word shows it as intended.
- **Whether the default font name (Kalimati) is present on readers'
  computers** was not checked, nor how Word substitutes when it is not.
- **Unicode → Preeti output has never been seen in the Preeti font.** It is
  checked only by converting back with the same table, so a mistake shared by
  both directions would not show. Which of several equivalent keys a typist
  would use is not known; the choice is by rule.
- **Nothing new in the playground has been opened in a browser**, on any
  device, or run in real Pyodide. The Node tests fake the page and run the
  archive with ordinary Python. That `zipfile` and `xml.parsers.expat` work
  inside Pyodide 0.29.5 is expected, not checked. How long a large
  conversion blocks the page was not measured.
- No native reader has reviewed the table or any output; where the four
  source tables came from is still unknown.
- .docx cases not handled: fonts from table styles, DrawingML text, list
  numbers; see `docs/preeti.md`.
- Not pushed, not deployed, not released.

## 0.6.0 — 24 November 2026

Pushed and deployed to the playground on 24 November 2026. Not released on PyPI.

### Added

- **Preeti to Unicode, experimental** (`aksharkit.legacy`):
  `convert_preeti(text)` returns a `PreetiResult` with `.text`, `.unmapped`
  (each an `UnmappedChar` with the character and its offset in the input),
  `.complete` and `.unmapped_chars`; `preeti_to_unicode(text)` returns just
  the text. Both are exported from `aksharkit`. A character with no agreed
  letter is left unchanged and reported, never guessed.
- **A key table** in `data/font_preeti.json`, labelled *experimental —
  mapping agreed by at least 2 of 3 permissively-licensed table families
  (4 projects), not yet checked against real Preeti documents or by a native
  reader*. It was written by comparing the Preeti tables of four MIT-licensed
  projects (nepali-unicoder and nepalikit, counted as one family because they
  share a rule list; preeti-unicode-converter; nepali-keyboard). Of 136 keys
  compared: 122 agreed by two or more families; 4 agreed by two or more
  families with one table differing (`B`, `^`, `¡`, `¿` — used by default,
  off with `strict=True`); 5 in one family only (off unless
  `include_unconfirmed=True`); 5 with no agreement (never used). Plus 5
  two-key sequences with two or more families behind them.
- **Reordering in aksharkit's own code**: short i moved after its consonant
  cluster, reph moved before its cluster, the `m` stroke (फ, झ, ऊ, क्र, क्त),
  half form + bar = full letter, sign order, then `normalize`.
- `aksharkit convert preeti [TEXT] [--report] [--include-unconfirmed]
  [--strict] [--quiet]`. Unmapped characters are named on standard error and
  the exit code stays 0.
- Playground: the Preeti tab is on, with the experimental notice, a list of
  characters left unchanged, the two tier switches, examples, a copy button
  and a shareable address. The input box uses the system's monospace font;
  the page does not load the Preeti font.
- `scripts/compare_preeti_sources.py` (report, `--check`, `--write`) and
  `scripts/preeti_sources.json` (what each project states for each key, with
  attribution). `NOTICE` with the four MIT copyright notices, shipped with
  the package.
- `docs/preeti.md`; `tests/golden/preeti_samples.tsv`, empty, with
  instructions for real samples.

### Changed

- `legacy.preeti_to_unicode`, `legacy.to_unicode` and `legacy.load_font_map`
  no longer raise `DataNotVerifiedError`. `aksharkit convert preeti` no
  longer exits with code 3.
- `legacy.unicode_to_preeti` now raises `NotImplementedError` ("not
  implemented") rather than `DataNotVerifiedError`.
- `docs/sources.md` section 4, known issues, ROADMAP and README updated.

### Not verified

- **No real Preeti document has been converted.** Every Preeti sample in the
  tests was typed by the builder from the table itself: those tests show
  self-consistency only.
- **No native reader has reviewed the key table or any output.** Nobody
  opened the Preeti font to see what each key draws.
- **Where the four source tables came from is unknown.** None of the
  projects says, and their authors have not been asked. Whether any descends
  from the GPL or non-commercial tables (which were not opened) is an open
  question. For 16 keys the only two tables with the key are nepalikit and
  nepali-keyboard, whose keys overlap almost entirely.
- The four `majority` keys rest on the judgement that the one differing
  table has a slip.
- The reordering rules have not been tried on real typing.
- **The Preeti tab has not been opened in any browser**, on any device, and
  not with real Pyodide; it is covered by the Node tests only.
- Unicode → Preeti is not implemented.

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
