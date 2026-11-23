# aksharkit

> **Status: pre-release, local build (0.1.0.dev0).** Not yet published to PyPI.
> "aksharkit" is a working name.

A small, typed, dependency-free Python toolkit for everyday Nepali text
chores: cleaning Unicode, converting and formatting numbers, spelling numbers
in words, and splitting text into words and sentences.

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

If you need BS dates or Preeti conversion **now**, use nepali-datetime or
npttf2utf: aksharkit does not do either yet (see the status table).

What aksharkit aims to add:

- **One consistent, fully typed API** (`py.typed`, checked with `mypy --strict`).
- **Zero runtime dependencies** — standard library only.
- **Golden tests** — every number from 0 to 100 in words, digit round-trips
  and a table of awkward sentence splits are pinned in the test suite.
- **Refusing rather than guessing** — features whose data has not been
  verified raise a clear error instead of returning something plausible.
- **Planned:** a JavaScript port and a browser playground (see the roadmap).

No accuracy comparison with other packages has been made. None is claimed.

## Module status

| Module | Status | Notes |
| --- | --- | --- |
| `normalize` | Done | NFC, split vowels, duplicate signs, ZWJ/ZWNJ policy, whitespace, danda repair |
| `numerals` | Done | Devanagari ↔ ASCII digits, 3-2-2 grouping, parsing to `int`/`Decimal` |
| `words` | Done, awaiting native-speaker review of spellings | 0 to 99,99,99,99,99,999; negatives, decimals, rupees and paisa |
| `tokens` | Done | Word tokeniser with offsets, sentence splitter |
| `stopwords` | Done, awaiting review | Short hand-written list |
| `legacy` (Preeti) | **Planned — raises `DataNotVerifiedError`** | Loader and API exist; glyph table is empty |
| `dates` (BS ↔ AD) | **Planned — raises `DataNotVerifiedError`** | Loader and API exist; calendar table is empty |
| Transliteration, spell check | Planned | Roadmap phase 5 |
| JavaScript port, playground | Planned | Roadmap phases 2 and 6 |

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
```

Pass money and other exact values as strings or `Decimal`, not floats.

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

## Further reading

- [docs/normalisation.md](docs/normalisation.md) — exactly what `normalize` changes
- [docs/sources.md](docs/sources.md) — where the number words come from, spelling decisions, candidate data sources
- [docs/known-issues.md](docs/known-issues.md) — current limits
- [ROADMAP.md](ROADMAP.md)

## Licence

MIT. See [LICENSE](LICENSE).
