# Preeti to Unicode (experimental)

> **Status: experimental — mapping agreed by at least 2 of 3
> permissively-licensed table families (4 projects), not yet checked against
> real Preeti documents or by a native reader.**

Preeti is a legacy font: a file typed in it holds Latin letters and symbols
(`g]kfn`) that only look like Nepali (`नेपाल`) while that font is installed.
`aksharkit.legacy` turns such text into Unicode.

```python
from aksharkit import convert_preeti, preeti_to_unicode

preeti_to_unicode("g]kfn")  # 'नेपाल'

result = convert_preeti("sfo{qmd ¥")
result.text  # 'कार्यक्रम ¥'
result.unmapped  # (UnmappedChar(char='¥', offset=8),)
result.complete  # False
```

```console
$ aksharkit convert preeti 'd]/f] gfd ;ld/ xf] .' --quiet
मेरो नाम समिर हो ।
$ echo 'sfo{qmd ¥' | aksharkit convert preeti - --quiet --report
कार्यक्रम ¥
aksharkit: warning: 1 character(s) had no agreed Preeti entry and were left unchanged: ¥ (U+00A5)
  position 8: ¥ (U+00A5)
```

The warning goes to standard error and the exit code stays 0. Options go
after the text. `--quiet` hides the one-line experimental notice, `--report`
lists each unmapped character with its position, `--include-unconfirmed` and
`--strict` change which keys are used (below).

## What has and has not been checked

Checked:

- every key in the table against what four published tables say for it
  (`scripts/compare_preeti_sources.py --check` repeats this);
- that the reordering rules do what this page says, on inputs typed by the
  builder from the table.

**Not checked:**

- **No real Preeti document has been converted.** Every sample in the tests
  was typed from the table itself, so the tests show the parts are consistent
  with each other, not that they are right.
- **No native reader has looked at the table or the output.**
- **Nobody opened the Preeti font** to see what each key draws. The table
  rests entirely on other converters' tables, and where they share a mistake,
  so does this one.
- Whether the four tables are truly independent of each other, or of older
  tables under licences this project cannot use, is not known (see
  "How independent are the sources?").

Real samples go in `tests/golden/preeti_samples.tsv`. The file explains the
format; each line added becomes a test.

## Sources

Read as plain text on 24 November 2026, at the commits shown. Licences are
from each project's own LICENSE file.

