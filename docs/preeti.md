# Preeti and Unicode (experimental)

> **Status: experimental — mapping agreed by at least 2 of 3
> permissively-licensed table families (4 projects), not yet checked against
> real Preeti documents or by a native reader.**

Preeti is a legacy font: a file typed in it holds Latin letters and symbols
(`g]kfn`) that only look like Nepali (`नेपाल`) while that font is installed.
`aksharkit.legacy` turns such text into Unicode, and Unicode back into Preeti
keys. Version 0.7 added Word (.docx) files, text files, protected stretches,
the other direction and fuller reports. Version 0.8 works on the other
direction, Unicode to Preeti: a coverage audit, better encoding rules, a
hand-written word list, Word files and a clearer playground. **None of that
changes the status above:** the key table is the 0.6 table, and it is still
unchecked against real documents.

```python
from aksharkit import convert_preeti, preeti_to_unicode

preeti_to_unicode("g]kfn")  # 'नेपाल'

result = convert_preeti("sfo{qmd ¥")
result.text  # 'कार्यक्रम ¥'
result.unmapped  # (UnmappedChar(char='¥', offset=8),)  also .line, .column, .output_offset
result.complete  # False
result.stats  # PreetiStats(agreed=7, majority=0, unconfirmed=0, unmapped=1, untouched=1, protected=0)
```

```console
$ aksharkit convert preeti 'd]/f] gfd ;ld/ xf] .' --quiet
मेरो नाम समिर हो ।
$ aksharkit convert preeti -i patra.txt -o patra-unicode.txt --report
aksharkit: note: Preeti conversion is experimental — mapping agreed by at least 2 of 3 permissively-licensed table families (4 projects), not yet checked against real Preeti documents or by a native reader
aksharkit: warning: 1 character(s) had no agreed Preeti entry and were left unchanged: ¥ (U+00A5)
  line 3, column 10: ¥ (U+00A5)
aksharkit: summary: 34 character(s) to convert: 32 by agreed keys (94.1%), 1 by majority keys (2.9%), 1 left unchanged (2.9%); 2 stretch(es) protected
```

Notes and warnings go to standard error and the exit code stays 0, unless
`--fail-on-unmapped` is given (then 1 when anything was left unconverted).
An error (a missing file, an output that already exists) exits with 2.

## Word files (.docx)

```python
from aksharkit import convert_docx

report = convert_docx("suchana.docx", "suchana-unicode.docx")
report.runs_converted, report.runs_untouched  # (11, 6)
report.unmapped  # (DocxUnmapped(part='word/document.xml', paragraph=2, char='¥'), ...)
report.stats.share("agreed")  # 0.959...
```

```console
$ aksharkit convert preeti --docx suchana.docx -o suchana-unicode.docx --report
aksharkit: warning: 2 character(s) had no agreed Preeti entry and were left unchanged: ¥ (U+00A5) Ý (U+00DD)
  word/document.xml, paragraph 2: ¥ (U+00A5)
  word/document.xml, paragraph 2: Ý (U+00DD)
aksharkit: docx: 11 run(s) converted and set to Kalimati, 6 run(s) in other fonts left as they were, 7 paragraph(s) changed, 0 run boundary move(s); parts read: word/document.xml, word/header1.xml, word/footer1.xml, word/footnotes.xml
aksharkit: docx: fonts found on text runs: Calibri (6), Preeti (11)
aksharkit: summary: 74 character(s) to convert: 71 by agreed keys (95.9%), 1 by majority keys (1.4%), 2 left unchanged (2.7%)
```

