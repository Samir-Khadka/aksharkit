# Known issues and limits

## Not implemented

- **Legacy fonts other than Preeti** (Kantipur, Himali, Sagarmatha, …).
- **Old `.doc` files, PDF, spreadsheets, presentations, OpenDocument.** The
  Preeti converter reads plain text and `.docx` only.
- **Telling Preeti from English without help.** There is no automatic
  "skip English words" option: see `docs/preeti.md` for why.

## Preeti and Unicode (experimental, added in 0.6, extended in 0.7 and 0.8)

- **The key table has not been checked against any real Preeti document, and
  no native reader has reviewed it or its output.** It holds what the Preeti
  tables of four MIT-licensed projects (three families) agree on. Nobody
  opened the font to see what each key draws. A mistake shared by those
  tables is a mistake here.
- **Every Preeti sample in the tests was typed by the builder from the table
  itself.** They show self-consistency only. `tests/golden/preeti_samples.tsv`
  is empty and waiting for real text.
- **Where the four tables came from is unknown.** None says, and their
  authors have not been asked. Two of the four share one rule list and are
  counted once. For 16 keys (`¢ ± ´ Å Ö Ø Û Ü ß ç ˜ „ • … ‹ ›`) the only two
  tables that have the key are nepalikit and nepali-keyboard, whose keys
  overlap almost entirely, so that agreement is weak. See `docs/preeti.md`.
- Four keys (`B` द्य, `^` ६, `¡` ज्ञ्, `¿` रू) are used although one table
  gives something else. `strict=True` / `--strict` leaves them out.
- Five keys with no agreement (`¥ ° Ì Ú Ý`) are never converted, and five
  more that only one family has (`¤ © Ò × ‘`) are off by default. They are
  left as they are and reported.
- It cannot tell Preeti from English: in plain text an English word is
  converted as if it were Preeti unless it is protected with `--keep`,
  `--keep-word` or markers. Only web and e-mail addresses are left alone
  automatically, and that rule has a known wrong answer: Preeti text shaped
  like an e-mail address (`s@v.ug`) is left unconverted.
- **Word files (0.7): only files built by the tests have been converted.**
  No .docx written by Microsoft Word has been tried and no output has been
  opened in Microsoft Word (python-docx and LibreOffice opened the output of
  one test document on the build machine). Fonts that come from a table
  style, text in drawings and text boxes (DrawingML), and list numbers are
  not handled; a run with Preeti in only one of its two Latin font slots is
  left alone and counted. `docs/preeti.md` has the full table.
- **The font named on converted Word text (Kalimati by default) is only a
  name.** No font is supplied or checked for; a computer without it shows a
  substitute.
- Where a word is cut across runs of a Word file and no cut gives the right
  text, the stretch is put into its first run, so some letters take that
  run's formatting. The text itself is right; `report.groups_merged` counts
  these.
- **Unicode → Preeti is checked only against this package's own table**,
  by converting every word back. Nobody has looked at its output in the
  Preeti font, and where several keys give one letter the key is chosen by
  rule, not by typists' habit. The 0.8 numbers (5,236 of 5,300 audited
  forms, 2,638 of 2,639 hand-written words, 61 of 62 sentences) measure
  that self-consistency and nothing more. The word list and sentences were
  written by the builder and not reviewed by a native reader.
- **What Unicode → Preeti cannot write** (left in Unicode and reported):
  the hyphen `-`, dashes, `…`, straight quotes, `[ ] { }`, `*`, `&`, `#`,
  `@`, `÷`, `॰`; a colon straight after a letter; forms with a zero-width
  joiner or non-joiner (गर्‍यो, भर्‍याङ); nukta letters (ड़ and ढ़ only
  with the single-table option); ॉ ऍ ऑ ॠ ॄ ऌ ॢ; ॅ and `×` only with the
  single-table option. The hyphen matters most in practice: dates such as
  २०८३-०१-१५ and names such as काठमाडौं-३ keep a Unicode hyphen.
