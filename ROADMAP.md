# Roadmap

Weeks are counted from the start of the project (23 November 2026). They are
targets, not promises.

| Phase | Weeks | Goal | Status |
| --- | --- | --- | --- |
| 0. Setup | 1 | Package skeleton, licence, CI workflow, lint and type checks | Done; CI runs on Python 3.10 to 3.13 |
| 1. Basics | 2–3 | Normaliser, numerals, number to words, tokeniser, sentence splitter, stopwords | Done (v0.1); words → number and script detection added in v0.4; akshara segmentation, alphabetical order and ordinals 1–100 added in v0.5; spellings and sort order await native-speaker review |
| 2. Preeti converter + playground | 4–5 | Preeti → Unicode with a verified glyph table and a public test set; browser playground | Playground built (v0.3), live and checked once in a desktop browser (24 Nov 2026); v0.4 adds four tabs, copy buttons, examples and shareable links, deployed 24 Nov 2026 and checked once in a desktop browser the same day, phone untested; v0.5 adds Aksharas and Sort tabs, not yet opened in any browser. Preeti: sources researched (v0.2), table still empty |
| 3. Dates | 6–7 | BS ↔ AD conversion from a verified calendar table; formatting | Done for BS 2000–2083 (v0.2); date arithmetic, age and month grid added in v0.4; format patterns and month-name parsing added in v0.5; 2084 onwards and one disputed month of 2062 are open |
| 4. First PyPI release | 8 | Documentation pass, first PyPI release | Not started |
| 5. Transliteration + spell check | 9–12 | Romanised ↔ Devanagari; basic spell checking | Transliteration done (v0.3): `iast` exact, `simple` approximate, spellings await review. Spell check not started |
| 6. JavaScript port + more fonts | 13–16 | npm package sharing the same golden tests; Kantipur, Himali, Sagarmatha and others | Not started |
| 7. "Awesome Nepali NLP" list | 8 onwards | A companion list of Nepali language tools and datasets | Not started |

## Before phase 2 can start

1. Real Preeti text with the correct Unicode beside it, to test against.
2. A glyph table whose origin is known. The plan in `docs/sources.md`
   (section 4) is to compare two MIT-licensed tables and keep what agrees,
   after asking their authors where the tables came from. npttf2utf (GPL-3.0),
   2utf8 and npm `preeti` (both non-commercial) cannot be copied.

## Still open for the playground

1. Done 24 Nov 2026: GitHub Pages is on and the page is deployed.
2. Desktop checks of v0.3 and v0.4 done 24 Nov 2026 (every tab; for v0.4
   also copy, examples and a shared link after a reload). Still to do: a
   real phone, other browsers, the error state, a screen reader; and for
   v0.5 everything, since its new tabs have not been opened in a browser.
3. Decide whether to add a Content-Security-Policy once it has been seen
   working.

## Still open for transliteration

1. Native-speaker review of the 37 `simple` spellings marked in
   `tests/golden/translit_words.tsv`.
2. A list of customary spellings for place names (Kathmandu, Biratnagar).
3. Whether `simple` should drop the inherent `a` in the middle of words.

## Still open for numbers and detection

1. Native-speaker review of the alternative spellings `parse_words` accepts
   and of the spoken shortcuts (`docs/sources.md`, section 1).
2. Native-speaker review of the romanised word list, then a measured test of
   `looks_romanised_nepali` on real chat text before anyone relies on it.
3. Native-speaker review of the 100 ordinal forms added in v0.5
   (`docs/sources.md`), above all the 32 written with `औँ` after a vowel.
4. Ordinals above 100, reading ordinals back, and fractions (आधा, डेढ, साढे).

## Still open for aksharas and sorting

1. Native-speaker review of the sort order in `docs/sorting.md`, and a check
   against at least one printed dictionary.
2. Whether a final halant consonant should join the syllable before it.
3. Numeric-aware sorting; grapheme-aware fallback outside Devanagari.

## Still open for dates

1. BS 2084 onwards: the published tables disagree. Add the year once an
   official 2084 calendar can be checked.
2. Baishakh/Jestha 2062: settle it from a printed calendar of that year.
3. Native-speaker review of the month and weekday names, and of the short
   weekday names used in the month grid and by the `%a` token.
4. Whether `parse_bs` should accept other month spellings (जेष्ठ, मङ्सिर, पौष).

## Decisions still open

- Spelling choices listed in `docs/sources.md`.
- When to make the first PyPI release.
