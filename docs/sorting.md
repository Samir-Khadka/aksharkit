# Sorting: the order `sort_key` uses

`aksharkit.sort_key(text)` returns a key for `sorted`, and
`aksharkit.sorted_nepali(items)` sorts with it.

```python
import aksharkit as ak

ak.sorted_nepali(["हात", "कमल", "ज्ञान", "क्षेत्र", "काम", "अंक", "अक", "आमा", "त्रिशूल", "तारा"])
# ['अंक', 'अक', 'आमा', 'कमल', 'काम', 'तारा', 'हात', 'क्षेत्र', 'त्रिशूल', 'ज्ञान']
ak.sorted_nepali(["हात", "क्षेत्र", "कमल", "ज्ञान"], conjunct_letters=False)
# ['कमल', 'क्षेत्र', 'ज्ञान', 'हात']
sorted(words, key=ak.sort_key)
```

**Dictionaries do not all use the same order.** They differ on where
anusvara and candrabindu go, on whether `क्ष`, `त्र` and `ज्ञ` are letters of
their own, and on smaller points. The order below is one consistent set of
choices made for this project from general knowledge. It was not checked
against any dictionary, it is **not claimed to match any named dictionary or
any official rule**, and no native speaker has reviewed it. Every choice is
listed so that it can be checked and changed.

## How it differs from a plain sort

Python's own `sorted` compares code points. For Devanagari that is already
close to the alphabet. The differences are:

- `sorted` files `क्ष`, `त्र`, `ज्ञ` under `क`, `त`, `ज`. Here they come after `ह`
  unless `conjunct_letters=False`.
- `sorted` puts a nukta letter after everything that starts with the plain
  letter (`जहाज` before `ज़रा`). Here `ज़` sorts with `ज`.
- `sorted` puts Devanagari digits after every letter, and upper-case Latin
  before lower-case. Here digits and Latin come first and case is ignored
  except as a tie-break.
- `ऍ ऎ ऑ ऒ`, `ॠ ऌ ॡ` and joiners are placed differently (below).

## The order

1. **Everything that is not a Devanagari letter or sign comes first**:
   spaces, punctuation, digits, Latin and other scripts, by code point after
   case-folding. A Devanagari digit has the same weight as its ASCII digit.
   Numbers are compared digit by digit, not by value: `10` and `१०` come
   before `2` and `२`.
2. **Independent vowels**: अ आ इ ई उ ऊ ऋ ॠ ऌ ॡ ऍ ऎ ए ऐ ऑ ऒ ओ औ. The loanword
   vowels `ऍ ऎ` are put just before `ए`, and `ऑ ऒ` just before `ओ`; `ॠ ऌ ॡ`
   follow `ऋ`.
3. **Consonants** in the order of the Unicode block, U+0915 to U+0939:
   क ख ग घ ङ, च छ ज झ ञ, ट ठ ड ढ ण, त थ द ध न ऩ, प फ ब भ म, य र ऱ ल ळ ऴ व, श ष स ह.
   `ऩ ऱ ऴ ळ`, which Nepali does not use, simply keep their block position.
4. **`क्ष`, `त्र`, `ज्ञ`** as three more letters after `ह`, in that order. This
   applies wherever the conjunct occurs, not only at the start of a word:
   `कक्षा` comes after `कह…`, `पत्र` after `पहर`, and `क्षत्रिय` after `क्षमा`. A
   joiner inside the conjunct (`क्‍ष`) stops it being treated as a letter.
   With `conjunct_letters=False` they are ordinary conjuncts under `क`, `त`, `ज`.
5. **Other Devanagari letters** (`ऽ`, `ॐ`, the rarely used U+0972–U+097F)
   come last, by code point.

Within one consonant, what follows it is ordered like this:

| Order | What follows the consonant | Example |
| --- | --- | --- |
| 1 | nothing (end of the word) | क |
| 2 | candrabindu | कँ |
| 3 | anusvara | कं |
| 4 | visarga | कः |
| 5 | another letter | कक, कमल |
| 6 | a vowel sign, in the vowel order above | का, कि, की, कु, कू, कृ, के, कै, को, कौ |
| 7 | a virama (a conjunct or a final halant) | क्या, क्र, क् |

So `क < कँ < कं < कः < कक < का < कि < कौ < क्या < ख`. The same three signs
after a vowel sign or an independent vowel sort the same way: `का < काँ <
कां < काः < काक`, and `अंक < अक`.

Consequences that follow from these rules and may or may not be what a
particular dictionary does:

- **Anusvara is a sign, not a nasal consonant.** `अंक` and `अङ्क` are different
  keys and sort apart (`अंक < अक < अङ्क`). Dictionaries that file an anusvara
  as the nasal of the following consonant's class will order these words
  differently.
- **A conjunct sorts after every vowel sign of its first consonant.**
  `कर < करा < कर्म`: the `र्` of `कर्म` comes after `रा`.
- **A following letter sorts before a vowel sign.** `कमल < का`, because the
  inherent `अ` of `क` comes before `आ`.

Ties and marks:

- **Nukta** is ignored on the first pass: `ज़` sorts as `ज`. If two strings
  are otherwise the same, the one without the nukta comes first
  (`जरा < ज़रा < जल`). The precomposed letters U+0958–U+095F are treated as
  letter + nukta.
- **ZWJ and ZWNJ** are ignored on the first pass.
- **Case** is ignored on the first pass (`a < B < b`).
- Strings that are still equal after all of this are ordered by code point,
  so two different strings never compare equal and the sort is stable.
- Vowel signs outside the list in step 6 of the table (U+093A, U+093B,
  U+094E, U+094F, U+0955–U+0957) sort after the listed ones and before the
  virama.

## Limits

- Text is compared as written. It is not normalised first, so a word typed
  with a split vowel (`अ` + `ा`) sorts apart from the same word typed
  properly. Run `normalize` first.
- No numeric sorting, no ignoring of punctuation or spaces, no locale
  tailoring for the Latin part.
- No treatment of other conjuncts as letters (`श्र` is `श` + `्` + `र`).
- The CLI `aksharkit sort` reads one item per line, strips the ends of each
  line and drops empty lines.
