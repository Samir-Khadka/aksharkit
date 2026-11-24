# Roadmap

Weeks are counted from the start of the project (23 November 2026). They are
targets, not promises.

| Phase | Weeks | Goal | Status |
| --- | --- | --- | --- |
| 0. Setup | 1 | Package skeleton, licence, CI workflow, lint and type checks | Done; CI runs on Python 3.10 to 3.13 |
| 1. Basics | 2–3 | Normaliser, numerals, number to words, tokeniser, sentence splitter, stopwords | Done (v0.1); words → number and script detection added in v0.4; spellings await native-speaker review |
| 2. Preeti converter + playground | 4–5 | Preeti → Unicode with a verified glyph table and a public test set; browser playground | Playground built (v0.3), live and checked once in a desktop browser (24 Nov 2026); v0.4 adds four tabs, copy buttons, examples and shareable links, not yet deployed. Preeti: sources researched (v0.2), table still empty |
| 3. Dates | 6–7 | BS ↔ AD conversion from a verified calendar table; formatting | Done for BS 2000–2083 (v0.2); date arithmetic, age and month grid added in v0.4; 2084 onwards and one disputed month of 2062 are open |
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
2. Desktop check of v0.3 done 24 Nov 2026 (every tab). Still to do for
   v0.4: open the deployed page on a desktop and on a real phone, try Copy
   and the shared link there, other browsers, the error state, a screen
   reader.
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
3. Ordinals and fractions (पहिलो, आधा, डेढ, साढे) in both directions.

## Still open for dates

1. BS 2084 onwards: the published tables disagree. Add the year once an
   official 2084 calendar can be checked.
2. Baishakh/Jestha 2062: settle it from a printed calendar of that year.
3. Native-speaker review of the month and weekday names, and of the short
   weekday names used in the month grid.

## Decisions still open

- Spelling choices listed in `docs/sources.md`.
- When to make the first PyPI release.
