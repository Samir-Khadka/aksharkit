# Sources and decisions

## 1. Number words (0–100)

The table in `src/aksharkit/words.py` was typed by hand and compared, entry by
entry, with two full published lists read on 23 November 2026:

1. Omniglot, "Numbers in Nepali" — <https://www.omniglot.com/language/numbers/nepali.htm>
2. Lingocard, "Nepali numbers" — <https://lingocard.com/nepali-numbers> (also lists "also written" variants)

Partial corroboration (individual words seen, not full lists):

- Wikipedia, "Numbers in Nepali language" — <https://en.wikipedia.org/wiki/Numbers_in_Nepali_language>
- <https://www.imnepal.com/nepali-numbers/>
- <https://ling-app.com/blog/nepali-numbers-and-counting/>
- <https://barala.com.np/calculators/nepali-numbers-and-words/>

These are web references, **not** an official dictionary or the Nepal
Academy's spelling rules. No such authority was consulted. A native speaker
should review the table.

`tests/golden/number_words_0_100.tsv` was generated from the reviewed table.
It guards against accidental changes; it is not independent proof.

### Where the sources disagree, and what was chosen

| Number | Chosen | Alternative(s) | Notes |
| --- | --- | --- | --- |
| 0 | शून्य | सुन्ना, शुन्य | Omniglot gives सुन्ना; Lingocard शून्य |
| 10 | दस | दश | Omniglot, Wikipedia: दस. Lingocard, imnepal, ling-app: दश |
| 20, 30, 40 and the 21–48 forms | short i: बिस, तिस, चालिस, पच्चिस | long i: बीस, तीस, चालीस, पच्चीस | Both full lists give short i first; long i is "also written" |
| 31 | एकतिस | एकत्तिस | Both full lists: एकतिस |
| 34 | चौँतिस | चौतिस | Omniglot omits the chandrabindu |
| 59 | उनन्साठी | उनसट्ठी | Omniglot's cardinal is उनसट्ठी |
| 64 | चौसट्ठी | चौँसट्ठी | Both full lists: चौसट्ठी |
| 89, 92–98 | -ान्नब्बे (उनान्नब्बे, बयान्नब्बे …) | -ानब्बे | Omniglot: double न. Lingocard: single न first |
| 99 | उनान्सय | उनन्सय | Omniglot, imnepal: उनान्सय |

75 (पचहत्तर): Omniglot's Devanagari did not come through cleanly in the fetched
page; its romanisation matches Lingocard's पचहत्तर.

### Other wording choices

| Item | Chosen | Alternative(s) |
| --- | --- | --- |
| 10⁹, 10¹¹ | अर्ब, खर्ब | अरब, खरब |
| Decimal point | दशमलव | दशमलब |
| Negative | ऋण | माइनस |
| 100 | एक सय | सय |
| Cheque suffix (`only=True`) | मात्र | — |
| Currency | रुपैयाँ, पैसा | रुपियाँ |
| Fractions | read digit by digit: 12.50 → बाह्र दशमलव पाँच शून्य | — |

## 2. Stopwords

`src/aksharkit/stopwords.py` is a short list of closed-class words
(postpositions, pronouns, conjunctions, common auxiliary forms) written by
hand for this project. It was **not** copied from another package or corpus
and has not been reviewed by a native speaker or measured against a corpus.

## 3. Normaliser

Behaviour follows the Unicode Standard: NFC as defined in UAX #15, and the
Devanagari block's guidance that ZWJ/ZWNJ affect conjunct shaping after a
virama. The list of split-vowel repairs was written from the Devanagari code
chart's "do not use" sequences as recalled; it was not re-checked against the
chart text during this build.

## 4. Preeti glyph table — NOT CHOSEN, table is empty

`src/aksharkit/data/font_preeti.json` is empty on purpose. Candidate sources,
for approval:

| Candidate | Licence (as listed on PyPI/npm, 23 Nov 2026) | Usable in an MIT package? |
| --- | --- | --- |
| [npttf2utf](https://github.com/trippygeese/npttf2utf) 0.3.7 (last release May 2021) | GPL-3.0 | **No** — mapping must not be copied |
| [nepalikit](https://github.com/prabhashj07/nepalikit) 1.0.7 | MIT | Possibly, with attribution; origin of its table not checked |
| [nepali-unicoder](https://github.com/realsanjeev/nepali_unicoder) 0.3.0 | MIT | Possibly, with attribution; not inspected |
| npm `preeti` 1.0.3, npm `unicode-to-preeti` 1.0.0 | Not checked | Unknown |
| Build the table independently from the Preeti font's own glyphs, checked against real documents | — | Yes, but the font file's own licence is unknown and must be checked first |

None of these repositories' files were opened or copied during this build.

## 5. Bikram Sambat calendar table — NOT CHOSEN, table is empty

`src/aksharkit/data/bs_calendar.json` is empty on purpose. BS month lengths
are published year by year and cannot be computed.

| Candidate | Licence (PyPI, 23 Nov 2026) | Notes |
| --- | --- | --- |
| [nepali-datetime](https://github.com/amitgaru/nepali-datetime) 1.0.8.5 | MIT | Data origin not checked |
| [nepali](https://github.com/opensource-nepal/py-nepali) 1.2.0 | MIT | Data origin not checked |
| [nepkit](https://github.com/akakritagya/nepkit) 0.4.1 | MIT | Data origin not checked |
| Official published calendars (patro) | — | The authoritative origin; no specific official source or URL was verified during this build |

Whichever is used, the table should be cross-checked against at least one
other source and a set of known BS/AD date pairs before it is marked verified.

## 6. Related packages (licences as listed on PyPI, 23 Nov 2026)

nepalikit 1.0.7 — MIT · nepali-datetime 1.0.8.5 — MIT · nepali 1.2.0 — MIT ·
nepalify 1.0.1.1 — MIT · nepali-date-numword 0.1.2 — MIT · nepkit 0.4.1 — MIT ·
npttf2utf 0.3.7 — GPL-3.0 · npltk 0.3.2 — no licence field on PyPI.
