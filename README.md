# aksharkit

[![CI](https://github.com/Samir-Khadka/aksharkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Samir-Khadka/aksharkit/actions/workflows/ci.yml)

> **Status: pre-release (0.4.0).** Not yet published to PyPI.

A small, typed, dependency-free Python toolkit for everyday Nepali text
chores: cleaning Unicode, converting and formatting numbers, spelling numbers
in words and reading them back, splitting text into words and sentences,
telling scripts apart, converting dates between Bikram Sambat (BS) and AD and
doing arithmetic on them, and writing Devanagari in Roman letters and back.

## Why aksharkit

- **Zero runtime dependencies.** Standard library only.
- **Typed.** Ships `py.typed`; the source, tests and playground glue pass
  `mypy --strict`.
- **Tested.** 1,934 pytest tests passed on the last local run
  (24 November 2026, Python 3.12), plus 14 Node tests of the playground
  script. CI runs the suite on Python 3.10 to 3.13.
- **Refuses rather than guesses.** Dates outside the checked calendar table,
  a disputed month, unreadable number words and the unverified Preeti table
  all raise a clear error.
- **Try before installing.** The [playground](https://samir-khadka.com.np/aksharkit/)
  runs the package itself in your browser.

## Try it in your browser

**<https://samir-khadka.com.np/aksharkit/>**

The playground runs this Python package inside your browser (through
[Pyodide](https://pyodide.org/)), so what you see is what the library does
and nothing you type is sent anywhere. Each result has a copy button, each
tab has examples to tap, and "Copy a link to this result" puts what you typed
in the address after `#`, which browsers do not send to the server.

The 0.3.0 page was checked once in a desktop browser on 24 November 2026.
The 0.4.0 page has only been checked for layout and wiring in a headless
browser with the Python side stubbed; real phones and screen readers are
untested, see [docs/known-issues.md](docs/known-issues.md).

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

If you need Preeti conversion **now**, use npttf2utf or nepalikit: aksharkit
does not do it yet. For BS dates outside BS 2000–2083, or for a full
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
| `normalize` | Done | NFC, split vowels, duplicate signs, ZWJ/ZWNJ policy, whitespace, danda repair |
| `numerals` | Done | Devanagari ↔ ASCII digits, 3-2-2 grouping, parsing to `int`/`Decimal` |
| `words` | Done, awaiting native-speaker review of spellings | 0 to 99,99,99,99,99,999; negatives, decimals, rupees and paisa |
| `words.parse_words` (words → number) | Done (0.4), same table and range | Reads everything `number_to_words` and `currency_to_words` write, plus 47 listed alternative spellings; rejects anything else |
| `detect` | Done (0.4) | Script of a character, token or text by Unicode range, with shares. Does **not** identify the language. `looks_romanised_nepali` is an unmeasured word-list heuristic |
| `tokens` | Done | Word tokeniser with offsets, sentence splitter |
| `stopwords` | Done, awaiting review | Short hand-written list |
| `dates` (BS ↔ AD) | Done for BS 2000–2083 (14 April 1943 to 13 April 2027) | Five published tables compared; one month of 2062 is disputed and refused by default; names await review |
| `dates` arithmetic | Done (0.4), same range and guards | `add_days`, `add_months`, `days_between`, `difference`, `age`, `month_calendar`, `format_month_calendar` |
| `translit` | Done; `simple` spellings await native-speaker review | `iast`: exact and reversible. `simple`: plain ASCII, rule-based and approximate, especially Roman → Devanagari |
| `legacy` (Preeti) | **Planned — raises `DataNotVerifiedError`** | Loader and API exist; glyph table is empty |
| Browser playground (`site/`) | 0.3.0 is live and was checked once in a desktop browser (24 Nov 2026); the 0.4.0 page is not deployed yet | 0.4 adds Words to number, Calendar, Date maths and Detect tabs, copy buttons, examples and shareable links; Preeti shown as coming soon |
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

ak.number_to_words(125000)  # 'एक लाख पच्चिस हजार'
ak.number_to_words("12.5")  # 'बाह्र दशमलव पाँच'
ak.currency_to_words("1250.50", only=True)
# 'एक हजार दुई सय पचास रुपैयाँ पचास पैसा मात्र'

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

## Command line

```console
$ aksharkit words 125000
एक लाख पच्चिस हजार
$ aksharkit words --currency --only 1250.50
एक हजार दुई सय पचास रुपैयाँ पचास पैसा मात्र
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
$ aksharkit convert preeti 'g]kfn'
aksharkit: Preeti conversion is not available yet: ...
```

Words to number is its own command, `aksharkit number`, rather than
`words --reverse`: its input is text, and it takes `--devanagari` and
`--group` for the number it prints. `--add-days`, `--add-months`, `--until`
and `--age` take a BS date; `--calendar` columns are separated by tabs.

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
- [docs/transliteration.md](docs/transliteration.md) — both schemes, the exact rules, what `simple` gets wrong, spellings awaiting review
- [docs/sources.md](docs/sources.md) — where the number words and the calendar table come from, spelling decisions, Preeti source research
- [docs/known-issues.md](docs/known-issues.md) — current limits
- [ROADMAP.md](ROADMAP.md)
- [CHANGELOG.md](CHANGELOG.md)

## Licence

MIT. See [LICENSE](LICENSE).
