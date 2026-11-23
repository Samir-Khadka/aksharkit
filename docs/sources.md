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

## 4. Preeti glyph table — research only, table still empty

`src/aksharkit/data/font_preeti.json` is still empty on purpose. On
23 November 2026 the candidates below were looked at: licence files and
READMEs were read as text; **no mapping table was opened, copied or compared**.

| Candidate | Licence (read 23 Nov 2026) | States where its table came from? | Usable in an MIT package? |
| --- | --- | --- | --- |
| [npttf2utf](https://github.com/trippygeese/npttf2utf) 0.3.7 | GPL-3.0 (PyPI) | — | **No** |
| [foss-np/2utf8](https://github.com/foss-np/2utf8) | CC BY-NC-SA 3.0 (LICENSE file) | Original FOSS Nepal rules | **No** (non-commercial, share-alike) |
| npm `preeti` 1.0.3 ([mapmeld/preeti](https://github.com/mapmeld/preeti)) | CC BY-NC-SA 4.0 (npm) | Yes: README says it is based on FOSS Nepal's 2utf8 and on nep-ttf2utf | **No** |
| [sapradhan/nep-ttf2utf](https://github.com/sapradhan/nep-ttf2utf) | Apache-2.0 (LICENSE file) | Described by mapmeld as a port of 2utf8, which is CC BY-NC-SA | Unclear: the licence label and the upstream's licence do not match |
| [nepali-unicoder](https://github.com/realsanjeev/nepali_unicoder) 0.3.0 | MIT (LICENSE: Copyright (c) 2025 RealSanjeev) | No statement found in README | Licence allows it; origin unverified |
| [preeti-unicode-converter](https://github.com/diwaskunwar/preeti-unicode-converter) 0.1.1 | MIT (LICENSE: Copyright (c) 2024 Diwas Kunwar) | Only "Thanks to the Nepali computing community for font specifications" | Licence allows it; origin unverified |
| [nepalikit](https://github.com/prabhashj07/nepalikit) 1.0.7 | MIT (LICENSE: Copyright (c) 2024 Prabhash Kumar Jha) | No statement found in README | Licence allows it; origin unverified |
| [nepali-converter](https://github.com/nepalibhasha/nepali-fonts) 0.1.1 | MIT for code (repository LICENSE is dual: MIT code, OFL-1.1 fonts) | Not checked beyond the README | Licence allows it; origin unverified |
| [prabin194/nepali-keyboard](https://github.com/prabin194/nepali-keyboard) | MIT (LICENSE: Copyright (c) 2026 Prabin Paudel) | Not checked | Licence allows it; origin unverified |
| npm `preeti-to-unicode` 1.0.12 | MIT (npm) | Not checked (repository files not reachable at the usual paths) | Unverified |
| npm `unicode-to-preeti` 1.0.0, npm `preeti-unicode` 0.0.1 | ISC (npm), no repository listed | Not checked | Unverified |

Other findings:

- **The Preeti font itself.** Web pages commonly attribute it to Ajay Mishra,
  1993, and call it freeware
  ([nepaltype.com](https://www.nepaltype.com/blogs/what-is-preeti-font),
  [topnepali.com](https://topnepali.com/top-nepali-fonts)); one of the same
  sites names a different designer on another page. No licence text for the
  font was found. aksharkit does not need to ship the font, only a table of
  which key shows which letter.
- **No standards document** for the Preeti layout was found. Pages describe it
  as following the Remington typewriter layout and as the model for the Nepali
  Unicode "Traditional" keyboard layout; neither claim was checked against a
  primary source.
- **The licence label is not the whole story.** The oldest public rule sets
  (2utf8, npttf2utf, npm `preeti`) are GPL or non-commercial. The newer
  MIT-labelled packages do not say whether their tables were typed up
  independently or carried over from those. That question was not answered,
  so none of them counts as "clearly MIT-compatible" yet.

### Recommendation

Do not copy any one package's table. Use the same method as the calendar:

1. Samir (or another Preeti typist) supplies real Preeti text with the correct
   Unicode beside it — a few pages of his own typing is enough to start. This
   becomes the golden test set, with its origin written down.
2. Read the single-key facts (which key shows which letter) from at least two
   MIT-licensed tables — nepali-unicoder and preeti-unicode-converter are the
   first two to try — keep only the entries where they agree, and list the
   rest for a native speaker to settle. Before doing this, ask both authors
   (a GitHub issue each) where their tables came from.
3. Write the reordering rules (short i before the consonant, reph after it,
   half forms) in aksharkit's own code, driven by the golden tests.
4. Mark the table "unreviewed by native speaker" until Samir has read through it.

Steps 1 and 2 need Samir: the sample text, and his agreement to open the
issues.

## 5. Bikram Sambat calendar table — verified for BS 2000–2083

BS month lengths are published year by year and cannot be computed.
`src/aksharkit/data/bs_calendar.json` holds the lengths for **BS 2000 to 2083
(14 April 1943 to 13 April 2027)**. It was built on 23 November 2026 by
comparing five published tables and keeping the years on which they agree.

### Sources (all fetched 23 November 2026)

| Source | File | Licence | Commit | Years |
| --- | --- | --- | --- | --- |
| [amitgaru/nepali-datetime](https://github.com/amitgaru/nepali-datetime) | `nepali_datetime/data/calendar_bs.csv` (master) | MIT per `setup.py` and PyPI; the repository's `license.txt` is detected by GitHub as Apache-2.0 | `83bb3b2ea623` | 1975–2100 |
| [medic/bikram-sambat](https://github.com/medic/bikram-sambat) | `test-data/daysInMonth.json` (master) | Apache-2.0 | `aeaa7b883323` | 1970–2090 |
| [opensource-nepal/py-nepali](https://github.com/opensource-nepal/py-nepali) | `nepali/date_converter.py` (main) | MIT | `3ff19477150e` | 2000–2099 |
| [subeshb1/Nepali-Date](https://github.com/subeshb1/Nepali-Date) | `src/date-config.ts` (master) | MIT | `f14e039965ec` | 2000–2090 |
| [akakritagya/nepkit](https://github.com/akakritagya/nepkit) | `src/nepkit/data/calendar.json`, `DATA.md` (main) | MIT | not recorded | 2000–2090 |

Raw URLs are in the JSON file's `sources` list. Notes:

- **nepkit is not an independent source.** Its `DATA.md` says its table came
  from medic/bikram-sambat and was checked against another converter.
- The other four are separate projects, but none names an official origin for
  its numbers, so they may share an ancestor. "Independent" here means
  "published separately", not "derived separately".
- npm `nepali-datetime` 2.0.0 is GPL-3.0 and was not opened.
- **No official source was reached** — no government or calendar-committee
  (पञ्चाङ्ग निर्णायक समिति) table was found online in a readable form.
- Only the numbers were used. The files were read as text by
  `scripts/compare_bs_sources.py`; no code from these projects was run or copied.

### What the comparison found

| Years (BS) | Result | In the table? |
| --- | --- | --- |
| 1970–1999 | Two sources only (nepali-datetime from 1975, medic); they disagree on 1975, 1989, 1991 and 1993 | No |
| 2000–2061 | All five agree exactly | Yes |
| **2062** | nepali-datetime has Baishakh 31, Jestha 31; the other four have Baishakh 30, Jestha 32. The other ten months and the 365-day total agree | **Yes, with a guard — see below** |
| 2063–2083 | All five agree exactly | Yes |
| 2084–2090 | py-nepali differs from the other four in every year | No |
| 2091–2099 | Only nepali-datetime and py-nepali reach this far and they disagree; nepali-datetime's 2096 adds up to 364 days | No |

Other checks that passed: every included year has 12 months of 29 to 32 days
and totals 365 or 366; walking medic's own starting point (BS 1970-01-01 =
13 April 1913) forward lands on BS 2000-01-01 = 14 April 1943, the same day
py-nepali states; the 84 years add up to exactly the 30,681 days between
14 April 1943 and 13 April 2027.

### The disputed month in 2062

The task for this build was "include only years where the sources agree
exactly". 2062 does not meet that. Leaving it out would have cut the table in
two, so it is included with the majority values and a guard: any date from
**31 Baishakh to 32 Jestha 2062 (14 May to 14 June 2005)** raises
`DisputedDateError` unless the caller passes `allow_disputed=True`. Dates
outside those 32 days are the same under both readings.

Outside evidence is split as well, so the question is open:

- Wikipedia's "List of massacres in Nepal" and "Maoist insurgency in Nepal"
  give 6 June 2005 as 24 Jestha 2062 — this fits the majority reading.
- Advocacy Forum press statements give the same day as 23 Jestha 2062 — this
  fits nepali-datetime's reading.

A printed 2062 calendar would settle it.

### Anchors

Date pairs taken from pages that are not date-conversion libraries, all
reproduced by the table (also stored in the JSON file and run as tests):

| BS | AD | Where the pair is stated |
| --- | --- | --- |
| 2000-01-01 | 1943-04-14 | py-nepali's reference date; nepkit `DATA.md` (library sources) |
| 2058-02-19 | 2001-06-01 | Wikipedia, "List of massacres in Nepal" |
| 2062-01-01 | 2005-04-14 | subedirabindra.com.np calendar page (computed; the page warns it can be a day off) |
| 2062-08-29 | 2005-12-14 | Wikipedia, "List of massacres in Nepal" |
| 2072-06-03 | 2015-09-20 | Date line of the Constitution of Nepal (copy hosted by WHO) |
| 2072-11-16 | 2016-02-28 | Date line of the first amendment, same document |
| 2083-01-01 | 2026-04-14 (Tuesday) | The Himalayan Times; Embassy of Nepal, Malaysia |
| 2083-08-07 | 2026-11-23 (Monday) | bikrambhujel.com.np |

### Repeating the comparison

Download the files named above into one directory under these names
(nepkit's `DATA.md` is for reading only): `nd_calendar_bs.csv`, `medic_daysInMonth.json`, `pynepali_date_converter.py`, `subesh_date-config.ts`, `nepkit_calendar.json`.
Then run `python scripts/compare_bs_sources.py <directory>`. The downloaded
files are not kept in this repository.

### Month and weekday names

The Devanagari and romanised month and weekday names in `aksharkit.dates`
were written from general knowledge, not taken from a cited source. Spellings
vary in real use (जेठ/जेष्ठ, असार/आषाढ, मंसिर/मङ्सिर, पुस/पौष, फागुन/फाल्गुन,
चैत/चैत्र; Asar/Ashadh, Mangsir/Mangshir). They await native-speaker review.

## 6. Related packages (licences as listed on PyPI, 23 Nov 2026)

nepalikit 1.0.7 — MIT · nepali-datetime 1.0.8.5 — MIT · nepali 1.2.0 — MIT ·
nepalify 1.0.1.1 — MIT · nepali-date-numword 0.1.2 — MIT · nepkit 0.4.1 — MIT ·
npttf2utf 0.3.7 — GPL-3.0 · npltk 0.3.2 — no licence field on PyPI.