(The experimental notice line is left out above. The document in this
example was built by the project's own test code, not written in Word.)

Standard library only (`zipfile` and the `expat` parser); python-docx is not
needed. `convert_docx_bytes(data)` does the same on bytes and returns
`(new_bytes, report)`.

**What is converted.** Only the text of runs whose font is Preeti. Everything
else in the file — English runs, other fonts, pictures, styles, settings,
every other part of the archive — is copied through byte for byte. The
changes are made in place in the XML text, so nothing is re-serialised.

**What "its font is Preeti" means.** A run counts when both its `w:ascii` and
`w:hAnsi` fonts resolve to Preeti (the name is compared without regard to
case; `source_fonts=("Preeti", "PREETI Normal")` or `--source-font` adds
others). The font is looked up in this order:

| Where the font is stated | Handled |
| --- | --- |
| `w:rFonts` on the run itself | Yes |
| The run's character style (`w:rStyle`), and the styles it is based on | Yes |
| The paragraph's style (`w:pStyle`), the styles it is based on, and the default paragraph style when none is named | Yes |
| Document defaults (`w:docDefaults`) | Yes |
| Theme fonts (`w:asciiTheme` and so on), read from `word/theme/theme1.xml` | Yes |
| Table styles, and table-level conditional formatting | **No** |
| Numbering definitions (the font of a list number or bullet) | **No** — list labels are not runs and are never touched |
| Fonts inside a tracked formatting change (`w:rPrChange`) | Ignored; the current font is used and the tracked change is kept whole |
| The paragraph mark's own properties | Ignored (they hold no text) |
| A run with Preeti in only one of `w:ascii` and `w:hAnsi` | **Left alone**, and counted in `report.runs_partial_font` |
| A run with Preeti only as its complex-script font (`w:cs`) | **Left alone**, counted with the other fonts |
| Text in drawings and text boxes written as DrawingML (`a:t`), charts, SmartArt | **No** |
| Field codes (`w:instrText`) and deleted text in tracked changes (`w:delText`) | Left alone on purpose |

`report.fonts_seen` lists the Latin (`w:ascii`) font of every text run with a count, so a
document whose Preeti text hides under another name ("PREETI", "Preeti
Normal") shows up at once.

**Parts read.** The body with its tables (`word/document.xml`), headers,
footers, footnotes, endnotes and comments. A file that is not a zip, an old
`.doc` file, a password-protected file and a part that is not UTF-8 are
refused with a message.

**The font put on converted text.** Converted runs get
`w:ascii`, `w:hAnsi` and `w:cs` set to **Kalimati** by default
(`font="Noto Sans Devanagari"` or `--font` to choose another); `w:eastAsia`
is kept. Only the *name* is written: aksharkit does not ship, embed or check
for any font. If the reader's computer has no font of that name, the word
processor substitutes one of its own. Kalimati is a common Unicode
Devanagari font name in Nepal; it is a default, not a recommendation tested
on real machines. Word draws Devanagari with the
"complex script" bold, italic and size, so where those differ from the
ordinary ones they are copied across (`w:bCs`, `w:iCs`, `w:szCs`); every other
property of the run is left as it was.

**Words split across runs.** Word often cuts one word into several runs
(`lj` + `Bf` + `yL{`), and Preeti's short i and reph have to move across the
cut. Runs of Preeti text that follow each other in a paragraph are converted
as one stretch, then the result is shared back out so that every run keeps
its own formatting. Where a letter and its sign would land in different runs,
the fewest leading characters are moved to the run before
(`report.boundary_moves`). If no cut gives the right text, the whole stretch
goes into its first run (`report.groups_merged`); that changes which
formatting some letters carry, never the text. A tab, a line break, a
picture or a run in another font ends the stretch. The tests check, for 300
random splits, that the joined text is exactly what converting the whole
stretch gives.

**Never overwrites.** `convert_docx` refuses when the output is the input,
and when the output exists unless `overwrite=True` (`--force`).

**Not checked:** no document produced by Microsoft Word has been through
this, and no output has been opened in Microsoft Word. The test documents
are built by the tests themselves. On the build machine python-docx and
LibreOffice both opened the output of the mixed test document.

## Text files and batches

```console
$ aksharkit convert preeti -i in.txt -o out.txt            # one file
$ aksharkit convert preeti -i a.txt -i b.txt --out-dir out # several, same names
$ aksharkit convert preeti - < in.txt > out.txt            # standard input and output
$ aksharkit convert preeti -i old.txt --encoding cp1252 -o out.txt
```

Line breaks (`\n` and `\r\n`), tabs, blank lines and runs of spaces come out
as they went in, and nothing is added at the end of a file. Files are read as
UTF-8, with or without a byte-order mark; text that is not valid UTF-8 is
refused with a message that names `--encoding` (older Preeti text files are
often cp1252). The output is UTF-8 without a byte-order mark. An input file
is never written to, an existing output is refused without `--force`, and a
zip or other binary file given to `-i` is refused.

## Leaving parts of the text alone

Preeti text is Latin letters, so the converter cannot see which words are
English. It never guesses. What it offers instead:

| What | How | Applies to |
| --- | --- | --- |
| Web addresses (`http://`, `https://`, `www.`) and e-mail addresses | Left alone automatically; `keep_links=False` or `--no-keep-links` turns it off | Plain text. In a .docx it is off unless `keep_links=True`, because there the font already says what is Preeti |
| Anything matching a pattern | `keep=r"[A-Z]+-\d+"` or `--keep REGEX` (repeatable) | Both |
| Whole words | `keep_words=["Kathmandu"]` or `--keep-word WORD` (repeatable) | Both |
| Marked stretches | `markers=("[[", "]]")` or `--markers '[[' ']]'`: the text between is kept and the markers are removed | Plain text |

```console
$ aksharkit convert preeti 'g]kfn [[Kathmandu Post]] df' --markers '[[' ']]' --quiet
नेपाल Kathmandu Post मा
$ aksharkit convert preeti 'ID AB-123 g]kfn' --keep '[A-Z]+-\d+' --keep-word ID --quiet
ID AB-123 नेपाल
```

Protected stretches are listed in `result.protected` with their place and the
reason (`link`, `keep`, `word`, `marker`). An opening marker with no closing
one is an error that names the line and column.

**Known wrong answer.** Preeti text that happens to have the shape of an
e-mail address is left alone: `s@v.ug` is kept as it is, although typed in
Preeti it would be Nepali. Use `--no-keep-links` for text with no addresses
in it.

**Why there is no "skip English words" switch.** One was considered and left
out. Ordinary Preeti words are made of plain ASCII letters (`dfof` is माया,
`sdn` is कमल, `gfd` is नाम), and ordinary English words convert to
plausible-looking Devanagari (`the cat` becomes तजभ अबत). Without a
dictionary of both languages no rule tells them apart, and a rule that is
wrong silently in either direction is worse than none.

## Unicode to Preeti

Rewritten in 0.8 so that it can be measured. It is still experimental: the
key table is the same unchecked table, and **nobody has looked at any of
these keys in the Preeti font.**

```python
from aksharkit import encode_preeti, unicode_to_preeti

unicode_to_preeti("विद्यार्थी")  # 'ljBfyL{'
result = encode_preeti("दर्ता नं. 245, काठमाडौं-३, Nepal")
result.text  # 'btf{ g+= 245, sf7df8f}+-#, Nepal'
[span.text for span in result.foreign]  # ['245,', 'Nepal']   not Nepali: left alone
result.unmapped_chars  # ('-',)   inside Nepali text, no Preeti key
result.stats  # PreetiEncodeStats(words=3, words_encoded=2, encoded=18, unmapped=1, ...)
result.segments  # every stretch, in order, with its kind: keys, space, foreign, unmapped, ...
```

```console
$ aksharkit convert preeti --to preeti 'नेपाल राम्रो देश हो । दर्ता नं. 245, काठमाडौं-३, Nepal' --quiet --report
g]kfn /fd|f] b]z xf] . btf{ g+= 245, sf7df8f}+-#, Nepal
aksharkit: warning: 1 character(s) had no Preeti key and were left unchanged: - (U+002D)
  line 1, column 46: - (U+002D)
aksharkit: note: 2 stretch(es) with no Devanagari (English words, ASCII numbers) were left as they were; in the Preeti font they would show as other letters. Use --mark-kept to mark them
  line 1, column 33: left alone: 245,
  line 1, column 50: left alone: Nepal
aksharkit: summary: 7 of 8 Nepali word(s) written as keys (87.5%); 35 character(s) written as keys, 1 left with no key, 0 in words that did not read back, 9 not Devanagari and left alone; 0 stretch(es) protected
```

What it promises is narrow and checked: **every word it writes as keys
converts back, with `convert_preeti`, to the normalised form of what went
in.** Each word is converted back before it is accepted; a word that does not
come back the same is left in Unicode and listed in `result.skipped`. A
character with no key in the table is left as it is and listed in
`result.unmapped`. Nothing is guessed.

### How much can be written: the coverage audit

`scripts/preeti_coverage.py` writes 5,300 forms one by one and reads each
back. A form passes only if all of it became keys and the keys read back as
exactly the same text.

```console
$ python scripts/preeti_coverage.py                 # the report, with every failure and why
$ python scripts/preeti_coverage.py --unconfirmed   # also use the single-table keys
$ python scripts/preeti_coverage.py --strict        # leave out the four majority keys
$ python scripts/preeti_coverage.py --check         # the table below is current
```

<!-- coverage:start -->
| Class | Forms | Default | `--unconfirmed` | `--strict` |
| --- | ---: | ---: | ---: | ---: |
| The 33 consonants | 33 | 33 | 33 | 33 |
| Independent vowels, with अं and अः | 13 | 13 | 13 | 13 |
| Devanagari digits | 10 | 10 | 10 | 9 |
| Consonant with a vowel sign | 330 | 330 | 330 | 330 |
| Consonant with ँ ं ः or a halant | 132 | 132 | 132 | 132 |
| Consonant, vowel sign, then ँ or ं | 660 | 660 | 660 | 660 |
| Every two-consonant conjunct | 1089 | 1089 | 1089 | 1089 |
| Every two-consonant conjunct with ि | 1089 | 1089 | 1089 | 1089 |
| Every two-consonant conjunct with a halant | 1089 | 1089 | 1089 | 1089 |
| Longer conjuncts (hand list) | 86 | 86 | 86 | 86 |
| Longer conjuncts with ि, ी, े and ों | 344 | 344 | 344 | 344 |
| Shapes with a key of their own (hand list) | 55 | 55 | 55 | 55 |
| Reph, ra stroke and ऋ forms | 273 | 269 | 269 | 269 |
| Punctuation straight after a word | 35 | 16 | 17 | 16 |
| Punctuation standing alone between words | 35 | 17 | 18 | 17 |
| ॐ, ऽ, borrowed vowels and nukta letters | 17 | 2 | 5 | 2 |
| Forms with a zero-width joiner or non-joiner | 10 | 2 | 2 | 2 |
| **All** | **5300** | **5236** | **5241** | **5235** |
<!-- coverage:end -->

Every consonant, vowel, digit, vowel sign, nasal sign, halant, every one of
the 1,089 two-consonant conjuncts (plain, with ि, and with a halant), the
listed longer conjuncts and every listed reph and ra form can be written.
**That is a statement about this table reading its own output back, not
about what the font draws.**

The 64 forms that cannot be written, and why:

| Form | Why |
| --- | --- |
| र्‍य र्‍ह क्‍ष श्‍च (with a zero-width joiner, U+200D) | The only candidate key, `¥`, is disputed between the tables (र् or र्‍), so it is never written. This is the "eyelash" ra of words like गर्‍यो and भर्‍याङ |
| Forms with a zero-width non-joiner (U+200C) | No key |
| ॠ, ॄ, ऌ, ॢ | No key in any table |
| ऍ, ऑ, ॉ (borrowed vowels) | No key in any table |
| ॅ | Only a single-table key (`‘`): written with `include_unconfirmed=True` |
| ड़ ढ़ | Only a single-table key for the dot (`Þ` after `8` and `9`): written with `include_unconfirmed=True` |
| क़ ख़ ग़ ज़ फ़ य़ | No key: the single-table dot is listed for ड and ढ only |
| `-` `–` `—` `…` `[` `]` `{` `}` `*` `"` `'` `॰` `÷` `&` `#` `@` | No key in the agreed table. In Preeti these keyboard keys draw Nepali letters and marks |
| `’` | The key is disputed |
| `×` | Only a single-table key |
| `:` straight after a letter | The only key for a colon is the visarga key `M`, and after a letter that key reads as ः. After a space, a digit or at the start it is written (see "Rule choices") |

Standing alone between words, a mark with no key is not Nepali text at all
and is simply left as it is, like an English word.

### The word list

`tests/golden/preeti_wordlist.txt` holds 2,639 different everyday Nepali
words (government and form vocabulary, names, places, numbers, dates,
months, weekdays) and `tests/golden/preeti_sentences.txt` holds 62 ordinary
sentences. Both were written by hand for this project and have **not been
reviewed by a native reader**; a few spellings may be non-standard.

- **2,638 of 2,639 words (99.96%)** are written wholly as keys, and every
  one of them reads back exactly. The one left in Unicode is भर्‍याङ (the
  zero-width joiner).
- **61 of 62 sentences** are written wholly as keys and read back exactly.
  The one that is not holds गर्‍यो.

There are **no hand-made Preeti "expected outputs"** in those files. Making
some up would be inventing ground truth. The test checks one property: what
is written reads back the same. It does not show that the keys are the ones
a typist would press or that they look right in the font.

### Worked examples from two other converters

`tests/golden/preeti_crosscheck.tsv` holds 14 Preeti/Unicode pairs shown as
examples on two public converter pages, each labelled with its page:

- https://www.engineeringnepal.com.np/p/preeti-to-unicode.html (6 pairs)
- https://shobfree.com/nepali-preeti-to-unicode-converter (8 pairs)

All 14 convert to the Unicode those pages show, and all 14, converted the
other way, give **the identical key string** those pages show (for example
`;D´f}tf`, `cGt/f{li6«o`, `km"n`). The test would also accept a different
key sequence that reads back the same; it was not needed. These are **worked
examples from other converters, not ground truth and not real documents**:
those pages may descend from the same tables aksharkit compared, so
agreement is weaker evidence than it looks. `tests/golden/preeti_samples.tsv`
stays empty, reserved for text really typed in Preeti.

### English, numbers and punctuation in Nepali text

Only Devanagari is turned into keys. Decided in 0.8:

- **A word with no Devanagari in it is left exactly as it is** and listed in
  `result.foreign`: English words, web and e-mail addresses, ASCII numbers.
  It does not count as a failure and `result.complete` stays true. (0.7
  reported every Latin letter as unmapped.)
- **ASCII digits are never written as keys.** The digit keys of the Preeti
  font draw other things (`2` draws द्द, `5` draws a ligature), so `245`
  typed in Preeti would not show 245. By default the digits stay as they
  are, flagged as foreign. With `digits="devanagari"` (`--digits
  devanagari`) ASCII numbers on lines that hold Devanagari are first
  rewritten in Devanagari digits, which do have keys: `2083` becomes `@)*#`.
  That changes the text: converting back gives २०८३, not 2083.
- **Punctuation that has a key** (`।` `,` `.` `?` `!` `;` `(` `)` `/` `%`
  `+` `=` and the curly quotes) is written as that key when it stands in or
  beside Nepali text.
- **Punctuation with no key** (see the table above) inside a Nepali word is
  left as it is and reported in `result.unmapped`; the letters round it are
  still written. With `whole_words=True` the letters stay in Unicode too
  when the hole is a joiner inside the word.

In plain text the result is one string, so the parts left alone sit among
the keys, and a reader who sets the whole text in Preeti would see them as
wrong letters. Two ways round that:

- `mark_kept=("{{", "}}")` (`--mark-kept '{{' '}}'`) puts markers round
  every stretch that was left as it was. Converting back with
  `markers=("{{", "}}")` then gives the normalised input again:

  ```console
  $ aksharkit convert preeti --to preeti 'दर्ता नं. 245, Nepal' --quiet --mark-kept '{{' '}}'
  btf{ g+= {{245,}} {{Nepal}}
  $ aksharkit convert preeti 'btf{ g+= {{245,}} {{Nepal}}' --quiet --markers '{{' '}}'
  दर्ता नं. 245, Nepal
  ```

- use a Word file, where each part keeps a font of its own (next section).

### Word files: Unicode .docx to Preeti .docx

```python
from aksharkit import encode_docx

report = encode_docx("nibedan.docx", "nibedan-preeti.docx")
report.runs_converted, report.runs_split, report.runs_untouched
[item.text for item in report.left]  # Nepali left in Unicode, with part and paragraph
report.stats.share_words
```

```console
$ aksharkit convert preeti --to preeti --docx nibedan.docx -o nibedan-preeti.docx --report
aksharkit: note: Preeti conversion is experimental — mapping agreed by at least 2 of 3 permissively-licensed table families (4 projects), not yet checked against real Preeti documents or by a native reader
aksharkit: warning: 3 stretch(es) of Nepali text were left in Unicode, in the font they had
  word/document.xml, paragraph 1: : (no key: : (U+003A))
  word/document.xml, paragraph 1: भर्‍याङ (no key: ? (U+200D))
  word/document.xml, paragraph 1: - (no key: - (U+002D))
aksharkit: docx: 2 run(s) written as keys and set to Preeti, 2 mixed run(s) cut into pieces, 3 run(s) left as they were, 2 paragraph(s) changed, 1 word(s) moved whole into their first run; parts read: word/document.xml
aksharkit: summary: 11 of 14 Nepali word(s) written as keys (78.6%); 61 character(s) written as keys, 9 left with no key, 0 in words that did not read back, 18 not Devanagari and left alone
```

(That file was built for the purpose, with awkward cases in it.)

- Every stretch of Devanagari that can be written is replaced by its keys
  in a run whose font is set to **the name** `Preeti` (`--font NAME` for
  another name). No font is added to the file, bundled with this package or
  linked from anywhere: the computer that opens the file must have Preeti.
- Runs with no Devanagari are not touched. A run holding both is cut into
  several runs: keys in Preeti, the rest (English, ASCII numbers, a mark
  with no key) with the properties it had.
- A Nepali word holding a character with no key **stays whole, in Unicode,
  in the font it had**, and is listed in `report.left`.
- A word cut across several runs is written as one and put into its first
  run (`report.boundary_moves` counts these), as in the other direction.
- Bold, italic and size that were set only for complex scripts are copied to
  the ordinary properties, because key codes are plain Latin characters to a
  word processor.
- The same parts are read as in the other direction (body, tables, headers,
  footers, footnotes, endnotes, comments), everything else is copied byte
  for byte, and the input file is never written to.
- Converting the result back with `convert_docx` gives the same text. The
  tests check that, and that the output is well-formed XML; one output was
  also read with python-docx and converted to PDF by LibreOffice without
  error. **It has not been opened in Microsoft Word, and nobody has seen it
  with the Preeti font installed.**

Text files work as in the other direction: `-i FILE -o FILE`, several `-i`
with `--out-dir DIR`, `--force`, line endings kept exactly.

### Single-table keys (off by default)

`include_unconfirmed=True` (`--include-unconfirmed`) also writes the keys
only one table family has: ड़ (`8Þ`), ढ़ (`9Þ`), ॅ (`‘`) and `×`. That
raises the audit from 5,236 to 5,241 forms. Such text reads back only when
the other direction is given the same option, and these keys are the least
attested in the table. The disputed keys are never written.

### Rule choices made in 0.8

Each of these makes more text writable and reads back exactly. Each is a
choice made from the tables and the worked examples, **not from looking at
the font**:

- **्र under round letters.** After ङ छ ट ठ ड ढ the ra stroke is written
  with `«` (ट्रक is `6«s`, राष्ट्र is `/fi6«`), as the cross-check example
  `cGt/f{li6«o` has it; after other letters with `|`. 0.7 wrote `|`
  everywhere.
- **॥** is written as two danda keys, `..`, and two danda keys together are
  read as ॥.
- **A colon** that is not straight after a letter is written with the
  visarga key `M` (`विषय : निवेदन` is `ljifo M lgj]bg`, `१०:३०` is
  `!)M#)`), and that key with no letter before it is read as a colon. One
  table family notes this use; the others are silent. A visarga cannot
  stand without a letter, so nothing well-formed is lost.
- **Where several keys give the same letter**, one is chosen by rule: the
  key more table families agree on, then the shorter, then ASCII before
  other characters. The result is one valid way to type the text, not
  necessarily a typist's way.

## Reports

`convert_preeti(...).as_dict()`, `encode_preeti(...).as_dict()`,
`DocxReport.as_dict()` and `DocxEncodeReport.as_dict()` give plain data, and `--json` prints it:

```console
$ aksharkit convert preeti - --quiet --json < patra.txt
{
  "direction": "preeti-to-unicode",
  "status": "experimental — mapping agreed by at least 2 of 3 ...",
  "complete": false,
  "text": "नेपाल राम्रो देश हो ।\r\n\r\n\tविद्यार्थी ¥ कार्यक्रम\n...",
  "stats": {"agreed": 32, "majority": 1, "unconfirmed": 0, "unmapped": 1, "untouched": 14,
            "protected": 41, "convertible": 34, "share_agreed": 0.9412, "share_majority": 0.0294, ...},
  "unmapped": [{"char": "¥", "codepoint": "U+00A5", "offset": 35, "line": 3, "column": 10, "output_offset": 37}],
  "unmapped_counts": [{"char": "¥", "codepoint": "U+00A5", "count": 1}],
  "protected": [{"start": 45, "end": 70, "text": "https://example.com/a?b=1", "reason": "link", ...}, ...]
}
```

(Shortened here.) Lines and columns count from 1; a column is a character,
not a byte. `output_offset` is the character's place in the result.

**What the shares mean.** `stats` counts input characters: `agreed` were
converted by keys two or more table families agree on, `majority` by the four
keys where another table differs, `unconfirmed` by one-family keys (only with
`include_unconfirmed=True`), `unmapped` were left as they were. White space
and protected text are not counted. A high `agreed` share says the text used
well-attested keys. **It does not say the result is correct**: the table
itself is unchecked.

## The playground

The Preeti tab of the [playground](https://samir-khadka.com.np/aksharkit/)
runs the same code in the browser. From 0.7 it can open a `.txt` or `.docx`
file (up to 2 MB, read on the device and sent nowhere), download the result,
switch direction, and it marks the characters it left alone. Text longer than
20,000 characters is converted when you press Convert rather than as you
type. A file's text is never put in the address or the shareable link. The
page gives the text of a text file with whatever line endings the browser
keeps; use the command line where exact bytes matter.

From 0.8 the Unicode to Preeti direction has the same file open and
download (a `.txt` gives `-preeti.txt`, a `.docx` gives `-preeti.docx`), its
own examples, the single-table keys as an option, whole words that could not
be written highlighted, and a line saying how many Nepali words became keys.
A notice says that the result is key codes which read as Nepali only in the
Preeti font, which the page does not load or supply. The page has no digits
or marker options; use the command line for those.

**Browser checks.** The 0.7.0 Preeti tab was checked once in a desktop
browser on 24 November 2026: both directions, a link kept, an unmapped key
highlighted, and a `.docx` opened and downloaded. A phone is untested. What
0.8 adds has not been opened in any browser; it is covered by tests that
fake the page and run ordinary Python.

## What has and has not been checked

Checked:

- every key in the table against what four published tables say for it
  (`scripts/compare_preeti_sources.py --check` repeats this);
- that the reordering rules do what this page says, on inputs typed by the
  builder from the table;
- that Unicode → Preeti → Unicode gives back the normalised input for every
  word the encoder accepts: 5,300 audited forms, 2,639 hand-written words,
  62 sentences, and generated inputs (see "Unicode to Preeti");
- that 14 example pairs from two other converters' pages agree in both
  directions;
- that a Unicode .docx built by the tests, written as Preeti and converted
  back, has the same text;
- that a .docx built by the tests comes back with only its Preeti runs
  changed and every other part byte for byte the same.

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

- **No Word file made by Microsoft Word has been converted**, and no output
  has been opened in Microsoft Word. No real Preeti text file either.
- **The 0.8 additions to the playground tab have not been opened in a
  browser.** (The 0.7.0 tab was checked once in a desktop browser on
  24 November 2026, including a `.docx` open and download; a phone is
  untested.)
- **The keys written by Unicode → Preeti have never been looked at in the
  Preeti font.** The coverage audit, the word list and the sentences show
  only that this package reads its own output back. A mistake shared by both
  directions would not show.
- The word list and the sentences were written by the builder and not
  reviewed by a native reader.
- The 14 cross-check pairs are other converters' examples, not documents.

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

Added in 0.8, each with tests:

8. **Reph after a half letter.** `{` after a letter that ends in a halant
   (`s\{`) now moves to the front of it (र्क्); 0.7 reported that `{` as
   unmapped.
9. **Two danda keys together** (`..`) are read as ॥; 0.7 gave ।।. With a
   space between them they stay two dandas.
10. **The visarga key with no letter before it** (`M` after a space, a
    digit, punctuation or at the start) is read as a colon: `ljifo M lgj]bg`
    is विषय : निवेदन and `!)M#)` is १०:३०. After a letter or a vowel sign it
    is ः as before (`b'Mv` is दुःख). One table family notes this use of the
    key; no real document has confirmed it.

## What it does not do

- **Other fonts** (Kantipur, Himali, Sagarmatha, PCS Nepali): not supported.
- **Tell Preeti from English.** In plain text an English word is converted as
  if it were Preeti unless you protect it (see "Leaving parts of the text
  alone"). In a .docx the font decides, so English set in another font is
  safe, and English typed *in* the Preeti font is converted.
- **Old `.doc` files, PDF, Excel, PowerPoint, OpenDocument.** Only `.docx`
  and plain text. Save a `.doc` as `.docx` first.
- **Fonts in a .docx that come from a table style**, text in drawings, and
  the other cases marked "No" in the table above.
- **Typing habits it has not seen.** Real typists overstrike, repeat signs,
  and use keys in ways no table lists. Three one-family notes were left out:
  `f‘` for ॉ, `N˜` for ल and `6[` for ट्ट. (A fourth, `M` as a colon where
  no letter stands before it, is used from 0.8.)
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