- **Three 0.8 rule choices have not been seen in the font**: `«` for ्र
  under ङ छ ट ठ ड ढ, `..` for ॥, and the visarga key `M` for a colon that
  does not follow a letter. They agree with the tables and with the 14
  worked examples, which is not the same as being right.
- **English and ASCII numbers are left as they are** in Unicode → Preeti.
  In plain text they then sit among the keys, and set in the Preeti font
  they show as other letters; `--mark-kept` marks them, a Word file gives
  them their own runs. `--digits devanagari` changes the text (2083 becomes
  २०८३).
- **A Unicode .docx turned into Preeti (0.8)** was tried only on files
  built by the tests. One output was read with python-docx and converted to
  PDF by LibreOffice without error. It was never opened in Microsoft Word,
  and never seen with the Preeti font installed. A run that is cut leaves
  an empty run behind in some cases; that is valid, but untidy.
- **Changed in 0.8:** `M` with no letter before it now reads as a colon
  (0.7: ः), `..` reads as ॥ (0.7: ।।), and a reph key after a half letter
  is placed (0.7: reported). Unicode → Preeti reports English as `foreign`,
  not `unmapped`; writes `«` where 0.7 wrote `|` after ङ छ ट ठ ड ढ; and
  writes ॥ and some colons that 0.7 reported. `--include-unconfirmed` with
  `--to preeti` is now an option, not an error, and `--to preeti` accepts
  `--docx`.
- The share of characters "converted by agreed keys" in a report says how
  well-attested the keys used were. It is not a measure of correctness.
- **Changed in 0.7:** a character with no agreed letter is now copied
  through exactly; 0.6 passed it through Unicode normalisation with the rest.
  `--report` prints a line and column instead of a position, and adds a
  summary line.
- The reordering rules (short i, reph, the `m` stroke, half forms) were
  written from how Devanagari is stored, and have not been tried on real
  typing. Overstrikes, repeated signs and unusual key orders may come out
  wrong without any warning, because every key in them is a known key.
- A stray `m` or `{` with no letter to attach to is reported as unmapped.

## Browser playground

- **Version 0.3.0 was checked once, on one desktop browser** (24 November
  2026, deployed page): it loaded, reported aksharkit 0.3.0 on Python 3.13.2,
  and every tab gave the expected output. The browser console was not
  inspected.
- **Version 0.4.0 was checked once, on one desktop browser** (24 November
  2026, deployed page): the new tabs, the copy buttons, the examples and a
  shared link reopened after a reload all worked. Earlier the same day the
  built page had been loaded in headless Chromium at 360px and 1280px wide
  with Pyodide replaced by a stub. **It has not been tried on a real phone**;
  touch behaviour, other browsers, the error state and screen readers are
  untested too.
- **Version 0.5.0 was checked once, in one desktop browser, on 24 November
  2026.** The Aksharas and Sort tabs, the ordinal and date-pattern rows and
  the address fix below all behaved as expected there. Nothing narrower than
  a desktop window was looked at.
- The address fix in 0.5 (an edit still waiting to run no longer puts the
  previous tab back in the address after a tab click) was worked out from
  the code and reproduced in the Node tests. It has not been confirmed in
  the browser where the stale address was seen.
- Copy needs the browser's clipboard API, which works only on HTTPS or
  localhost; without it the button says "Copy is not available".
- A shared link holds the inputs in the address after `#`. Inputs that would
  make the address longer than about 1,800 characters are left out of it.
  Anyone who receives the link can read what was typed.
- It needs JavaScript, WebAssembly and a connection to `cdn.jsdelivr.net`.
  The first visit downloads roughly 5 MB (Pyodide 0.29.5); there is no
  offline mode.
- Pyodide 0.29.5 runs Python 3.13.2. The package is tested on CPython
  3.10–3.13, not inside Pyodide.
