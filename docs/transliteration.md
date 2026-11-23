# Transliteration

`aksharkit.translit` converts between Devanagari and Roman letters. It is
plain Python with no data files. The tables and rules were written for this
project; nothing was copied from another package.

```python
import aksharkit as ak

ak.to_roman("नेपाल राम्रो छ।")  # 'nepāla rāmro cha|'
ak.to_devanagari("nepāla rāmro cha|")  # 'नेपाल राम्रो छ।'
ak.to_roman("नेपाल राम्रो छ।", "simple")  # 'nepal ramro chha.'
ak.to_devanagari("mero ghar", "simple")  # 'मेरो घर'
```

There are two schemes, and they make very different promises.

| | `iast` | `simple` |
| --- | --- | --- |
| Alphabet | Roman with diacritics (ā ī ū ṛ ṭ ḍ ṇ ś ṣ ṅ ñ ṃ ḥ) | plain ASCII |
| Devanagari → Roman | exact | rule-based, **approximate** |
| Roman → Devanagari | exact | best effort, **often wrong** |
| Round trip | yes, under the conditions below | no |
| Use it for | storing, searching, library catalogues, anything that must come back | showing a readable spelling to a person |

## The `iast` scheme

It follows IAST, with ISO 15919 where IAST has no letter.

| Devanagari | Roman |
| --- | --- |
| अ आ इ ई उ ऊ ऋ ॠ ए ऐ ओ औ | a ā i ī u ū ṛ ṝ e ai o au |
| क ख ग घ ङ | k kh g gh ṅ |
| च छ ज झ ञ | c ch j jh ñ |
| ट ठ ड ढ ण | ṭ ṭh ḍ ḍh ṇ |
| त थ द ध न | t th d dh n |
| प फ ब भ म | p ph b bh m |
| य र ल व | y r l v |
| श ष स ह ळ | ś ṣ s h ḷ |
| ं (anusvara) | ṃ (`ṁ` is also read) |
| ँ (candrabindu) | m̐ (the letter m followed by U+0310) |
| ः (visarga) | ḥ |
| ऽ (avagraha) | `'` |
| । and ॥ | `\|` and `\|\|` |
| ०–९ | 0–9 (unless `digits=False`) |
| क़ ख़ ग़ ज़ ड़ ढ़ फ़ य़ | q x ġ z ṙ ṙh f ẏ |

A consonant with no vowel sign carries the inherent `a` (क → `ka`); a halant
removes it (क् → `k`).

### Where it departs from the standards, and why

- **ड़ is `ṙ` and ढ़ is `ṙh`.** ISO 15919 writes ड़ as `ṛ`, which is IAST's
  letter for the vowel ऋ. One letter cannot mean both and still be reversible,
  so the vowel keeps `ṛ`.
- **ख़ is `x`.** The usual `k͟h` needs a combining line under two letters.
- **A colon separates letters that would otherwise merge**, as in ISO 15919:
  कइ → `ka:i` (not `kai`, which is कै), क्ह → `k:ha` (not `kha`, which is ख),
  क्अ → `k:a`. A real colon between two letters is doubled (क:ख → `ka::kha`);
  a colon before a space or at the end is left alone.

### When the round trip holds

`to_devanagari(to_roman(text)) == text` when all of these are true:

1. The text is in NFC (the functions normalise their input, so the result
   is compared with the NFC form). Note that NFC splits the eight
   precomposed nukta letters U+0958–095F into letter + nukta.
2. It has no Latin letters. They pass through `to_roman` unchanged and would
   then be read as IAST: `abc` comes back as अब्च्.
3. It has no ASCII digits (they would come back as Devanagari digits), or
   `digits=False` is passed to both calls.
4. It has no `|` (it would come back as ।) and no two single dandas in a row
   (।। comes back as ॥ — `normalize` makes the same repair).
5. It has no apostrophe directly after a Devanagari letter (it would come
   back as ऽ).

Everything else is either converted reversibly or passed through untouched:
other punctuation, spaces, ZWJ/ZWNJ, ॐ, and Devanagari characters outside the
table above (for example ऑ, ऍ, ॅ, ॉ, ऌ, ऩ, ऱ, the abbreviation sign ॰).

The test suite checks the round trip for every consonant (including the
nukta letters) with every vowel sign and mark, every pair of consonants with
and without a halant, every independent vowel in every position, a list of
harder conjuncts, and 10,000 random well-formed strings.

## The `simple` scheme

This is how Nepali is commonly typed in chat. It is lossy by design.

### Devanagari → simple

- Long and short vowels are the same letter: आ and अ → `a`, ई and इ → `i`,
  ऊ and उ → `u`. ऋ → `ri`.
- Retroflex and dental stops are the same: ट/त → `t`, ठ/थ → `th`,
  ड/द → `d`, ढ/ध → `dh`, ण/न → `n`. श and ष → `sh`.
- च → `ch`, छ → `chh`, ङ → `ng`, ञ → `ny`, क्ष → `ksh`, ज्ञ → `gy`.
- व → `v`, or `w` when it follows another consonant (स्वागत → `swagat`).
  Nepali often pronounces व as b or w; the scheme does not guess.
- Anusvara → `m` before प फ ब भ म and at the end of a word after the
  inherent vowel, otherwise `n`. Candrabindu → `n`. Visarga → `h` at the end
  of a word and nothing inside one (दुःख → `dukha`).
