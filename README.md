# aksharkit

> **Status: pre-release (0.3.0).** Not yet published to PyPI.

A small, typed, dependency-free Python toolkit for everyday Nepali text
chores: cleaning Unicode, converting and formatting numbers, spelling numbers
in words, splitting text into words and sentences, converting dates between
Bikram Sambat (BS) and AD, and writing Devanagari in Roman letters and back.

## Try it in your browser

**<https://samir-khadka.github.io/aksharkit/>** — *not live yet: the link
starts working after the first GitHub Pages deploy.*

The playground runs this Python package inside your browser (through
[Pyodide](https://pyodide.org/)), so what you see is what the library does
and nothing you type is sent anywhere. It has not yet been tested in a real
browser; see [docs/known-issues.md](docs/known-issues.md).

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
| `tokens` | Done | Word tokeniser with offsets, sentence splitter |
| `stopwords` | Done, awaiting review | Short hand-written list |
| `dates` (BS ↔ AD) | Done for BS 2000–2083 (14 April 1943 to 13 April 2027) | Five published tables compared; one month of 2062 is disputed and refused by default; names await review |
| `translit` | Done; `simple` spellings await native-speaker review | `iast`: exact and reversible. `simple`: plain ASCII, rule-based and approximate, especially Roman → Devanagari |
| `legacy` (Preeti) | **Planned — raises `DataNotVerifiedError`** | Loader and API exist; glyph table is empty |
| Browser playground (`site/`) | Built; **not yet deployed or run in a real browser** | Normalise, Numbers, Dates, Tokenise, Transliterate; Preeti shown as coming soon |
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

ak.tokenize("नेपालको जनसंख्या २,९१,६४,५७८ छ।")
# ['नेपालको', 'जनसंख्या', '२,९१,६४,५७८', 'छ', '।']
ak.sentences("डा. राम आए। मूल्य रु. 99.50 हो। ठिक छ?")
# ['डा. राम आए।', 'मूल्य रु. 99.50 हो।', 'ठिक छ?']

import datetime

ak.ad_to_bs(datetime.date(2026, 11, 23))  # BSDate(year=2083, month=8, day=7)
ak.bs_to_ad(2083, 8, 7)  # datetime.date(2026, 11, 23)
ak.format_bs((2083, 8, 7), "full", devanagari=True)  # '२०८३ मंसिर ७, सोमबार'
ak.fiscal_year(datetime.date(2026, 11, 23))  # '2083/84'

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
$ aksharkit translit "नेपाल राम्रो छ।"
nepāla rāmro cha|
$ aksharkit translit --scheme simple "नेपाल राम्रो छ।"
nepal ramro chha.
$ aksharkit translit --to devanagari "nepāla rāmro cha|"
नेपाल राम्रो छ।
$ aksharkit convert preeti 'g]kfn'
aksharkit: Preeti conversion is not available yet: ...
```

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