- `pyodide.js` is loaded with a Subresource Integrity hash; the files it
  then fetches (`pyodide.asm.js`, `pyodide.asm.wasm`, `python_stdlib.zip`)
  are not hash-checked by the page. There is no Content-Security-Policy.
- The "Today" button and `today_bs()` stop working after 13 April 2027,
  when the calendar table ends.
- **The 0.6 Preeti tab was checked once, in one desktop browser, on
  24 November 2026** (five words, two unmapped characters reported, copy,
  examples and a shared link). Phone untested. Its input box uses the
  system's monospace font; the page does not load the Preeti font, so pasted
  Preeti text looks like Latin letters.
- **The 0.7.0 Preeti tab was checked once, in one desktop browser, on
  24 November 2026**: both directions, a link kept, an unmapped key
  highlighted, and a `.docx` opened and downloaded (so Python's `zipfile`
  and `xml.parsers.expat` do work inside Pyodide 0.29.5). Phone untested.
- **What 0.8 adds to the Preeti tab has not been opened in any browser**:
  Unicode → Preeti for `.txt` and `.docx` files, its examples, the notice
  about the Preeti font, whole-word highlighting and the coverage line. It
  is covered by Node tests that fake the page and run ordinary Python. 0.8
  was deployed on 24 November 2026; this direction has not yet been opened in a browser.
- The conversion runs on the page's own thread. Text over 20,000 characters
  waits for the Convert button, and the page does not respond while it works.
  How long that takes in a browser was not measured. Files over 2 MB are
  refused by the page; use the command line for those.
- A text file opened in the page goes through the browser's text box, which
  may change `\r\n` line endings to `\n`. The command line keeps bytes exactly.
- More than 400 characters left unconverted are listed but not highlighted.

## Transliteration

- **`simple` is approximate in both directions.** Devanagari → `simple`
  merges long and short vowels, dental and retroflex stops, and श/ष. It
  keeps the inherent `a` in the middle of words (सरकार → `sarakar`) and does
  not reproduce customary spellings (काठमाडौँ → `kathamadaun`, विराटनगर →
  `viratnagar`). व is always `v`, or `w` after a consonant.
- **`simple` → Devanagari is a guess.** `a` is always अ, `i`/`u` always
  short, `t`/`d`/`n` always dental, `sh` always श; no halant is added at the
  end of a word; anusvara, candrabindu and visarga are never produced. Only
  32 of the 109 test words survive a `simple` round trip.
- The rules for dropping the final `a` are hand-written and unreviewed; 37
  test spellings are marked for native-speaker review.
- `iast` departs from ISO 15919 for ड़/ढ़ (`ṙ`/`ṙh`) and ख़ (`x`) to stay
  reversible. The round trip needs input without Latin letters, ASCII
  digits (or `digits=False`), `|`, a doubled single danda, or an apostrophe
  directly after a Devanagari letter.
- Devanagari characters outside the table (ऑ, ऍ, ॅ, ॉ, ऌ, ऩ, ऱ, ॰) are passed
  through unchanged in both schemes.
- No other schemes (ITRANS, Harvard-Kyoto) and no dictionary of names.

## Dates (BS ↔ AD)

- **Range:** BS 2000-01-01 to 2083-12-30 only (14 April 1943 to 13 April 2027).
  Anything else raises `DateRangeError`. The range **ends in April 2027**:
  the published tables disagree from BS 2084 onwards, so those years were
  left out. A later release must extend it once the 2084 calendar is settled.
- **Disputed month:** 31 Baishakh to 32 Jestha 2062 (14 May to 14 June 2005)
  raises `DisputedDateError` unless `allow_disputed=True` is passed. Four of
  the five tables say Baishakh 30 / Jestha 32, one says 31 / 31, and outside
  evidence is split. With the flag, the majority reading is used and may be
  one day off.
- **No official source.** The table rests on five open-source projects'
  published tables agreeing, plus eight date pairs from other pages. No
  government or calendar-committee table was checked. Four of the five
  projects are published separately, but they may share a common origin.
