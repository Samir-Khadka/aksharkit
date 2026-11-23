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
| 5 | Collapse an immediately repeated combining sign | `किि` → `कि` |
| 6 | Whitespace: CRLF → LF, tabs and no-break spaces → space, runs collapsed, ends trimmed. Line breaks are kept | |
| 7 | Danda repair | `छ|` → `छ।`; `।।` → `॥` |

Steps 2 and 6 are skipped with `whitespace=False`; step 7 with `danda=False`.

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

## What it deliberately leaves alone

- Spelling. `कीि` (two different vowel signs) is not "fixed".
- Repeated avagraha `ऽऽ`, repeated letters and digits.
- `|` that is not clearly a danda (`a | b`, `छ|तर`).
- Digits: use `to_devanagari_digits` / `to_ascii_digits`.
- Blank lines.

See `docs/known-issues.md` for the limits.
