# aksharkit

[![CI](https://github.com/Samir-Khadka/aksharkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Samir-Khadka/aksharkit/actions/workflows/ci.yml)

> **Status: pre-release (0.6.0).** Not yet published to PyPI.

A small, typed, dependency-free Python toolkit for everyday Nepali text
chores: cleaning Unicode, splitting text into aksharas (written syllables),
sorting in Devanagari alphabetical order, converting and formatting numbers,
spelling numbers in words and reading them back, splitting text into words
and sentences, telling scripts apart, converting dates between Bikram Sambat
(BS) and AD, formatting and doing arithmetic on them, and writing Devanagari
in Roman letters and back.

## Why aksharkit

- **Zero runtime dependencies.** Standard library only.
- **Typed.** Ships `py.typed`; the source, tests and playground glue pass
  `mypy --strict`.
- **Tested.** 2,632 pytest tests passed on the last local run
  (24 November 2026, Python 3.12), plus 19 Node tests of the playground
  script. CI runs the suite on Python 3.10 to 3.13.
- **Refuses rather than guesses.** Dates outside the checked calendar table,
  a disputed month and unreadable number words raise a clear error. The
  experimental Preeti converter leaves any key it has no agreed letter for
  unchanged and reports it.
- **Try before installing.** The [playground](https://samir-khadka.com.np/aksharkit/)
  runs the package itself in your browser.

## Try it in your browser

**<https://samir-khadka.com.np/aksharkit/>**

The playground runs this Python package inside your browser (through
[Pyodide](https://pyodide.org/)), so what you see is what the library does
and nothing you type is sent anywhere. Each result has a copy button, each
tab has examples to tap, and "Copy a link to this result" puts what you typed
in the address after `#`, which browsers do not send to the server.

The 0.3.0, 0.4.0 and 0.5.0 pages were each checked once in a desktop browser
on 24 November 2026. The Preeti tab added in 0.6.0 has not been opened in a
browser yet. Real phones and screen
readers are untested for every version, see
[docs/known-issues.md](docs/known-issues.md).

## The problem

Nepali text in the wild is messy. The same visible word can be stored as
several different code-point sequences, so search and de-duplication miss
matches. Numbers appear in two digit sets and with lakh/crore grouping that
generic formatters do not produce. Sentences end in `।` rather than a full
stop, and the full stop itself turns up inside `डा.`, `वि.सं.` and `रु. 99.50`.
A great deal of older material is still stored in legacy fonts such as Preeti,
and dates are in Bikram Sambat.

Each of these has been solved before, usually in a separate package with its
own conventions. aksharkit puts the basics behind one consistent API.

## What exists already

This is not the first Nepali text library, and for some jobs another package
is the better choice today:

| Package | What it covers |
| --- | --- |
| [nepalikit](https://github.com/prabhashj07/nepalikit) | Tokenisation, stemming, normalisation, transliteration, Preeti conversion |
| npltk | Part-of-speech tagging and named-entity recognition |
| [nepali-datetime](https://github.com/amitgaru/nepali-datetime) | Bikram Sambat dates, `datetime`-style API |
| [npttf2utf](https://github.com/trippygeese/npttf2utf) | Legacy font (Preeti and others) to Unicode |

aksharkit's Preeti conversion is **experimental**: its key table has not been
checked against real Preeti documents. For work that matters today, use
npttf2utf or nepalikit, or check aksharkit's output by eye. For BS dates outside BS 2000–2083, or for a full
`datetime`-style API, use nepali-datetime.

What aksharkit aims to add:

- **One consistent, fully typed API** (`py.typed`, checked with `mypy --strict`).
- **Zero runtime dependencies** — standard library only.
- **Golden tests** — every number from 0 to 100 in words, digit round-trips
  and a table of awkward sentence splits are pinned in the test suite.
- **Refusing rather than guessing** — features whose data has not been
  verified raise a clear error instead of returning something plausible.
- **A browser playground** that runs the package itself, so it cannot drift
  from the library.
- **Planned:** a JavaScript port (see the roadmap).

No accuracy comparison with other packages has been made. None is claimed.

## Module status

| Module | Status | Notes |
| --- | --- | --- |
| `normalize` | Done | NFC, split vowels, `र्इ` → `ई` (0.5), duplicate signs, ZWJ/ZWNJ policy, whitespace, danda repair |
| `akshara` | Done (0.5), rules unreviewed | Splits text into written syllables with offsets; count; truncate without cutting a syllable. Orthographic, not phonetic. See [docs/aksharas.md](docs/aksharas.md) |
| `collate` (sorting) | Done (0.5), order awaits native-speaker review | `sort_key`, `sorted_nepali`. One documented set of choices; dictionaries differ and no named dictionary is matched. See [docs/sorting.md](docs/sorting.md) |
| `numerals` | Done | Devanagari ↔ ASCII digits, 3-2-2 grouping, parsing to `int`/`Decimal` |
| `words` | Done, awaiting native-speaker review of spellings | 0 to 99,99,99,99,99,999; negatives, decimals, rupees and paisa |
| `words.ordinal_to_words` | Done for 1–100 (0.5), awaiting native-speaker review | Base form only (पहिलो … सयौँ); no source consulted, all 100 forms listed in [docs/sources.md](docs/sources.md) |
| `words.parse_words` (words → number) | Done (0.4), same table and range | Reads everything `number_to_words` and `currency_to_words` write, plus 47 listed alternative spellings; rejects anything else |
| `detect` | Done (0.4) | Script of a character, token or text by Unicode range, with shares. Does **not** identify the language. `looks_romanised_nepali` is an unmeasured word-list heuristic |
| `tokens` | Done | Word tokeniser with offsets, sentence splitter |
| `stopwords` | Done, awaiting review | Short hand-written list |
| `dates` (BS ↔ AD) | Done for BS 2000–2083 (14 April 1943 to 13 April 2027) | Five published tables compared; one month of 2062 is disputed and refused by default; names await review |
| `dates` patterns and month names | Done (0.5), same range and guards | `format_bs(date, "%-d %B %Y")`; `parse_bs("२०८३ मंसिर ८")`. Only the package's own month spellings are read |
| `dates` arithmetic | Done (0.4), same range and guards | `add_days`, `add_months`, `days_between`, `difference`, `age`, `month_calendar`, `format_month_calendar` |
| `translit` | Done; `simple` spellings await native-speaker review | `iast`: exact and reversible. `simple`: plain ASCII, rule-based and approximate, especially Roman → Devanagari |
| `legacy` (Preeti → Unicode) | **Experimental (0.6)** — not checked against real Preeti documents or by a native reader | 126 keys agreed by at least 2 of 3 families of MIT-licensed tables; own reordering rules; unmapped characters reported, never guessed. Unicode → Preeti is not implemented. See [docs/preeti.md](docs/preeti.md) |
| Browser playground (`site/`) | 0.5.0 is live and was checked once in a desktop browser on 24 Nov 2026, phone untested | 0.4 added Words to number, Calendar, Date maths and Detect tabs, copy buttons, examples and shareable links; 0.5 adds Aksharas and Sort tabs, ordinals and date patterns; 0.6 turns the Preeti tab on (experimental), not yet opened in a browser |
| Spell check | Planned | Roadmap phase 5 |
| JavaScript port | Planned | Roadmap phase 6 |

## Quick start

Requires Python 3.10 or newer. Until there is a release, install from a checkout:

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

```python
import aksharkit as ak

ak.normalize("  राम   घर गयो|  ")  # 'राम घर गयो।'
ak.to_devanagari_digits("2083-08-07")  # '२०८३-०८-०७'
ak.format_number(1234567)  # '12,34,567'
ak.format_number("1234567.5", devanagari=True)  # '१२,३४,५६७.५'
ak.parse_number("१२,३४,५६७")  # 1234567

ak.aksharas("नमस्ते")  # ['न', 'म', 'स्ते']
ak.aksharas("विद्यार्थी")  # ['वि', 'द्या', 'र्थी']
ak.akshara_count("काठमाडौँ उपत्यका")  # 9   (the space counts; skip_whitespace=True gives 8)
ak.truncate("विद्यार्थीहरू विद्यालय गए", 6, suffix="…")  # 'विद्यार्थीहरू…'

ak.sorted_nepali(["हात", "कमल", "ज्ञान", "क्षेत्र", "काम", "अंक", "अक", "आमा", "त्रिशूल", "तारा"])
# ['अंक', 'अक', 'आमा', 'कमल', 'काम', 'तारा', 'हात', 'क्षेत्र', 'त्रिशूल', 'ज्ञान']
ak.sorted_nepali(["हात", "क्षेत्र", "कमल", "ज्ञान"], conjunct_letters=False)
# ['कमल', 'क्षेत्र', 'ज्ञान', 'हात']

ak.number_to_words(125000)  # 'एक लाख पच्चिस हजार'
ak.number_to_words("12.5")  # 'बाह्र दशमलव पाँच'
ak.currency_to_words("1250.50", only=True)
# 'एक हजार दुई सय पचास रुपैयाँ पचास पैसा मात्र'

ak.ordinal_to_words(1)  # 'पहिलो'
ak.ordinal_to_words(21)  # 'एक्काइसौँ'   (1 to 100; forms await native-speaker review)

ak.parse_words("एक लाख पच्चिस हजार")  # 125000
ak.parse_words("एक लाख पच्चीस हजार")  # 125000   (listed alternative spelling)
ak.parse_words("ऋण बाह्र दशमलव पाँच")  # Decimal('-12.5')
ak.parse_words("एक हजार दुई सय पचास रुपैयाँ पचास पैसा मात्र")  # Decimal('1250.50')

ak.tokenize("नेपालको जनसंख्या २,९१,६४,५७८ छ।")
# ['नेपालको', 'जनसंख्या', '२,९१,६४,५७८', 'छ', '।']
ak.sentences("डा. राम आए। मूल्य रु. 99.50 हो। ठिक छ?")
# ['डा. राम आए।', 'मूल्य रु. 99.50 हो।', 'ठिक छ?']

ak.detect_script("नेपाल राम्रो छ।")  # 'devanagari'
ak.detect_script("Facebookमा photo राख्नुहोस्")  # 'mixed'
ak.token_scripts("म school जान्छु")
# [('म', 'devanagari'), ('school', 'latin'), ('जान्छु', 'devanagari')]
ak.looks_romanised_nepali("timi kasto cha? malai ramro lagyo")  # True   (rough heuristic)

import datetime

ak.ad_to_bs(datetime.date(2026, 11, 23))  # BSDate(year=2083, month=8, day=7)
ak.bs_to_ad(2083, 8, 7)  # datetime.date(2026, 11, 23)
ak.format_bs((2083, 8, 7), "full", devanagari=True)  # '२०८३ मंसिर ७, सोमबार'
ak.format_bs((2083, 8, 8), "%-d %B %Y, %A", devanagari=True)  # '८ मंसिर २०८३, मङ्गलबार'
ak.format_bs((2083, 8, 8), "%d/%m/%y (%a)")  # '08/08/83 (Man)'
ak.parse_bs("२०८३ मंसिर ८")  # BSDate(year=2083, month=8, day=8)
ak.parse_bs("8 Mangsir 2083")  # BSDate(year=2083, month=8, day=8)
ak.fiscal_year(datetime.date(2026, 11, 23))  # '2083/84'

ak.add_days((2083, 8, 7), 30)  # BSDate(year=2083, month=9, day=8)
ak.add_months((2083, 3, 32), 1)  # BSDate(year=2083, month=4, day=31)   (day clamped)
ak.days_between((2083, 1, 1), (2083, 8, 7))  # 223
ak.difference((2059, 5, 12), (2083, 8, 7))  # BSDifference(years=24, months=2, days=25)
ak.age((2059, 5, 12), on=(2083, 8, 7))  # 24
ak.days_in_month(2083, 8)  # 29
ak.month_calendar(2083, 8)[0]  # [0, 0, 1, 2, 3, 4, 5]   (Sunday first, 0 = blank)

ak.to_roman("नेपाल राम्रो छ।")  # 'nepāla rāmro cha|'   (iast: exact)
ak.to_devanagari("nepāla rāmro cha|")  # 'नेपाल राम्रो छ।'
ak.to_roman("नेपाल राम्रो छ।", "simple")  # 'nepal ramro chha.'   (approximate)
ak.to_devanagari("mero ghar", "simple")  # 'मेरो घर'   (best effort)
```

Pass money and other exact values as strings or `Decimal`, not floats.

**Transliteration has two schemes.** `iast` uses diacritics and converts
back to exactly the text you started with. `simple` is plain ASCII, the way
Nepali is typed in chat; it is rule-based and approximate. It does not
reproduce customary spellings (काठमाडौँ gives `kathamadaun`, not Kathmandu),
and reading it back is a guess: `nepal` becomes नेपल, because a single `a`
is always the short vowel. See [docs/transliteration.md](docs/transliteration.md).

**Aksharas follow the writing, not the sound.** `नमस्ते` is `न`, `म`, `स्ते`,
and a final halant consonant (`न्` in `श्रीमान्`) is a unit of its own. The rules
are this project's own and are set out, with their limits, in
[docs/aksharas.md](docs/aksharas.md).

**The sort order is one set of choices.** Dictionaries differ on where
anusvara goes and on whether `क्ष`, `त्र`, `ज्ञ` are letters of their own.
[docs/sorting.md](docs/sorting.md) lists every choice made here. The order
has not been checked against any dictionary and is not claimed to match one.

**Ordinals are unreviewed.** `ordinal_to_words` covers 1 to 100 in one base
form. Six forms are listed by hand and the rest come from a rule; no source
was consulted. The forms for 59–70 and 79–98 (`साठीऔँ`, `असीऔँ` …) are the least
certain.

**Date patterns** use `%Y %y %m %-m %B %d %-d %A %a %%`; anything else after
a `%` is an error. `parse_bs` reads a month name only in the spelling the
package itself writes, and refuses two-digit years and month-first order.

**`parse_words` is strict.** It reads the spellings in the package's table
and the alternatives listed in [docs/sources.md](docs/sources.md), and raises
`ValueError` naming the word it could not read. It does not correct typos and
does not read ordinals or fractions.

**`detect` reports scripts, not languages.** Nepali, Hindi, Marathi, Maithili
and other languages written in Devanagari all come back as `devanagari`;
nothing in this package tells them apart. `looks_romanised_nepali` counts
matches against a short hand-written word list. Its accuracy has not been
measured, and romanised Hindi or Maithili can pass it.

Dates outside BS 2000–2083 raise `DateRangeError`. Dates from 14 May to
14 June 2005 raise `DisputedDateError` unless you pass `allow_disputed=True`,
because the published calendars disagree by one day there. Both are
`ValueError`s. See [docs/sources.md](docs/sources.md) for how the table was checked.

**Preeti to Unicode is experimental.** Its key table is what at least 2 of 3
families of MIT-licensed tables agree on; it has not been checked against
real Preeti documents or by a native reader.

```python
from aksharkit import convert_preeti, preeti_to_unicode

preeti_to_unicode("g]kfn")  # 'नेपाल'
result = convert_preeti("sfo{qmd ¥")  # ¥ has no agreed letter
result.text  # 'कार्यक्रम ¥'
result.unmapped  # (UnmappedChar(char='¥', offset=8),)
```

Characters with no agreed letter are left as they are and listed in
`result.unmapped`, never guessed. If you have real Preeti text with the
correct Unicode beside it, `tests/golden/preeti_samples.tsv` is where it
goes. Details: [docs/preeti.md](docs/preeti.md).

## Command line

```console
$ aksharkit words 125000
एक लाख पच्चिस हजार
$ aksharkit words --currency --only 1250.50
एक हजार दुई सय पचास रुपैयाँ पचास पैसा मात्र
$ aksharkit words --ordinal 5
पाँचौँ
$ aksharkit aksharas नमस्ते --sep " | "
न | म | स्ते
$ aksharkit aksharas --count "काठमाडौँ उपत्यका"
9
$ aksharkit aksharas --truncate 6 --suffix … "विद्यार्थीहरू विद्यालय गए"
विद्यार्थीहरू…
$ printf 'हात\nकमल\nज्ञान\nक्षेत्र\nकाम\n' | aksharkit sort
कमल
काम
हात
क्षेत्र
ज्ञान
$ aksharkit number "एक लाख पच्चीस हजार"
125000
$ aksharkit number --group "बाह्र लाख पचास हजार"
12,50,000
$ aksharkit format --devanagari 1234567
१२,३४,५६७
$ aksharkit digits --to ascii २०८३
2083
$ echo "राम घर गयो|" | aksharkit normalize
राम घर गयो।
$ aksharkit tokenize --sentences "के छ? ठिक छ।"
के छ?
ठिक छ।
$ aksharkit date 2026-11-23
2083-08-07
$ aksharkit date --style full --devanagari 2026-11-23
२०८३ मंसिर ७, सोमबार
$ aksharkit date --to ad 2083-08-07
2026-11-23
$ aksharkit date --to ad "२०८३ मंसिर ८"
2026-11-24
$ aksharkit date 2026-11-24 --pattern "%-d %B %Y, %A" --devanagari
८ मंसिर २०८३, मङ्गलबार
$ aksharkit date --fiscal-year 2026-11-23
2083/84
$ aksharkit date --calendar 2083-08
Mangsir 2083
Aai	Som	Man	Bud	Bih	Shu	Sha
		1	2	3	4	5
6	7	8	9	10	11	12
13	14	15	16	17	18	19
20	21	22	23	24	25	26
27	28	29
$ aksharkit date 2083-08-07 --add-days 30
2083-09-08
$ aksharkit date 2083-03-32 --add-months 1
2083-04-31
$ aksharkit date 2059-05-12 --until 2083-08-07
24 years, 2 months, 25 days (8853 days)
$ aksharkit date 2059-05-12 --age --until 2083-08-07
24
$ aksharkit detect "Facebookमा photo राख्नुहोस्"
script: mixed
devanagari: 48.0%
latin: 52.0%
digit: 0.0%
other: 0.0%
$ aksharkit detect --tokens "म school जान्छु"
म	devanagari
school	latin
जान्छु	devanagari
$ aksharkit translit "नेपाल राम्रो छ।"
nepāla rāmro cha|
$ aksharkit translit --scheme simple "नेपाल राम्रो छ।"
nepal ramro chha.
$ aksharkit translit --to devanagari "nepāla rāmro cha|"
नेपाल राम्रो छ।
$ aksharkit convert preeti 'g]kfn' --quiet
नेपाल
$ aksharkit convert preeti 'sfo{qmd ¥' --quiet --report
कार्यक्रम ¥
aksharkit: warning: 1 character(s) had no agreed Preeti entry and were left unchanged: ¥ (U+00A5)
  position 8: ¥ (U+00A5)
```

`convert preeti` is experimental: without `--quiet` it says so on standard
error every time. The warning lines above also go to standard error, and the
exit code stays 0.

Words to number is its own command, `aksharkit number`, rather than
`words --reverse`: its input is text, and it takes `--devanagari` and
`--group` for the number it prints. `--add-days`, `--add-months`, `--until`
and `--age` take a BS date; `--calendar` columns are separated by tabs.
`aksharkit aksharas` prints one akshara per line unless `--sep` is given;
`aksharkit sort` reads one item per line from standard input (or from one
argument holding the lines).

Exit codes: `0` success, `2` bad input, `3` feature not available yet.

## Development

```bash
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy
```

To look at the playground locally:

```bash
python scripts/build_site.py --out _site
python -m http.server --directory _site   # then open http://localhost:8000
```

`build_site.py` copies `site/` and packs `src/aksharkit` into
`_site/pkg/aksharkit.zip`, which the page unpacks inside Pyodide. The same
script runs in `.github/workflows/pages.yml`. If Node.js is installed,
`pytest` also drives `site/app.js` against a fake DOM (`tests/js/`).

## Further reading

- [docs/normalisation.md](docs/normalisation.md) — exactly what `normalize` changes
- [docs/aksharas.md](docs/aksharas.md) — the akshara rules and their limits
- [docs/sorting.md](docs/sorting.md) — the sort order, choice by choice
- [docs/transliteration.md](docs/transliteration.md) — both schemes, the exact rules, what `simple` gets wrong, spellings awaiting review
- [docs/preeti.md](docs/preeti.md) — the experimental Preeti converter: sources and licences, what agreed and what did not, the reordering rules, what is not checked
- [docs/sources.md](docs/sources.md) — where the number words and the calendar table come from, spelling decisions, the 100 ordinal forms for review, Preeti candidates
- [docs/known-issues.md](docs/known-issues.md) — current limits
- [ROADMAP.md](ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)

## Licence

MIT. See [LICENSE](LICENSE). The Preeti key table was compiled by comparing
the tables of four MIT-licensed projects; their copyright notices are in
[NOTICE](NOTICE).