- Nukta letters: क़ `q`, ख़ `kh`, ग़ `g`, ज़ `z`, ड़ `r`, ढ़ `rh`, फ़ `f`.
- । → `.`, ॥ → `||`, digits → ASCII digits.

**The inherent `a` at the end of a word is dropped** (नेपाल → `nepal`,
घर → `ghar`), **except** when:

1. the word is a single syllable (म → `ma`, छ → `chha`, र → `ra`);
2. the word ends in a conjunct (मित्र → `mitra`, गर्छ → `garchha`,
   सम्बन्ध → `sambandha`);
3. the syllable before it carries an anusvara or visarga (अंक → `anka`);
4. the last letter is य (समय → `samaya`, हिमालय → `himalaya`) or
   छ (हुनेछ → `hunechha`);
5. it is a negative verb form ending in ‑ैन, ‑इन or ‑एन (छैन → `chhaina`,
   होइन → `hoina`);
6. the word has three or more syllables and ends in ‑ेर (गरेर → `garera`);
7. the word is in a short hand-written list: तर, अब, जब, तब, किन, बाट, गर,
   भन, हुन, आज, तल, सँग, पर, वर, तिर, बाहिर, अझ, झन.

An explicit halant always wins (हुन् → `hun`).

**The inherent `a` in the middle of a word is always kept**, because no
reliable rule was found: सरकार → `sarakar`, गोरखा → `gorakha`. The one
exception is a word that ends in a common second element — बजार, डाँडा,
खोला, नगर, गञ्ज, गाउँ, बारी, बेसी, गढी, पुर, कोट, टार, घाट, चोक, गढ — where
the first part is treated as a word of its own: ललितपुर → `lalitpur`,
धनगढी → `dhangadhi`.

So customary spellings are **not** reproduced: काठमाडौँ gives `kathamadaun`,
not Kathmandu; विराटनगर gives `viratnagar`, not Biratnagar.

### simple → Devanagari

Best effort only. The reading is fixed, not clever:

| Typed | Read as | So it cannot produce |
| --- | --- | --- |
| `a` | अ (the inherent vowel) | आ — type `aa` |
| `i`, `u` | इ, उ | ई, ऊ — type `ee`/`ii`, `oo`/`uu` |
| `t`, `th`, `d`, `dh`, `n` | त थ द ध न | ट ठ ड ढ ण |
| `s`, `sh` | स, श | ष (except in `ksh` → क्ष) |
| `ri` | रि | ऋ |
| `n` before `k`/`g` | ङ | न् + क (`jankari` → जङ्करि) |
| `ng` at the end or before a consonant | ङ | |
| `gy` at the start of a word | ज्ञ | ग्य |
| `c`, `q` → क; `f` → फ; `z` → ज; `w`, `v` → व; `x` → क्स | | |
| `.` after a word, before a space or the end | । | |

Consonants with no vowel between them are joined with a halant
(`namaste` → नमस्ते). No halant is added at the end of a word
(`garchhan` → गर्छन, not गर्छन्). Anusvara, candrabindu and visarga are never
produced. Upper-case letters are read as lower-case.

Of the 109 words in `tests/golden/translit_words.tsv`, 32 come back exactly
when their `simple` spelling is converted back to Devanagari.

## Spellings awaiting native-speaker review

`tests/golden/translit_words.tsv` lists every word with its expected `iast`
and `simple` output. Rows marked `review = yes` (37 of 109) are judgement
calls in the `simple` scheme, each with a note. They fall into these groups:

| Question | Examples |
| --- | --- |
| Long ā as `a` or `aa`? | नाम `nam`, काम `kam`, आमा `ama`, भात `bhat`, आज `aja` |
| व as `v`, `b` or `w`? | धन्यवाद `dhanyavad`, विकास `vikas`, विदेश `videsh`, हावा `hava`, विद्यार्थी `vidyarthi`, संविधान `sanvidhan` |
| Candrabindu as `n` or nothing? | गाउँ `gaun`, यहाँ `yahan`, सँग `sanga`, आउँछ `aunchha`, तपाईं `tapain` |
| Final `a` after a tatsama word? | सुख `sukh`, शुभ `shubh`, शिव `shiv`, दुःख `dukha` |
| Final `a` after य? | समय `samaya`, विजय `vijaya` |
| Middle `a` kept | सरकार `sarakar`, तरकारी `tarakari` |
| छ as `chh` or `ch`? | छ `chha` |
| ष्ट as `sht` or `st`? | राष्ट्रिय `rashtriya` |
| सिंह | `sinha` or `singh`? |
| Place names that differ from the customary spelling | काठमाडौँ `kathamadaun`, विराटनगर `viratnagar`, नेपालगञ्ज `nepalganj`, वीरगञ्ज `virganj`, गोरखा `gorakha`, चितवन `chitavan`, बुटवल `butaval`, सगरमाथा `sagaramatha`, बागमती `bagamati`, लमजुङ `lamajung` |

## Not done

- No dictionary. A word list of customary spellings (Kathmandu, Biratnagar)
  would fix most place names; none is bundled.
- No other schemes (Harvard-Kyoto, ITRANS, Velthuis, the Nepali government's
  romanisation).
- No capital letters in the output; no sentence casing.
- Devanagari → Roman does not mark which Devanagari characters were passed
  through untouched.