- **Month and weekday names** were written from general knowledge and have not
  been reviewed by a native speaker. Only one spelling of each is offered.
- `parse_bs` reads numeric dates (`2083-08-07`, `२०८३/८/७`) and, from 0.5,
  `year month day` or `day month year` with a month name (`२०८३ मंसिर ८`,
  `8 Mangsir 2083`). It knows only the one spelling of each month that the
  package writes: `जेष्ठ`, `मङ्सिर`, `पौष`, `Mangshir` and other variants are
  refused. The year needs four digits. Month-first order (`Mangsir 8, 2083`)
  is refused, as are abbreviated month names. A weekday may follow and is
  checked against the date; a wrong one is an error.
- `format_bs` patterns have ten tokens (`%Y %y %m %-m %B %d %-d %A %a %%`).
  There is no padding control beyond these, no AD tokens and no time. `%a`
  uses the unreviewed short weekday names. Any `style` containing `%` is
  treated as a pattern, and an unknown token is an error.
- **Arithmetic** (`add_days`, `add_months`, `difference`, `age`): a start or
  result inside the disputed month raises `DisputedDateError` unless
  `allow_disputed=True`; crossing it does not, because the total for the two
  months is the same in every table. `add_months` keeps the day and clamps
  it to the target month's length (32 Asar + 1 month = 31 Shrawan), so
  adding and then subtracting a month does not always return to the start.
  `difference` counts whole months first, then days. `age` is whole years
  completed; someone born on a day that the birthday month lacks in a later
  year turns a year older on that month's last day.
- `month_calendar` weeks start on Sunday. The short weekday names in
  `format_month_calendar` are unreviewed.
- No time-of-day or time-zone handling, and no `datetime`-style operators (`+`, `-`). `today_bs()` uses
  Nepal time (UTC+05:45).
- Dates before BS 2000 and tithi (lunar day) are out of scope for now.

## Verification gaps

- The number-word table was checked against web lists, not an official
  dictionary, and has not yet been reviewed by a native speaker. Several
  spellings are choices between accepted variants (see `docs/sources.md`).
- The stopword list is short, hand-written and unreviewed.
- CI runs the tests on Python 3.10 to 3.13. Python 3.9 was dropped: it is end-of-life and GitHub's current runners no longer provide it.
- No comparison with other Nepali packages has been made.

## Normaliser

- `र्इ` typed for `ई` is repaired from 0.5. The rule assumes `र्` directly
  before an independent `इ` is never intended; this was not checked against
  a corpus. Other vowels typed the same way (`र्ई`, `र्उ`) are not touched.
- A legacy-style short-i sign typed before its consonant is not reordered by
  `normalize`. (The Preeti converter does its own reordering first.)
- NFC decomposes `क़ ख़ ग़ ज़ ड़ ढ़ फ़ य़` (U+0958–095F) into letter + nukta. This is
  correct Unicode behaviour, but string lengths change.
- `|` becomes `।` only directly after Devanagari text (optionally one space)
  and before whitespace or the end. `छ|तर` is left alone.
- With the default `joiners="safe"`, a ZWJ/ZWNJ survives only between a virama
  and a following Devanagari letter. Joiners in other scripts (for example
  emoji sequences or Persian text) are removed; use `joiners="keep"` for
  mixed-script text.

## Numbers

- Words stop at 99,99,99,99,99,999 (10¹³ − 1). नील, पद्म and शंख are not
  implemented; larger values raise `ValueError`.
- Decimals are read digit by digit and trailing zeros are kept as written
  (`"12.50"` → बाह्र दशमलव पाँच शून्य).
- Currency rounds half-up to whole paisa. An amount that rounds to zero is
  शून्य रुपैयाँ with no sign.
- Floats are converted through their shortest `repr`; pass strings or
  `Decimal` for money.
