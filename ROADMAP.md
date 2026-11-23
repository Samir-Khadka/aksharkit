# Roadmap

Weeks are counted from the start of the project (23 November 2026). They are
targets, not promises.

| Phase | Weeks | Goal | Status |
| --- | --- | --- | --- |
| 0. Setup | 1 | Package skeleton, licence, CI workflow, lint and type checks | Done locally; CI workflow written but never run (no repository yet) |
| 1. Basics | 2–3 | Normaliser, numerals, number to words, tokeniser, sentence splitter, stopwords | Done locally; spellings await native-speaker review |
| 2. Preeti converter + playground | 4–5 | Preeti → Unicode with a verified glyph table and a public test set; browser playground | Not started — API and loader stubbed, table empty |
| 3. Dates | 6–7 | BS ↔ AD conversion from a verified calendar table; formatting | Not started — API and loader stubbed, table empty |
| 4. Release v0.1 | 8 | Documentation pass, first PyPI release | Not started |
| 5. Transliteration + spell check | 9–12 | Romanised ↔ Devanagari; basic spell checking | Not started |
| 6. JavaScript port + more fonts | 13–16 | npm package sharing the same golden tests; Kantipur, Himali, Sagarmatha and others | Not started |
| 7. "Awesome Nepali NLP" list | 8 onwards | A companion list of Nepali language tools and datasets | Not started |

## Before phase 2 can start

1. Choose a source for the Preeti glyph table whose licence allows reuse in an
   MIT package (see `docs/sources.md`). npttf2utf is GPL-3.0, so its mapping
   cannot be copied.
2. Collect real Preeti documents with known-correct Unicode to measure against.

## Before phase 3 can start

1. Choose an authoritative source for BS month lengths and record it.
2. Collect known BS/AD date pairs to cross-check the table.

## Decisions still open

- The project name ("aksharkit" is a working name).
- Creating the repository and the first push.
- Spelling choices listed in `docs/sources.md`.
