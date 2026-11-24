# What `normalize` does

`aksharkit.normalize(text, *, joiners="safe", danda=True, whitespace=True)`
applies these steps in order. The result is idempotent: normalising twice
gives the same string as normalising once.

| # | Step | Example |
| --- | --- | --- |
| 1 | Joiner policy (see below) | `नेपा‍ल` with a stray ZWJ → `नेपाल` |
| 2 | Remove invisible characters: zero-width space, word joiner, BOM, soft hyphen | |
| 3 | Unicode NFC | `न` + nukta → `ऩ` |
| 4 | Repair split vowels | `अ` + `ा` → `आ`; `ा` + `े` → `ो` |
| 5 | Repair `र्इ` typed for `ई` (added in 0.5, see below) | `र्इश्वर` → `ईश्वर` |
| 6 | Collapse an immediately repeated combining sign | `किि` → `कि` |
| 7 | Whitespace: CRLF → LF, tabs and no-break spaces → space, runs collapsed, ends trimmed. Line breaks are kept | |
| 8 | Danda repair | `छ|` → `छ।`; `।।` → `॥` |

Steps 2 and 7 are skipped with `whitespace=False`; step 8 with `danda=False`.

## Joiner policies

ZWJ (U+200D) and ZWNJ (U+200C) change how a conjunct is drawn, so they are
sometimes meaningful: `र्‍य` (as in र्‍याल) needs its ZWJ.

- `"safe"` (default): keep one joiner where it sits between a virama and a
  following Devanagari letter; remove it anywhere else. If several are stacked
  there, the last one is kept.
- `"strip"`: remove every joiner. Useful for search keys; changes rendering.
- `"keep"`: leave joiners untouched.

## Split-vowel repairs

`अ+ा→आ`, `अ+ो→ओ`, `अ+ौ→औ`, `आ+े→ओ`, `आ+ै→औ`, `ए+े→ऐ`, `उ+ु→ऊ`,
`ा+े→ो`, `ा+ै→ौ`, `ा+ॅ→ॉ`.

## `र्इ` for `ई`

`ई` is sometimes typed as `र` + virama + `इ`, which many fonts draw the same
way (a reph over `इ`). `repair_reph_i` replaces that sequence with `ई`.

It is left alone when the `र` is itself the second part of a conjunct
(`क्र्इ`), or when a ZWJ or ZWNJ sits between the virama and the `इ`. The rule
assumes that `र्` directly before an independent `इ` is never intended in
Nepali text; that was not checked against a corpus. Call the other steps
yourself if you need to keep such a sequence.

## What it deliberately leaves alone

- Spelling. `कीि` (two different vowel signs) is not "fixed".
- Repeated avagraha `ऽऽ`, repeated letters and digits.
- `|` that is not clearly a danda (`a | b`, `छ|तर`).
- Digits: use `to_devanagari_digits` / `to_ascii_digits`.
- Blank lines.

See `docs/known-issues.md` for the limits.