- Non-strict `parse_number` accepts commas anywhere between digits (`1,2,3` → 123).
- **Ordinals** (0.5): `ordinal_to_words` covers 1 to 100 and gives one base
  form. No source was consulted; 6 forms are listed by hand and 94 come from
  a rule, of which the 32 for 59–70 and 79–98 (साठीऔँ, असीऔँ, नब्बेऔँ …) are
  the least certain. No feminine, plural or oblique forms, nothing above
  100, and `parse_words` does not read ordinals. See `docs/sources.md`.
- Fractions (आधा, डेढ, साढे) are not supported, in either direction.
- `parse_words` reads only whole spellings from the table and the listed
  alternatives. It does not correct typos, does not read digits mixed with
  words (`५ लाख`), and does not skip surrounding words: the text must be the
  number and nothing else.
- `parse_words` accepts a few things `number_to_words` never writes: सय and
  हजार alone at the start (100, 1000), a count above nine before सय
  (पन्ध्र सय → 1500), अरब and खरब as scales, and माइनस, दशमलब, रुपियाँ. These
  were added from general knowledge and are unreviewed.
- The long-i alternatives for 21–48 (एक्काईस, पच्चीस, सतचालीस …) and the
  single-न nineties are produced by a rule from the chosen spellings, not
  copied from a list. Some of the forms it produces may not be spellings
  anyone uses.

## Aksharas

- The split follows the writing, not the sound, so the count is not a spoken
  syllable count. A final halant consonant is a unit of its own.
- The rules are this project's own reading of the Unicode Devanagari block.
  They have not been compared with another segmenter or with Unicode's
  grapheme-cluster rules, and no native speaker has reviewed them.
- Outside Devanagari the fallback is one code point plus combining marks:
  emoji sequences and other Indic scripts' conjuncts are split.
- Details: `docs/aksharas.md`.

## Sorting

- The order is one set of choices among several in use. It was checked
  against no dictionary and is not claimed to match any. Where anusvara
  goes, and whether `क्ष`, `त्र`, `ज्ञ` are letters, are the points most likely
  to differ from what a reader expects.
- Digit strings are compared digit by digit (`10` before `2`). Text is not
  normalised before comparing.
- Details: `docs/sorting.md`.

## Script detection

- **Scripts, not languages.** `detect_script` and the other functions look
  only at Unicode ranges. Nepali, Hindi, Marathi, Maithili, Newari and
  Sanskrit in Devanagari are all `devanagari`; English, romanised Nepali
  and French are all `latin`. No function here claims to tell Nepali from
  Hindi.
- Shares count letters, marks and digits; spaces and punctuation are left
  out. `mixed` means both Devanagari and Latin letters are present in any
  proportion, so one English word in a Nepali paragraph gives `mixed`.
- Bengali, Arabic, CJK and every other script are reported together as `other`.
- **`looks_romanised_nepali` is a rough heuristic.** It counts how many
  Latin words are in a hand-written list of 71 common romanised Nepali
  words. The list is unreviewed, the default threshold was chosen by
  judgement, and its accuracy has not been measured on real text. Short
  texts, names, and text with unusual spellings will be missed; romanised
  Hindi or Maithili that shares words can be accepted.

## Tokeniser and sentence splitter

- Tokens break at script boundaries: `Facebookमा` → `Facebook`, `मा`;
  `5G` → `5`, `G`.
- Hyphenated Devanagari splits into three tokens (`आ-आफ्नो`); hyphenated Latin
  words stay whole.
- Dates such as `२०८०-०१-१५` are split at the hyphens.
- No stemming: postpositions stay attached (`नेपालको` is one token).
- A full stop after a listed abbreviation never ends a sentence, so
  `... arrived etc. Then dinner.` stays as one sentence.
- A sentence ending in a dotted abbreviation or a single Latin initial
  (`... in the U.S. Then ...`) is not split there.
- A full stop followed by a lower-case Latin letter does not split.
- `?` and `!` always end a sentence, including inside a URL query string.
- The abbreviation list is short and hand-written.
