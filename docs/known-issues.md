# Known issues and limits

## Not implemented

- **Preeti / legacy fonts** (`aksharkit.legacy`): raises `DataNotVerifiedError`.
  The glyph table is empty; no source with a clearly reusable licence and a
  known origin has been confirmed (see `docs/sources.md`, section 4).

## Browser playground

- **Never run in a real browser.** `site/app.js` has been syntax-checked and
  run in Node against a fake DOM and a fake Pyodide that calls the real
  Python code from the built archive. WebAssembly, the CDN download, the
  real Pyodide API, layout, fonts, touch behaviour and screen readers have
  not been tested.
- **The Pages workflow has never run.** It needs GitHub Pages switched on
  with "GitHub Actions" as the source; until then it fails.
- It needs JavaScript, WebAssembly and a connection to `cdn.jsdelivr.net`.
  The first visit downloads roughly 5 MB (Pyodide 0.29.5); there is no
  offline mode.
- Pyodide 0.29.5 runs Python 3.13.2. The package is tested on CPython
  3.10–3.13, not inside Pyodide.
- `pyodide.js` is loaded with a Subresource Integrity hash; the files it
  then fetches (`pyodide.asm.js`, `pyodide.asm.wasm`, `python_stdlib.zip`)
  are not hash-checked by the page. There is no Content-Security-Policy.
- The "Today" button and `today_bs()` stop working after 13 April 2027,
  when the calendar table ends.
- The Preeti tab is a notice only.

## Transliteration

- **`simple` is approximate in both directions.** Devanagari → `simple`
  merges long and short vowels, dental and retroflex stops, and श/ष. It
  keeps the inherent `a` in the middle of words (सरकार → `sarakar`) and does
  not reproduce customary spellings (काठमाडौँ → `kathamadaun`, विराटनगर →
  `viratnagar`). व is always `v`, or `w` after a consonant.
- **`simple` → Devanagari is a guess.** `a` is always अ, `i`/`u` always
  short, `t`/`d`/`n` always dental, `sh` always श; no halant is added at the
  end of a word; anusvara, candrabindu and visarga are never produced. Only
  32 of the 109 test words survive a `simple` round trip.
- The rules for dropping the final `a` are hand-written and unreviewed; 37
  test spellings are marked for native-speaker review.
- `iast` departs from ISO 15919 for ड़/ढ़ (`ṙ`/`ṙh`) and ख़ (`x`) to stay
  reversible. The round trip needs input without Latin letters, ASCII
  digits (or `digits=False`), `|`, a doubled single danda, or an apostrophe
  directly after a Devanagari letter.
- Devanagari characters outside the table (ऑ, ऍ, ॅ, ॉ, ऌ, ऩ, ऱ, ॰) are passed
  through unchanged in both schemes.
- No other schemes (ITRANS, Harvard-Kyoto) and no dictionary of names.

## Dates (BS ↔ AD)

- **Range:** BS 2000-01-01 to 2083-12-30 only (14 April 1943 to 13 April 2027).
  Anything else raises `DateRangeError`. The range **ends in April 2027**:
  the published tables disagree from BS 2084 onwards, so those years were
  left out. A later release must extend it once the 2084 calendar is settled.
- **Disputed month:** 31 Baishakh to 32 Jestha 2062 (14 May to 14 June 2005)
  raises `DisputedDateError` unless `allow_disputed=True` is passed. Four of
  the five tables say Baishakh 30 / Jestha 32, one says 31 / 31, and outside
  evidence is split. With the flag, the majority reading is used and may be
  one day off.
- **No official source.** The table rests on five open-source projects'
  published tables agreeing, plus eight date pairs from other pages. No
  government or calendar-committee table was checked. Four of the five
  projects are published separately, but they may share a common origin.
- **Month and weekday names** were written from general knowledge and have not
  been reviewed by a native speaker. Only one spelling of each is offered.
- `parse_bs` reads numeric dates only (`2083-08-07`, `२०८३/८/७`), not month names.
- No time-of-day, time-zone or `datetime`-style arithmetic. `today_bs()` uses
  Nepal time (UTC+05:45).
- Dates before BS 2000 and tithi (lunar day) are out of scope for now.

## Verification gaps

- The number-word table was checked against web lists, not an official
  dictionary, and has not yet been reviewed by a native speaker. Several
  spellings are choices between accepted variants (see `docs/sources.md`).
- The stopword list is short, hand-written and unreviewed.
- CI runs the tests on Python 3.10 to 3.13. Python 3.9 was dropped: it is end-of-life and GitHub's current runners no longer provide it.
- No comparison with other Nepali packages has been made.

## Normaliser

- `र्इ` typed for `ई` is not repaired.
- A legacy-style short-i sign typed before its consonant is not reordered.
- NFC decomposes `क़ ख़ ग़ ज़ ड़ ढ़ फ़ य़` (U+0958–095F) into letter + nukta. This is
  correct Unicode behaviour, but string lengths change.
- `|` becomes `।` only directly after Devanagari text (optionally one space)
  and before whitespace or the end. `छ|तर` is left alone.
- With the default `joiners="safe"`, a ZWJ/ZWNJ survives only between a virama
  and a following Devanagari letter. Joiners in other scripts (for example
  emoji sequences or Persian text) are removed; use `joiners="keep"` for
  mixed-script text.

## Numbers

- Words stop at 99,99,99,99,99,999 (10¹³ − 1). नील, पद्म and शंख are not
  implemented; larger values raise `ValueError`.
- Decimals are read digit by digit and trailing zeros are kept as written
  (`"12.50"` → बाह्र दशमलव पाँच शून्य).
- Currency rounds half-up to whole paisa. An amount that rounds to zero is
  शून्य रुपैयाँ with no sign.
- Floats are converted through their shortest `repr`; pass strings or
  `Decimal` for money.
- Non-strict `parse_number` accepts commas anywhere between digits (`1,2,3` → 123).
- Ordinals (पहिलो, दोस्रो) and fractions (आधा, डेढ, साढे) are not supported.

## Tokeniser and sentence splitter

- Tokens break at script boundaries: `Facebookमा` → `Facebook`, `मा`;
  `5G` → `5`, `G`.
- Hyphenated Devanagari splits into three tokens (`आ-आफ्नो`); hyphenated Latin
  words stay whole.
- Dates such as `२०८०-०१-१५` are split at the hyphens.
- No stemming: postpositions stay attached (`नेपालको` is one token).
- A full stop after a listed abbreviation never ends a sentence, so
  `... arrived etc. Then dinner.` stays as one sentence.
- A sentence ending in a dotted abbreviation or a single Latin initial
  (`... in the U.S. Then ...`) is not split there.
- A full stop followed by a lower-case Latin letter does not split.
- `?` and `!` always end a sentence, including inside a URL query string.
- The abbreviation list is short and hand-written.
