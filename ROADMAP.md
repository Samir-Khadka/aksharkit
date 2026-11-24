# Roadmap

Weeks are counted from the start of the project (23 November 2026). They are
targets, not promises.

| Phase | Weeks | Goal | Status |
| --- | --- | --- | --- |
| 0. Setup | 1 | Package skeleton, licence, CI workflow, lint and type checks | Done; CI runs on Python 3.10 to 3.13 |
| 1. Basics | 2–3 | Normaliser, numerals, number to words, tokeniser, sentence splitter, stopwords | Done (v0.1); words → number and script detection added in v0.4; akshara segmentation, alphabetical order and ordinals 1–100 added in v0.5; spellings and sort order await native-speaker review |
| 2. Preeti converter + playground | 4–5 | Preeti → Unicode with a verified glyph table and a public test set; browser playground | Playground built (v0.3), live and checked once in a desktop browser (24 Nov 2026); v0.4 adds four tabs, copy buttons, examples and shareable links, deployed 24 Nov 2026 and checked once in a desktop browser the same day, phone untested; v0.5 adds Aksharas and Sort tabs, checked once in a desktop browser on 24 Nov 2026. Preeti: **experimental converter in v0.6** — key table from what three families of MIT-licensed tables agree on, own reordering code, playground tab on; not checked against real Preeti documents or by a native reader at that point. v0.6 tab checked once in a desktop browser on 24 Nov 2026. **v0.7 (built locally)** adds Word (.docx) and text files, protected stretches, Unicode → Preeti that only writes what converts back exactly, line and column reports, JSON, and file open and download in the playground tab; none of it tried on a real Preeti document or a Word-made file at that point. v0.8 measured Unicode → Preeti and added files in that direction; deployed 24 Nov 2026 and that direction checked once in a desktop browser the same day (not a .docx, not a phone). **v0.9 (deployed 24 Nov 2026)**: tested on nine real Preeti PDFs from seven publishers — 2 of 409,081 key characters with no entry, 166 lines read by eye by the build assistant, 108 keys confirmed, 21 never seen, 26 real excerpts as tests; status changed from "experimental" to "tested on real documents"; still not reviewed by a native reader |
| 3. Dates | 6–7 | BS ↔ AD conversion from a verified calendar table; formatting | Done for BS 2000–2083 (v0.2); date arithmetic, age and month grid added in v0.4; format patterns and month-name parsing added in v0.5; 2084 onwards and one disputed month of 2062 are open |
| 4. First PyPI release | 8 | Documentation pass, first PyPI release | Not started |
| 5. Transliteration + spell check | 9–12 | Romanised ↔ Devanagari; basic spell checking | Transliteration done (v0.3): `iast` exact, `simple` approximate, spellings await review. Spell check not started |
| 6. JavaScript port + more fonts | 13–16 | npm package sharing the same golden tests; Kantipur, Himali, Sagarmatha and others | Not started |
| 7. "Awesome Nepali NLP" list | 8 onwards | A companion list of Nepali language tools and datasets | Not started |

## Still open for Preeti (before it can be called reviewed)

1. Real Preeti text with the correct Unicode beside it. **Started in 0.9**:
   26 excerpts from public PDFs are in `tests/golden/preeti_samples.tsv`,
   with the Unicode written down by the build assistant from the page
   images. Still wanted: text from a typist's own file (a `.docx` or `.txt`,
   not a PDF), and other kinds of document (a newspaper, a book, a letter).
2. A native reader going through the keys in `docs/preeti.md`, the 26
   excerpts and the output of a few real pages. **Not done**; this is the
   largest gap left.
3. Asking the four table authors where their tables came from (an issue
   each). Not done; nothing has been sent to anyone.
4. Settling the 3 keys still disputed (`° Ì Ý`), the 5 one-family keys and
   the dot key for ड़ ढ़. 0.9 settled `¥` and `Ú` from what the font draws
   in real documents; these others occur in none of the nine, so a document
   that uses them is needed. 21 keys in all were never seen.
5. The 0.6 and 0.7 Preeti tabs were each checked once in a desktop browser
   on 24 Nov 2026 (0.7 including a .docx open and download), and the 0.8
   Unicode → Preeti direction once that day (typed text, examples, copy,
   text download, deep link). Still to do: a phone, a `.docx` in that
   direction, and the 0.9 wording, which has not been opened in a browser.
6. A .docx written by Microsoft Word, with Preeti text in it, put through
   `convert_docx` and the result opened in Word. v0.7 has only seen files
   built by its own tests.
7. Someone looking at Unicode → Preeti output in the Preeti font, in Word.
   v0.9 drew the keys for 17 lines in the outlines found in real documents;
   the rest (5,246 of 5,300 audited forms, 2,639 of 2,639 hand-written
   words) is still only converted back with the same table. `..` for ॥ has
   not been seen in a document.
8. Keys for what cannot be written yet: the hyphen, straight quotes, square
   brackets, `…`, nukta letters, ॉ ऍ ऑ, forms with a zero-width non-joiner.
   (0.9 added the eyelash ra, both dashes and ‘ ’.) Each needs a document
   that shows it, or a source this project may use.
9. A Unicode .docx written by Microsoft Word put through `encode_docx`, and
   the result opened in Word with Preeti installed.
10. Table styles and DrawingML text in .docx files; other legacy fonts.

npttf2utf (GPL-3.0), 2utf8 and npm `preeti` (both non-commercial) cannot be
copied and were not opened.

## Still open for the playground

1. Done 24 Nov 2026: GitHub Pages is on and the page is deployed.
2. Desktop checks of v0.3 and v0.4 done 24 Nov 2026 (every tab; for v0.4
   also copy, examples and a shared link after a reload). Still to do: a
   real phone, other browsers, the error state, a screen reader; and for
   v0.5, v0.6 and v0.7 were each checked once on a desktop on 24 Nov 2026;
   the v0.8 Preeti tab additions have not been opened in a browser.
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
