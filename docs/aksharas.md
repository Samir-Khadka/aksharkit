# Aksharas: how the text is split

`aksharkit.aksharas(text)` splits text into aksharas, the units a reader sees
as one written syllable. `akshara_spans` gives the same units with their
offsets, `akshara_count` counts them, and `truncate(text, limit)` shortens
text without cutting through one.

```python
import aksharkit as ak

ak.aksharas("नमस्ते")  # ['न', 'म', 'स्ते']
ak.aksharas("विद्यार्थी")  # ['वि', 'द्या', 'र्थी']
ak.akshara_spans("स्त्री शक्ति")
# [Akshara(text='स्त्री', start=0, end=6), Akshara(text=' ', start=6, end=7),
#  Akshara(text='श', start=7, end=8), Akshara(text='क्ति', start=8, end=12)]
ak.akshara_count("काठमाडौँ उपत्यका")  # 9
ak.akshara_count("काठमाडौँ उपत्यका", skip_whitespace=True)  # 8
ak.truncate("विद्यार्थीहरू विद्यालय गए", 6, suffix="…")  # 'विद्यार्थीहरू…'
```

Joining the units always gives back the original string; nothing is added,
removed or normalised.

## The rules

The rules were written for this project from the layout of the Unicode
Devanagari block (U+0900–U+097F). They were not taken from another segmenter
and have not been compared with one, or with Unicode's own grapheme-cluster
rules (UAX #29).

Character classes used:

| Class | Characters |
| --- | --- |
| Consonant | U+0915–U+0939 (क to ह), U+0958–U+095F (क़ to य़), U+0978–U+097F |
| Independent vowel | U+0904–U+0914 (ऄ to औ), U+0960, U+0961 (ॠ, ॡ), U+0972–U+0977 |
| Nukta | U+093C |
| Virama (halant) | U+094D |
| Vowel sign (matra) | U+093A, U+093B, U+093E–U+094C, U+094E, U+094F, U+0955–U+0957, U+0962, U+0963 |
| Modifier | U+0900–U+0903 (candrabindu, anusvara, visarga), U+0951–U+0954 |
| Joiner | U+200C (ZWNJ), U+200D (ZWJ) |

One akshara is the longest match of the first rule that applies:

1. **Consonant cluster.** A consonant with an optional nukta, then any
   number of *virama, optional joiner, consonant, optional nukta*; ending in
   either a bare virama, or any number of vowel signs followed by any number
   of modifiers. So `स्त्री`, `र्थी`, `क्ष`, `ज़`, `हुँ`, `दुः` are one unit each,
   and `र्‍यो` (with its ZWJ) and `द्‌ध` (with its ZWNJ) stay whole.
2. **Independent vowel**, then any vowel signs and modifiers: `आँ`, `उ`, `ऑ`.
3. **Anything else** is one code point: a space, a digit, a danda, a Latin
   letter, `ॐ`, `ऽ`.

After any of the three, combining marks (Unicode categories Mn, Mc, Me) and
joiners that follow are attached to the unit. That is what keeps `é` typed as
`e` + U+0301 together, and what keeps a stray sign from standing alone when
it follows something.

## Choices worth knowing

- **A final dead consonant is its own unit.** `श्रीमान्` → `श्री`, `मा`, `न्` and
  `गर्नुहोस्` → `ग`, `र्नु`, `हो`, `स्`. It is not attached to the syllable before
  it, although it is said with it.
- **A consonant with virama joins the next consonant, always.** `नमस्ते` is
  `न`, `म`, `स्ते`, not `न`, `मस्`, `ते`. This follows the writing, not the sound.
- **Anusvara, candrabindu and visarga stay with the syllable before them.**
- **Spaces, digits and punctuation count as one unit each.** Use
  `akshara_count(text, skip_whitespace=True)` to leave whitespace out.
  `truncate` counts every unit, spaces included, and does not trim a trailing
  space before the suffix.
- `truncate(text, limit, suffix="…")` returns the text unchanged when it has
  `limit` units or fewer; otherwise the first `limit` units and the suffix.
  The suffix is not counted in the limit.

## Limits

- **Orthographic, not phonetic.** Nothing here knows about the unwritten
  vowel being dropped (`नेपाल` is three units though it is said in two
  syllables), so the count is not a syllable count for poetry or speech.
- **Malformed text is kept together, not repaired or rejected.** `कििि` is one
  unit and `अा` (अ + ा, a split आ) is one unit. A vowel sign at the very start
  of the text is a unit on its own. Run `normalize` first if the text may be
  untidy.
- **Outside Devanagari the fallback is one code point plus its combining
  marks.** That is not full grapheme segmentation: an emoji with a skin-tone
  modifier, a flag, or a ZWJ emoji sequence is split into its parts, and
  Hangul jamo are not grouped. Other Indic scripts (Bengali, Gurmukhi and so
  on) get the fallback too, so their conjuncts are split at the virama's
  following consonant.
- The Vedic signs in U+1CD0–U+1CFF and the Devanagari Extended block
  (U+A8E0–U+A8FF) have no rules of their own; the combining ones attach to
  the preceding unit like any other mark.
- Offsets are Python string indexes (code points), not bytes or UTF-16 units.
  In JavaScript the same text can have different indexes when it contains
  characters outside the Basic Multilingual Plane.
- No native speaker has reviewed the choices above.
