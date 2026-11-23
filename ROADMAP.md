# Roadmap

Weeks are counted from the start of the project (23 November 2026). They are
targets, not promises.

| Phase | Weeks | Goal | Status |
| --- | --- | --- | --- |
| 0. Setup | 1 | Package skeleton, licence, CI workflow, lint and type checks | Done; CI runs on Python 3.10 to 3.13 |
| 1. Basics | 2–3 | Normaliser, numerals, number to words, tokeniser, sentence splitter, stopwords | Done (v0.1); spellings await native-speaker review |
| 2. Preeti converter + playground | 4–5 | Preeti → Unicode with a verified glyph table and a public test set; browser playground | Not started — sources researched (v0.2), table still empty |
| 3. Dates | 6–7 | BS ↔ AD conversion from a verified calendar table; formatting | Done for BS 2000–2083 (v0.2); 2084 onwards and one disputed month of 2062 are open |
| 4. First PyPI release | 8 | Documentation pass, first PyPI release | Not started |
| 5. Transliteration + spell check | 9–12 | Romanised ↔ Devanagari; basic spell checking | Not started |
| 6. JavaScript port + more fonts | 13–16 | npm package sharing the same golden tests; Kantipur, Himali, Sagarmatha and others | Not started |
| 7. "Awesome Nepali NLP" list | 8 onwards | A companion list of Nepali language tools and datasets | Not started |

## Before phase 2 can start

1. Real Preeti text with the correct Unicode beside it, to test against.
2. A glyph table whose origin is known. The plan in `docs/sources.md`
   (section 4) is to compare two MIT-licensed tables and keep what agrees,
   after asking their authors where the tables came from. npttf2utf (GPL-3.0),
   2utf8 and npm `preeti` (both non-commercial) cannot be copied.

## Still open for dates

1. BS 2084 onwards: the published tables disagree. Add the year once an
   official 2084 calendar can be checked.
2. Baishakh/Jestha 2062: settle it from a printed calendar of that year.
3. Native-speaker review of the month and weekday names.

## Decisions still open

- Spelling choices listed in `docs/sources.md`.
- When to make the first PyPI release.