| Family | Project | Version, commit | Licence | Table read | Says where its table came from? |
| --- | --- | --- | --- | --- | --- |
| A | [nepali-unicoder](https://github.com/realsanjeev/nepali_unicoder) | 0.3.0, `3bb1e3b1` | MIT, Copyright (c) 2025 RealSanjeev | `src/nepali_unicoder/data/preeti_rules.json` | No |
| A | [nepalikit](https://github.com/prabhashj07/nepalikit) | repository head, `089831f8` | MIT, Copyright (c) 2024 Prabhash Kumar Jha | `nepalikit/transliterate/preeti.py` | No |
| B | [preeti-unicode-converter](https://github.com/diwaskunwar/preeti-unicode-converter) | 0.1.1, `9e137b98` | MIT, Copyright (c) 2024 Diwas Kunwar | `src/preeti_unicode/converter.py` | Only "Thanks to the Nepali computing community for font specifications" |
| C | [nepali-keyboard](https://github.com/prabin194/nepali-keyboard) | 1.3.0, `65a01d40` | MIT, Copyright (c) 2026 Prabin Paudel | `src/preeti.ts` | No |

Full commit hashes and the values each project states are in
`scripts/preeti_sources.json`; the copyright notices are in `NOTICE`.

### Left out

| Project | Why |
| --- | --- |
| npttf2utf | GPL-3.0. Not opened. |
| foss-np/2utf8, npm `preeti` | CC BY-NC-SA (non-commercial). Not opened. |
| sapradhan/nep-ttf2utf | Described elsewhere as a port of 2utf8. Not opened. |
| nepalibhasha/nepali-fonts (`nepali-converter`), commit `c2dcb305` | MIT-labelled, but the header of its Preeti map names npttf2utf as a reference. Excluded on reading that header; nothing from it was used. |
| npm `preeti-to-unicode` 1.0.12 (MIT), `unicode-to-preeti` 1.0.0 (ISC), `preeti-unicode` 0.0.1 (ISC) | Only the registry metadata was read. They ship bundled builds, two list no repository, and none says where its table came from. Their tables were not read. |

### How independent are the sources?

Honestly: not proven, in three ways.

1. **nepali-unicoder and nepalikit share one rule list**, entry for entry.
   They are counted as one family (A), so their agreement with each other
   counts for nothing.
2. **Family A's shape** (a key table plus a list of rewrite rules using a
   placeholder letter) is a common shape for Preeti converters, including,
   as far as the builder knows without having opened them, the GPL and
   non-commercial ones listed above. Neither project says it was carried
   over from those. This is an open question, not a finding.
3. **nepali-keyboard's keys are a subset of nepalikit's**, and they give the
   same letter for 121 of 125 shared keys. For the 16 keys below, the only
   two tables that have the key at all are these two, so "two families
   agree" is at its weakest there:

   `¢ ± ´ Å Ö Ø Û Ü ß ç ˜ „ • … ‹ ›`

In the other direction: the three families store their tables differently
and make different mistakes (see "Keys where a table differs"), which is
what separately typed tables look like. 92 of the 126 keys used by default
are carried by families B and C without any help from family A.

The way to settle this is to ask the four authors where their tables came
from. That has not been done.

## The table

`src/aksharkit/data/font_preeti.json`, written from the comparison. One vote
per family; a family whose own projects disagree on a key has no vote on it.

| Tier | Keys | Used |
| --- | --- | --- |
| `mapping` — two or more families agree, no table differs | 122 | Always |
| `majority` — two or more families agree, one table differs | 4 | By default; not with `strict=True` / `--strict` |
| `unconfirmed` — one family only | 5 | Only with `include_unconfirmed=True` / `--include-unconfirmed` |
| `disputed` — no two families agree | 5 | Never |
| `sequences` — two-key combinations, two or more families | 5 | Always |
| `unconfirmed_sequences` — one family only | 2 | Only with `include_unconfirmed` |

136 single keys were compared. Every printable ASCII character is covered:
92 by the first two tiers, and `m` and `{`, which are strokes rather than
letters and are handled by the rules below. Each entry records the families
that agreed and, for `majority`, the table that differed.

### Keys where a table differs (`majority`)

| Key | Used | Agreeing | Differing |
| --- | --- | --- | --- |
| `B` | द्य | nepali-unicoder, nepalikit, nepali-keyboard | preeti-unicode-converter: ध |
| `^` | ६ | nepali-unicoder, preeti-unicode-converter, nepali-keyboard | nepalikit: ० |
| `¡` | ज्ञ् | nepalikit, nepali-keyboard | preeti-unicode-converter: ्र |
| `¿` | रू | nepali-unicoder, nepalikit, nepali-keyboard | preeti-unicode-converter: ्र |

`^` is Shift+6 in a row where Shift+1 to Shift+5 and Shift+7 to Shift+0 are
agreed to be १–५ and ७–०, and `w` is agreed to be ध, so the two differing
values for `^` and `B` look like slips. That is an inference, which is why
these four sit in their own tier and can be switched off.

### One family only (`unconfirmed`)

`¤` झ्, `©` र, `Ò` ¨, `×` ×, `‘` ॅ — all from nepalikit alone. The two
sequences `8Þ` ड़ and `9Þ` ढ़ come from nepali-keyboard alone.

### No agreement (`disputed`, never used)

| Key | Values |
| --- | --- |
| `¥` | nepali-unicoder र्; nepalikit र् + ZWJ |
| `°` | nepali-keyboard ड्ढ; nepalikit ङ्ढ; preeti-unicode-converter ्र |
| `Ì` | nepali-keyboard त्र; nepalikit न्न |
| `Ú` | nepali-keyboard ’; nepalikit ’; nepali-unicoder : |
| `Ý` | nepali-keyboard ट्ठ; nepalikit ट्ट् |

(`Ú` is disputed because family A's two projects disagree with each other,
which leaves only one family voting.)

## Reordering rules

These are aksharkit's own, written from how Devanagari is stored in Unicode,
not from any project's rule list. Where a typing fact (not a rule) had to
come from the sources, the families that state it are named.

1. **Keys to letters.** Two-key sequences first, then single keys. Text that
   is already Devanagari, and white space, pass through untouched.
2. **The `m` stroke** completes the letter before it: `k`+`m` फ, `e`+`m` झ,
   `p`+`m` ऊ, `q`+`m` क्र, `Q`+`m` क्त (all: families A, B or C, at least
   two). Vowel signs or a subscript typed between the two are skipped over,
   so `k"mn` and `km"n` both give फूल, and `k|m` gives फ्र (the skipping is
   stated by A and C). An `m` with no such letter before it is reported as
   unmapped.
3. **Half form + upright bar = the full letter.** Preeti draws ण, क्ष, ष and
   others as a half form followed by the `f` bar; `0f` is ण, not ण्ा
   (A, B, C).
4. **Short i (`l`) is typed before its consonant and stored after it**
   (A, B, C). It moves to the end of the consonant cluster that follows it:
   half forms and subscripts included, so `l:ylt` is स्थिति. With no
   consonant after it, it stays where it was typed.
5. **Reph (`{`) is typed after the syllable and stored before it** as र्
   (A, B). It moves to the front of the cluster it follows, skipping back
   over that syllable's vowel signs: `sfo{` is कार्य, `kf6L{` is पार्टी. After
   an independent vowel it gives र् + vowel, and the normaliser turns र्इ
   into ई, so `O{` is ई (A, C). With nothing before it to sit on, it is
   reported as unmapped.
6. **Sign order within a syllable**: vowel signs, then candrabindu or
   anusvara, then visarga, whatever order they were typed in.
7. **Normalise.** The package's `normalize` composes split vowels
   (`cf` आ, `cf]` ओ, `sf]` को, `P]` ऐ) and drops doubled signs. White space
   and `|` are left alone here.

## What it does not do

- **Unicode → Preeti.** `legacy.unicode_to_preeti` raises
  `NotImplementedError`. Going back needs choices the table cannot make
  (which of several keys draws a conjunct), and there is nothing to test it
  against.
- **Other fonts** (Kantipur, Himali, Sagarmatha, PCS Nepali): not supported.
- **Mixed text.** It cannot tell Preeti from English. An English word in the
  input is converted as if it were Preeti; convert only the Preeti parts.
- **Typing habits it has not seen.** Real typists overstrike, repeat signs,
  and use keys in ways no table lists. Four one-family notes were left out:
  `f‘` for ॉ, `N˜` for ल, `6[` for ट्ट, and `M` at the start of a word as a
  colon.
- **Disputed and unknown keys** are left exactly as they are. Read the
  unmapped list: a short one usually means a rare conjunct key, a long one
  usually means the text is not Preeti.
- A half form at the end of a word followed by a space is left with its
  virama, even where the typist meant something else.

## Repeating the comparison

```console
$ python scripts/compare_preeti_sources.py          # the report
$ python scripts/compare_preeti_sources.py --check  # the table matches it
$ python scripts/compare_preeti_sources.py --write  # regenerate the table
```
