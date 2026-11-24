# Preeti and Unicode (tested on real documents)

> **Status: tested on real documents — mapping agreed by at least 2 of 3
> permissively-licensed table families (4 projects) and checked by eye
> against 9 public Preeti documents from 7 publishers (108 keys confirmed,
> 21 never seen); not reviewed by a native reader.**
>
> In those documents 2 of 409,081 key characters have no entry (0.0005%;
> it was 0.2278% in 0.8), and 166 lines read against their page images
> showed no wrongly converted key. The reading was done by the build
> assistant from images, not by a native reader. See
> [Tested on real documents](#tested-on-real-documents).

Preeti is a legacy font: a file typed in it holds Latin letters and symbols
(`g]kfn`) that only look like Nepali (`नेपाल`) while that font is installed.
`aksharkit.legacy` turns such text into Unicode, and Unicode back into Preeti
keys. Version 0.7 added Word (.docx) files, text files, protected stretches,
the other direction and fuller reports. Version 0.8 works on the other
direction, Unicode to Preeti: a coverage audit, better encoding rules, a
hand-written word list, Word files and a clearer playground. Version 0.9
is the first to meet real documents: it settled four keys the tables left
open, added the habits of real typists, and changed the status from
"experimental" to the one above.

```python
from aksharkit import convert_preeti, preeti_to_unicode

preeti_to_unicode("g]kfn")  # 'नेपाल'

result = convert_preeti("sfo{qmd °")
result.text  # 'कार्यक्रम °'
result.unmapped  # (UnmappedChar(char='°', offset=8),)  also .line, .column, .output_offset
result.complete  # False
result.stats  # PreetiStats(agreed=7, majority=0, unconfirmed=0, unmapped=1, untouched=1, protected=0)
```

```console
$ aksharkit convert preeti 'd]/f] gfd ;ld/ xf] .' --quiet
मेरो नाम समिर हो ।
$ aksharkit convert preeti -i patra.txt -o patra-unicode.txt --report
aksharkit: note: Preeti conversion is tested on real documents — mapping agreed by at least 2 of 3 permissively-licensed table families (4 projects) and checked by eye against 9 public Preeti documents from 7 publishers (108 keys confirmed, 21 never seen); not reviewed by a native reader
aksharkit: warning: 1 character(s) had no agreed Preeti entry and were left unchanged: ° (U+00B0)
  line 3, column 10: ° (U+00B0)
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
report.unmapped  # (DocxUnmapped(part='word/document.xml', paragraph=2, char='°'), ...)
report.stats.share("agreed")  # 0.959...
```

```console
$ aksharkit convert preeti --docx suchana.docx -o suchana-unicode.docx --report
aksharkit: warning: 2 character(s) had no agreed Preeti entry and were left unchanged: ° (U+00B0) Ý (U+00DD)
  word/document.xml, paragraph 2: ° (U+00B0)
  word/document.xml, paragraph 2: Ý (U+00DD)
aksharkit: docx: 11 run(s) converted and set to Kalimati, 6 run(s) in other fonts left as they were, 7 paragraph(s) changed, 0 run boundary move(s); parts read: word/document.xml, word/header1.xml, word/footer1.xml, word/footnotes.xml
aksharkit: docx: fonts found on text runs: Calibri (6), Preeti (11)
aksharkit: summary: 74 character(s) to convert: 71 by agreed keys (95.9%), 1 by majority keys (1.4%), 2 left unchanged (2.7%)
```

(The status notice line is left out above. The document in this
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

Rewritten in 0.8 so that it can be measured. From 0.9 the table it reads
backwards has been checked against real documents, and the keys written for
a small sample (17 lines) were drawn in the Preeti outlines found in those
documents and read by eye. **Your own output has not been looked at in the
Preeti font by anyone**, and nothing was opened in Word.

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
| Reph, ra stroke and ऋ forms | 273 | 271 | 271 | 269 |
| Punctuation straight after a word | 35 | 19 | 20 | 16 |
| Punctuation standing alone between words | 35 | 20 | 21 | 17 |
| ॐ, ऽ, borrowed vowels and nukta letters | 17 | 2 | 5 | 2 |
| Forms with a zero-width joiner or non-joiner | 10 | 4 | 4 | 2 |
| **All** | **5300** | **5246** | **5251** | **5235** |
<!-- coverage:end -->

Every consonant, vowel, digit, vowel sign, nasal sign, halant, every one of
the 1,089 two-consonant conjuncts (plain, with ि, and with a halant), the
listed longer conjuncts and every listed reph and ra form can be written.
**That is a statement about this table reading its own output back, not
about what the font draws.** From 0.9 the eyelash ra, both dashes and the
curly single quotation marks can be written, which is the rise from 5,236.

The 54 forms that cannot be written, and why:

| Form | Why |
| --- | --- |
| क्‍ष श्‍च (a zero-width joiner, U+200D, after a letter other than र) | No key. The eyelash ra of गर्‍यो and भर्‍याङ is written with `¥` from 0.9 |
| Forms with a zero-width non-joiner (U+200C) | No key |
| ॠ, ॄ, ऌ, ॢ | No key in any table |
| ऍ, ऑ, ॉ (borrowed vowels) | No key in any table |
| ॅ | Only a single-table key (`‘`): written with `include_unconfirmed=True` |
| ड़ ढ़ | Only a single-table key for the dot (`Þ` after `8` and `9`): written with `include_unconfirmed=True` |
| क़ ख़ ग़ ज़ फ़ य़ | No key: the single-table dot is listed for ड and ढ only |
| `-` `…` `[` `]` `{` `}` `*` `"` `'` `॰` `÷` `&` `#` `@` | No key in the agreed table. In Preeti these keyboard keys draw Nepali letters and marks. Typists use the short dash `–` where Unicode text has a hyphen; aksharkit does not swap one for the other, because that would not read back |
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

- **2,639 of 2,639 words** are written wholly as keys, and every one of
  them reads back exactly. (2,638 in 0.8: भर्‍याङ needed the `¥` key.)
- **62 of 62 sentences** are written wholly as keys and read back exactly.
  (61 in 0.8: one holds गर्‍यो.)

There are **no hand-made Preeti "expected outputs"** in those files. Making
some up would be inventing ground truth. The test checks one property: what
is written reads back the same. It does not show that the keys are the ones
a typist would press or that they look right in the font.

### Worked examples from two other converters

`tests/golden/preeti_crosscheck.tsv` holds 14 Preeti/Unicode pairs shown as
examples on two public converter pages, each labelled with its page:

- https://www.engineeringnepal.com.np/p/preeti-to-unicode.html (6 pairs)
- https://shobfree.com/nepali-preeti-to-unicode-converter (8 pairs)

All 14 convert to the Unicode those pages show, and 13 of the 14, converted
the other way, give **the identical key string** those pages show (for
example `cGt/f{li6«o`, `km"n`). The fourteenth differs by choice since 0.9:
झ is written `em`, as typists do (312 times against once for the key `´`
in the real documents), where the page shows `;D´f}tf`; it reads back the
same. These are **worked
examples from other converters, not ground truth and not real documents**:
those pages may descend from the same tables aksharkit compared, so
agreement is weaker evidence than it looks. Text really typed in Preeti is
in `tests/golden/preeti_samples.tsv` (from 0.9).

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
aksharkit: note: Preeti conversion is tested on real documents — mapping agreed by at least 2 of 3 permissively-licensed table families (4 projects) and checked by eye against 9 public Preeti documents from 7 publishers (108 keys confirmed, 21 never seen); not reviewed by a native reader
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
  with the Preeti font installed.** The real documents of 0.9 were PDFs, so
  they say nothing about Word files.

Text files work as in the other direction: `-i FILE -o FILE`, several `-i`
with `--out-dir DIR`, `--force`, line endings kept exactly.

### Single-table keys (off by default)

`include_unconfirmed=True` (`--include-unconfirmed`) also writes the keys
only one table family has: ड़ (`8Þ`), ढ़ (`9Þ`), ॅ (`‘`) and `×`. That
raises the audit from 5,246 to 5,251 forms. Such text reads back only when
the other direction is given the same option, and these keys are the least
attested in the table: none of them occurs in the real documents. The
disputed keys are never written.

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

Changed in 0.9, from the real documents:

- **Keys confirmed in documents come first.** Where several keys give the
  same letter, one that was confirmed by sight is preferred to one that was
  not; then the rule above. So झ is written `em` (confirmed, and what
  typists press) and no longer `´`.
- **A conjunct whose only key was never seen in a document is spelt out**
  with keys that were: हृ as `x[` (not `Å`), झ् as `em\` (not `‰`), द्म as
  `b\d`, ध्र as `w|`, ङ्ख as `ª\v`. Reading is unchanged: the never-seen
  keys still convert.
- **The eyelash ra** (र् + zero-width joiner) is written `¥`; ‘ and ’ are
  written `…` and `Ú`; – and — with their own keys.
- **Two ra strokes on one letter** are written as halant and letter, since
  the same stroke key twice now reads as once.

## Reports

`convert_preeti(...).as_dict()`, `encode_preeti(...).as_dict()`,
`DocxReport.as_dict()` and `DocxEncodeReport.as_dict()` give plain data, and `--json` prints it:

```console
$ aksharkit convert preeti - --quiet --json < patra.txt
{
  "direction": "preeti-to-unicode",
  "status": "tested on real documents — mapping agreed by at least 2 of 3 ...",
  "complete": false,
  "text": "नेपाल राम्रो देश हो ।\r\n\r\n\tविद्यार्थी ° कार्यक्रम\n...",
  "stats": {"agreed": 32, "majority": 1, "unconfirmed": 0, "unmapped": 1, "untouched": 14,
            "protected": 41, "convertible": 34, "share_agreed": 0.9412, "share_majority": 0.0294, ...},
  "unmapped": [{"char": "°", "codepoint": "U+00B0", "offset": 35, "line": 3, "column": 10, "output_offset": 37}],
  "unmapped_counts": [{"char": "°", "codepoint": "U+00B0", "count": 1}],
  "protected": [{"start": 45, "end": 70, "text": "https://example.com/a?b=1", "reason": "link", ...}, ...]
}
```

(Shortened here.) Lines and columns count from 1; a column is a character,
not a byte. `output_offset` is the character's place in the result.

**What the shares mean.** `stats` counts input characters: `agreed` were
converted by keys two or more table families agree on (the keys settled by
documents and a sign typed twice are counted here too), `majority` by the four
keys where another table differs, `unconfirmed` by one-family keys (only with
`include_unconfirmed=True`), `unmapped` were left as they were. White space
and protected text are not counted. A high `agreed` share says the text used
well-attested keys. **It does not say the result is correct**: it says
nothing about a typing slip in the source or a key used in an unusual way.

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
highlighted, and a `.docx` opened and downloaded. 0.8.0 was deployed on
24 November 2026 and its Unicode to Preeti direction was checked once in a
desktop browser that day: typed text, the examples, copy, a text download
and a deep link. Opening a `.docx` in that direction was not checked live,
and a phone is untested. **What 0.9 changes on the page (the status notice,
the badge, the wording of two notes) has not been opened in any browser**;
it is covered by tests that fake the page and run ordinary Python.

## What has and has not been checked

Checked:

- every key in the table against what four published tables say for it
  (`scripts/compare_preeti_sources.py --check` repeats this);
- that the reordering rules do what this page says, on inputs typed by the
  builder from the table;
- from 0.9, the table and the rules against nine real documents: what every
  key present draws, 166 lines read against their page images, and the
  count of characters with no entry (see "Tested on real documents");
- from 0.9, 26 real excerpts in both directions;
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

- **No native reader has looked at the table or the output.** The reading
  against real documents was done by the build assistant from images.
- **21 keys were never seen** in a document and 11 more in fewer than three
  publishers' documents; their entries rest on the tables alone. So do the
  three keys still disputed (`°` `Ì` `Ý`), which are not used, and the dot
  key for ड़ and ढ़.
- **Only 166 lines were read by eye**, out of about 10,800. The rest were
  only counted. A wrong letter in a rare combination could be there unseen.
- **Nine documents, all PDFs, all from public bodies or a university.** No
  newspaper, book, letter or form typed by a private person; no other
  version of the Preeti font was knowingly included (every document's
  outlines were the same).
- Text taken out of a PDF is not the typist's file: spaces and line breaks
  are the PDF's, so rules about spacing were not tested on real typing.
- Whether the four tables are truly independent of each other, or of older
  tables under licences this project cannot use, is not known (see
  "How independent are the sources?").

- **No Word file made by Microsoft Word has been converted**, and no output
  has been opened in Microsoft Word. No real Preeti text file either.
- **The 0.9 changes to the playground tab have not been opened in a
  browser.** (0.8.0 was checked once in a desktop browser on 24 November
  2026 in the Unicode to Preeti direction; a `.docx` in that direction and a
  phone are untested.)
- **The keys written by Unicode → Preeti were looked at in the Preeti
  outlines for 17 lines only**, and never in Word with the font installed.
  The coverage audit, the word list and the sentences show only that this
  package reads its own output back.
- The word list and the sentences were written by the builder and not
  reviewed by a native reader.
- The 14 cross-check pairs are other converters' examples, not documents.

Real samples go in `tests/golden/preeti_samples.tsv`. The file explains the
format; each line added becomes a test.

## Tested on real documents

Added in 0.9, on 24 November 2026. Until then no real Preeti document had
been converted and nobody had looked at what the keys draw.

### The documents

Nine public PDFs from seven publishers that embed a font named Preeti
(`pdffonts` prints the name shown). None is kept in this repository, and no
font is: the script below reads them from a folder you name.

| Publisher | Kind | Pages | Font as embedded | Address |
| --- | --- | --- | --- | --- |
| National Examinations Board, Biratnagar office | notice with lists | 120 | `ABCDEE+Preeti` | https://biratnagar.neb.gov.np/download-file/downloads/Downloads-202603251316403780.pdf |
| Nepal Rastra Bank | NRB Samachar newsletter, Asoj 2077 | 8 | `KPEKMH+Preeti` | https://www.nrb.org.np/contents/uploads/2020/10/NRB-Samachar_Asoj20770630.pdf |
| Public Service Commission | syllabus, 2023 | 14 | `ABCDEE+Preeti` | https://psc.gov.np/site_uploads/course/2023020811053563e381ff3153b.pdf |
| Public Service Commission | syllabus, 2024 | 7 | `ABCDEE+Preeti` | https://psc.gov.np/site_uploads/course/2024030801020565eb0c4dda255.pdf |
| Public Service Commission | syllabus, 2025 | 4 | `ABCDEE+Preeti` | https://psc.gov.np/site_uploads/course/202506300438476862bd97a96a2.pdf |
| Teacher Service Commission | candidate list, 2074 BS | 20 | `ABCDEE+Preeti` | https://giwmscdnone.gov.np/media/pdf_upload/6.Paschim203_revised1_pbxfevn.pdf |
| Tribhuvan University Central Library | MA thesis in the eLibrary | 187 | `ABCDEE+Preeti` | https://elibrary.tucl.edu.np/JQ99OgQIizUxyjI9nB0on9OyLkqsGIf4/api/core/bitstreams/d827f999-b255-4cf9-99cb-68e79ad340d9/content |
| Supreme Court of Nepal | Bulletin, 2065 BS | 31 | `FGPCAM+Preeti` | https://supremecourt.gov.np/publication/materials/101817.pdf |
| Nepal Electricity Authority | proactive disclosure, Magh-Chait 2080 | 122 | `ABCDEE+Preeti` | https://nea.org.np/uploads/shares/news_notice/32453821.pdf |

All nine mix Preeti with other fonts (English in Times or Arial, numbers,
headings). **Only text set in the font named Preeti was taken**: `pdftohtml
-xml` gives every piece of text with its font, and pieces in other fonts
were dropped before lines were put together. A line that also held text in
another font was used without that text.

### What was measured

| | Before (0.8) | After (0.9) |
| --- | --- | --- |
| Key characters in Preeti text (spaces not counted) | 409,081 | 409,081 |
| Words | 75,928 | 75,928 |
| Key characters with no entry, left as they were | 932 (0.2278%) | 2 (0.0005%) |

The 932 were `–` (558), `Ú` (292), `¥` (51), `—` (19), an `m` stroke with no
letter to complete (10) and a reph with nothing to sit on (2). The two left
are typing slips in the documents: an `m` typed after a vowel sign that
belongs to another letter, and a reph typed after a closing quotation mark.

`scripts/preeti_corpus.py FOLDER` recounts this from a folder of PDFs
(`--json`, `--strict`; the folder can also be named in
`AKSHARKIT_PREETI_PDFS`). It needs `pdftohtml` from poppler, and it says
"skipped" and exits 0 when the folder, the tool or the Preeti text is
missing, so it is safe where there are no PDFs. Its line count differs a
little from run to run of the method (it groups pieces into lines by
position); the character and word counts do not.

**A low "no entry" rate is not a correctness rate.** A key converted to the
wrong letter would not show in it. That is what reading by eye was for.

### What was read by eye

1. **Every key's outline.** The font programs embedded in the nine PDFs were
   opened with fontTools and each key present was drawn large beside the
   table's entry for it. Every key has the same outline in every document.
   119 different keys occur in the text.
2. **166 lines** across all nine documents, the page image (drawn by
   `pdftoppm` from the PDF, so with the real Preeti glyphs) above the
   converted text set in Noto Sans Devanagari. Some sampled lines are
   repeated table headings, so the number of different lines is lower.
3. **Unicode → Preeti**, on a small sample: the keys written for 17 lines
   (the 11 real excerpts that are not written with the typist's own keys,
   and six made-up lines of conjuncts and marks) were drawn with the
   embedded Preeti outlines and read against the Unicode; all 17 read the
   same. The 15 excerpts that come out as the typist's own keys are on the
   page already. Keys that no document contains cannot be drawn this way.

Result of the 166 lines:

- **No key was found converted to a wrong letter**, before or after.
- Before the fixes, 20 lines showed a difference: a key reported as having
  no entry (`¥`, `Ú`, the two dashes) or a typing habit the converter did
  not follow (below).
- The fixes changed the output of **12 of the 166** lines. Those 12, and 11
  more lines chosen to show each fixed pattern, were read again and match
  the page. The other 154 lines convert exactly as before and were not
  re-read.
- After the fixes no difference is known in the 166 lines. That is 0 found,
  not a proof of 0: see "Who read it".

**Who read it.** The reading was done by the AI assistant that built this
release, from rendered images, **not by a native reader** and not by a
person. It can tell जात from जाति and see a missing reph; it is less
trustworthy on fine distinctions (a short and a long dash, ब against व in
small print, spelling). Preeti draws the visarga and the colon with one
key, so sight cannot tell which was meant.

### Verdict on each key

| Verdict | Keys |
| --- | --- |
| Confirmed: outline read by eye and used in documents from at least 3 publishers | 108 |
| Seen, but in fewer than 3 publishers' documents | 11: `<` ``` `¢` `£` `´` `¶` `Ø` `Û` `•` `‹` `›` |
| Never seen in any of the documents | 21: `¡` `¤` `©` `°` `±` `»` `Å` `Ì` `Î` `Ò` `Ö` `×` `Ù` `Ü` `Ý` `ß` `ç` `˜` `‘` `„` `‰` |
| Contradicted by what the font draws | 0 |

The three majority keys that occur (`B` `^` `¿`) are among the confirmed:
the documents side with the majority each time. They still switch off with
`strict`, which means "the tables alone". The never-seen keys keep their
table entries, unconfirmed by sight; the key for the dot of ड़ and ढ़ (`Þ`)
is one of them, so those two letters stay behind `include_unconfirmed`.

### Keys the documents settled

Documents may only settle a key the tables left open (disputed or absent),
never overrule them, and only with evidence from three publishers. These
are used by default and left out with `strict`:

| Key | Reads as | Why | Seen in |
| --- | --- | --- | --- |
| `¥` | र् + zero-width joiner (the "eyelash" ra of गर्‍यो) | The tables disagreed (र् or र्‍). The font draws the eyelash form | `u¥of]` गर्‍यो (Nepal Rastra Bank, page 8); `k'¥ofpg` पुर्‍याउन (Public Service Commission, page 2); `8f]¥ofpg]` डोर्‍याउने (Nepal Electricity Authority, page 7); `k'¥ofpg` पुर्‍याउन (Tribhuvan University Central Library, page 153) |
| `Ú` | ’ | The tables disagreed (’ or :). The font draws a closing single quotation mark, the partner of `…` | `…sÚ` ‘क’ (Nepal Rastra Bank, page 1); `…;'hfgfÚ` ‘सुजाना’ (Supreme Court of Nepal, page 18); `…clGtd sljtfÚ` ‘अन्तिम कविता’ (Tribhuvan University Central Library, page 25) |
| `–` | – | No table had it. The font draws a short dash, which typists use for the hyphen | `hft–hflt` जात–जाति (Supreme Court of Nepal, page 10); `sfo{–1fg` कार्य–ज्ञान (Public Service Commission, page 1); `sf]le8–!(` कोभिड–१९ (Nepal Rastra Bank, page 1); `@)^%–@)^&` २०६५–२०६७ (Tribhuvan University Central Library, page 1) |
| `—` | — | No table had it. The font draws a longer dash | `d'2fM—` मुद्दाः— (Supreme Court of Nepal, page 8); `k"0ff{Í M— #)` पूर्णाङ्क :— ३० (Public Service Commission, page 1); `j'6jn—jb{3f6` बुटवल—बर्दघाट (Nepal Electricity Authority, page 91) |
| `t` + `m` | क्त | The tables list `Q` + `m`. Typists also put the stroke on `t`, and the font draws the same क्त | `ztmL` शक्ति (typed with long i) (Nepal Electricity Authority, page 24); `;+o'tm` संयुक्त (Supreme Court of Nepal, page 18); `kª\ltm` पङ्क्ति (Tribhuvan University Central Library, page 143) |

### Typing habits the documents showed

Each of these was seen on the page, where the print is unambiguous, and is
now followed (rule numbers are in "Reordering rules"). The first is in
eight of the nine documents (138 times) and the ra stroke habit in four
(15 times); the other four were each found in one document only (4, 17, 1
and 5 times), so they are less well supported than the keys:

- a sign the font draws with no width (`]` `}` `'` `"` `[` `F` `+` `\` `|`
  `«`) or the reph `{` typed twice prints once, and is converted once;
- such a sign typed after a comma (`atfcf,]`) belongs to the letter before
  the comma;
- the ra stroke typed after the vowel sign (`pk]|tL` उप्रेती, `6]«g` ट्रेन);
- the short i typed between a letter and its halant (`kªl\Qm` पङ्क्ति);
- the `m` stroke typed after the halant (`a'e\mg` बुझ्न);
- the reph typed between a half form and its bar (`jfli{fs` वार्षिक).

**Not converter mistakes, and left alone:** typing slips that print wrongly
on the page too (a vowel sign on a space, two different vowel signs on one
letter, `£` typed for `#` in a telephone number) convert to what the page
shows; a heading spaced out letter by letter converts letter by letter.
Things that come from taking text out of a PDF and not from Preeti (line
breaks inside a sentence, columns of a table run together, spaces lost or
doubled) were not counted as errors of either kind.

### Real excerpts as tests

`tests/golden/preeti_samples.tsv` holds 26 short excerpts from eight of the
documents, each with its publisher, address and page, and beside each the
Unicode **the page visibly prints**. All 26 convert to exactly that. All 26,
written back as keys, read back exactly; 15 come out as the very keys the
typist pressed, and the other 11 differ only in habits (which of two keys
for the same shape, a doubled sign). The Unicode was written down by the
build assistant from the comparison above, not by a native reader.

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
| `disputed` — no two families agree, and no document settles it | 3 | Never |
| `settled` — left open by the tables, settled by real documents (0.9) | 4 | By default; not with `strict` |
| `settled_sequences` — the same, for a two-key combination | 1 | By default; not with `strict` |
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

`¥` and `Ú` were here until 0.9; real documents settled them (see "Keys the
documents settled"). The three below occur in none of the documents.

| Key | Values |
| --- | --- |
| `°` | nepali-keyboard ड्ढ; nepalikit ङ्ढ; preeti-unicode-converter ्र |
| `Ì` | nepali-keyboard त्र; nepalikit न्न |
| `Ý` | nepali-keyboard ट्ठ; nepalikit ट्ट् |


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
    key. The real documents of 0.9 use the key this way often (`M–` and
    `M—` after a heading); the font draws one shape for both.

Added in 0.9, each seen in the real documents and each with tests:

11. **A sign with no width typed twice** (`]` `}` `'` `"` `[` `F` `+` `\`
    `|` `«`, and the reph `{`) is converted once: `sf]]` is को.
12. **A sign typed after a comma** (`]` `}` `F` `+`) moves before it when a
    letter stands before the comma: `atfcf,]` is बताओ,.
13. **The ra stroke typed after vowel signs** moves in front of them: `k]|`
    is प्रे, `6]«` is ट्रे.
14. **Short i typed between a letter and its halant** belongs after the
    whole cluster: `ªl\Qm` is ङ्क्ति.
15. **The `m` stroke reaches back across a halant**: `e\m` is झ्.
16. **Reph typed between a half form and its bar**: `i{f` is र्ष.
17. **`t` + `m`** is क्त, like `Q` + `m`.

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
  and use keys in ways no table lists; 0.9 follows the ones the nine
  documents showed and no others. Three one-family notes were left out:
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
