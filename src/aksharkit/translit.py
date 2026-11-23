"""Transliteration between Devanagari and the Roman alphabet.

Two schemes are offered:

``iast``
    Roman letters with diacritics, in the style of IAST / ISO 15919. It is
    reversible: for well-formed Devanagari made of the covered characters,
    ``to_devanagari(to_roman(text)) == text`` (see ``docs/transliteration.md``
    for the exact conditions and the few deliberate departures from IAST).

``simple``
    Plain ASCII, close to how Nepali is typed in chat and written on
    signboards (``नेपाल`` -> ``nepal``). It is rule-based and **approximate**
    in both directions: it throws information away going to Roman, and has
    to guess coming back.

Everything here is written for this project; no table or code was taken
from another package.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

__all__ = ["SCHEMES", "to_devanagari", "to_roman"]

SCHEMES = ("iast", "simple")

_VIRAMA = "\u094d"
_NUKTA = "\u093c"
_ANUSVARA = "\u0902"
_CHANDRABINDU = "\u0901"
_VISARGA = "\u0903"
_AVAGRAHA = "\u093d"
_DANDA = "\u0964"
_DOUBLE_DANDA = "\u0965"
_ZWJ = "\u200d"
_ZWNJ = "\u200c"

_DEV_DIGITS = "०१२३४५६७८९"
_ASCII_DIGITS = "0123456789"

# --------------------------------------------------------------------------
# IAST-style tables
# --------------------------------------------------------------------------

_CONSONANTS_IAST: dict[str, str] = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ṅ",
    "च": "c",
    "छ": "ch",
    "ज": "j",
    "झ": "jh",
    "ञ": "ñ",
    "ट": "ṭ",
    "ठ": "ṭh",
    "ड": "ḍ",
    "ढ": "ḍh",
    "ण": "ṇ",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "ś",
    "ष": "ṣ",
    "स": "s",
    "ह": "h",
    "ळ": "ḷ",
}

# Consonant + nukta. ISO 15919 writes ड़ as "ṛ", which is also IAST's letter
# for the vowel ऋ; to stay reversible aksharkit writes ड़ as "ṙ" and ख़ as "x".
_NUKTA_IAST: dict[str, str] = {
    "क": "q",
    "ख": "x",
    "ग": "ġ",
    "ज": "z",
    "ड": "ṙ",
    "ढ": "ṙh",
    "फ": "f",
    "य": "ẏ",
}

_VOWELS_IAST: dict[str, str] = {
    "अ": "a",
    "आ": "ā",
    "इ": "i",
    "ई": "ī",
    "उ": "u",
    "ऊ": "ū",
    "ऋ": "ṛ",
    "ॠ": "ṝ",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
}

_MATRAS_IAST: dict[str, str] = {
    "ा": "ā",
    "ि": "i",
    "ी": "ī",
    "ु": "u",
    "ू": "ū",
    "ृ": "ṛ",
    "ॄ": "ṝ",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
}

# Anusvara is IAST "ṃ"; candrabindu is ISO 15919 "m̐" (m + U+0310).
_MARKS_IAST: dict[str, str] = {
    _ANUSVARA: "ṃ",
    _CHANDRABINDU: "m\u0310",
    _VISARGA: "ḥ",
}

_C = "C"  # consonant
_V = "V"  # vowel
_M = "M"  # anusvara, candrabindu, visarga


def _build_iast_tokens() -> dict[str, tuple[str, str]]:
    """Roman token -> (kind, Devanagari). For vowels the value is the independent letter."""
    tokens: dict[str, tuple[str, str]] = {}
    for dev, roman in _CONSONANTS_IAST.items():
        tokens[roman] = (_C, dev)
    for dev, roman in _NUKTA_IAST.items():
        tokens[roman] = (_C, dev + _NUKTA)
    for dev, roman in _VOWELS_IAST.items():
        tokens[roman] = (_V, dev)
    for dev, roman in _MARKS_IAST.items():
        tokens[roman] = (_M, dev)
    tokens["ṁ"] = (_M, _ANUSVARA)  # ISO 15919 spelling, accepted on input
    return tokens


_IAST_TOKENS = _build_iast_tokens()
_IAST_MAX = max(len(token) for token in _IAST_TOKENS)
_IAST_MATRA_FOR = {roman: dev for dev, roman in _MATRAS_IAST.items()}


def _match(tokens: dict[str, tuple[str, str]], longest: int, text: str, pos: int) -> str | None:
    """Longest token of ``tokens`` that starts at ``text[pos]``."""
    for size in range(min(longest, len(text) - pos), 0, -1):
        candidate = text[pos : pos + size]
        if candidate in tokens:
            return candidate
    return None


def _needs_separator(left: str, right: str) -> bool:
    """True if ``left + right`` would be read back as a different first token."""
    return _match(_IAST_TOKENS, _IAST_MAX, left + right, 0) != left


def _lower(text: str) -> str:
    """Lower-case without ever changing the length of the string."""
    return "".join(low if len(low := ch.lower()) == 1 else ch for ch in text)


def _check_scheme(scheme: str) -> None:
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; choose one of {', '.join(SCHEMES)}")


# --------------------------------------------------------------------------
# Devanagari -> IAST
# --------------------------------------------------------------------------


def _is_iast_letter(ch: str) -> bool:
    return ch in _CONSONANTS_IAST or ch in _VOWELS_IAST


def _iast_from_devanagari(text: str, digits: bool) -> str:
    out: list[str] = []
    prev_roman = ""
    prev_kind = ""  # "", _C, _V or _M
    prev_bare = False  # previous token is a consonant with a virama

    def emit(roman: str, kind: str, *, bare: bool = False, independent: bool = False) -> None:
        nonlocal prev_roman, prev_kind, prev_bare
        if prev_kind and (
            (prev_bare and kind == _V and independent) or _needs_separator(prev_roman, roman)
        ):
            out.append(":")
        out.append(roman)
        prev_roman, prev_kind, prev_bare = roman, kind, bare

    def literal(chunk: str) -> None:
        nonlocal prev_kind, prev_bare
        out.append(chunk)
        prev_kind, prev_bare = "", False

    pos = 0
    size = len(text)
    while pos < size:
        ch = text[pos]
        if ch in _CONSONANTS_IAST:
            roman = _CONSONANTS_IAST[ch]
            pos += 1
            if pos < size and text[pos] == _NUKTA and ch in _NUKTA_IAST:
                roman = _NUKTA_IAST[ch]
                pos += 1
            if pos < size and text[pos] == _VIRAMA:
                emit(roman, _C, bare=True)
                pos += 1
            elif pos < size and text[pos] in _MATRAS_IAST:
                emit(roman, _C)
                emit(_MATRAS_IAST[text[pos]], _V)
                pos += 1
            else:
                emit(roman, _C)
                emit("a", _V)
        elif ch in _VOWELS_IAST:
            emit(_VOWELS_IAST[ch], _V, independent=True)
            pos += 1
        elif ch in _MARKS_IAST:
            emit(_MARKS_IAST[ch], _M)
            pos += 1
        elif ch == ":":
            end = pos
            while end < size and text[end] == ":":
                end += 1
            run = end - pos
            # A colon between two letters is the separator of this scheme, so
            # a real one written there is doubled to keep the text reversible.
            if prev_kind and end < size and _is_iast_letter(text[end]):
                run += 1
            literal(":" * run)
            pos = end
        elif ch == _AVAGRAHA and prev_kind:
            literal("'")
            pos += 1
        elif ch == _DANDA:
            literal("|")
            pos += 1
        elif ch == _DOUBLE_DANDA:
            literal("||")
            pos += 1
        elif digits and ch in _DEV_DIGITS:
            literal(_ASCII_DIGITS[_DEV_DIGITS.index(ch)])
            pos += 1
        else:
            literal(ch)
            pos += 1
    return "".join(out)


# --------------------------------------------------------------------------
# IAST -> Devanagari
# --------------------------------------------------------------------------


def _iast_to_devanagari(text: str, digits: bool) -> str:
    low = _lower(text)
    out: list[str] = []
    pending = False  # a consonant has been written and is waiting for its vowel
    prev_kind = ""
    separated = False  # an explicit ":" came just before this token

    def flush() -> None:
        nonlocal pending, prev_kind, separated
        if pending:
            out.append(_VIRAMA)
        pending, prev_kind, separated = False, "", False

    pos = 0
    size = len(text)
    while pos < size:
        token = _match(_IAST_TOKENS, _IAST_MAX, low, pos)
        if token is not None:
            kind, dev = _IAST_TOKENS[token]
            if kind == _C:
                if pending:
                    out.append(_VIRAMA)
                out.append(dev)
                pending = True
            elif kind == _V:
                if pending and not separated:
                    out.append(_IAST_MATRA_FOR.get(token, ""))
                else:
                    if pending:
                        out.append(_VIRAMA)
                    out.append(dev)
                pending = False
            else:
                if pending:
                    out.append(_VIRAMA)
                out.append(dev)
                pending = False
            prev_kind, separated = kind, False
            pos += len(token)
            continue
        ch = text[pos]
        if ch == ":" and prev_kind:
            end = pos
            while end < size and text[end] == ":":
                end += 1
            run = end - pos
            next_token = _match(_IAST_TOKENS, _IAST_MAX, low, end) if end < size else None
            if next_token is not None and _IAST_TOKENS[next_token][0] in (_C, _V):
                if run == 1:
                    separated = True
                    pos = end
                    continue
                run -= 1
            flush()
            out.append(":" * run)
            pos = end
        elif ch == "'" and prev_kind:
            flush()
            out.append(_AVAGRAHA)
            pos += 1
        elif ch == "|":
            flush()
            if low.startswith("||", pos):
                out.append(_DOUBLE_DANDA)
                pos += 2
            else:
                out.append(_DANDA)
                pos += 1
        elif digits and ch in _ASCII_DIGITS:
            flush()
            out.append(_DEV_DIGITS[_ASCII_DIGITS.index(ch)])
            pos += 1
        else:
            flush()
            out.append(ch)
            pos += 1
    if pending:
        out.append(_VIRAMA)
    return "".join(out)


# --------------------------------------------------------------------------
# Devanagari -> simple
# --------------------------------------------------------------------------

_CONSONANTS_SIMPLE: dict[str, str] = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    "ळ": "l",
}

_NUKTA_SIMPLE: dict[str, str] = {
    "क": "q",
    "ख": "kh",
    "ग": "g",
    "ज": "z",
    "ड": "r",
    "ढ": "rh",
    "फ": "f",
    "य": "y",
}

_VOWELS_SIMPLE: dict[str, str] = {
    "अ": "a",
    "आ": "a",
    "इ": "i",
    "ई": "i",
    "उ": "u",
    "ऊ": "u",
    "ऋ": "ri",
    "ॠ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
}

_MATRAS_SIMPLE: dict[str, str] = {
    "ा": "a",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "ृ": "ri",
    "ॄ": "ri",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
}

_VELARS = frozenset("कखगघ")
_LABIALS = frozenset("पफबभम")
_WORD_SIGNS = frozenset(
    (_VIRAMA, _NUKTA, _ANUSVARA, _CHANDRABINDU, _VISARGA, _ZWJ, _ZWNJ, *_MATRAS_SIMPLE)
)

# Common words that keep their final "a" although the general rule drops it.
# A short hand-written list; see docs/transliteration.md.
_KEEP_FINAL_A = frozenset(
    {
        "तर",
        "अब",
        "जब",
        "तब",
        "किन",
        "बाट",
        "गर",
        "भन",
        "हुन",
        "आज",
        "तल",
        "सँग",
        "पर",
        "वर",
        "तिर",
        "बाहिर",
        "अझ",
        "झन",
    }
)

# Words that drop their final "a" although they end in a conjunct.
_DROP_FINAL_A = frozenset({"गञ्ज"})

# Second elements of common compounds and place names. The element before
# one of these is romanised as a word of its own, so ललितपुर is "lalitpur".
_COMPOUND_FINALS = (
    "बजार",
    "डाँडा",
    "खोला",
    "नगर",
    "गञ्ज",
    "गाउँ",
    "बारी",
    "बेसी",
    "गढी",
    "पुर",
    "कोट",
    "टार",
    "घाट",
    "चोक",
    "गढ",
)


@dataclass
class _Unit:
    """One written syllable: a consonant cluster, its vowel and any marks."""

    consonants: list[str] = field(default_factory=list)  # each is a letter, maybe + nukta
    vowel: str = ""  # the vowel letter or sign; "" means inherent a or none
    inherent: bool = False  # the vowel is the unwritten "a"
    marks: list[str] = field(default_factory=list)


def _units(word: str) -> list[_Unit]:
    units: list[_Unit] = []
    pos = 0
    size = len(word)
    while pos < size:
        ch = word[pos]
        if ch in _CONSONANTS_SIMPLE:
            unit = _Unit()
            while pos < size and word[pos] in _CONSONANTS_SIMPLE:
                letter = word[pos]
                pos += 1
                if pos < size and word[pos] == _NUKTA:
                    letter += _NUKTA
                    pos += 1
                unit.consonants.append(letter)
                if pos < size and word[pos] == _VIRAMA:
                    pos += 1
                    if pos < size and word[pos] in _CONSONANTS_SIMPLE:
                        continue
                    break  # explicit halant: no vowel
                if pos < size and word[pos] in _MATRAS_SIMPLE:
                    unit.vowel = word[pos]
                    pos += 1
                else:
                    unit.inherent = True
                break
            units.append(unit)
        elif ch in _VOWELS_SIMPLE or ch in _MATRAS_SIMPLE:
            units.append(_Unit(vowel=ch))
            pos += 1
        elif ch in (_ANUSVARA, _CHANDRABINDU, _VISARGA):
            if not units:
                units.append(_Unit())
            units[-1].marks.append(ch)
            pos += 1
        else:  # stray virama or nukta
            pos += 1
    return units


def _cluster_simple(consonants: list[str]) -> str:
    parts: list[str] = []
    count = len(consonants)
    index = 0
    while index < count:
        letter = consonants[index]
        following = consonants[index + 1] if index + 1 < count else ""
        if letter == "ज" and following == "ञ":
            parts.append("gy")
            index += 2
            continue
        if (letter == "ङ" and following in _VELARS) or (letter == "ञ" and following):
            parts.append("n")
        elif letter == "व" and index > 0:
            parts.append("w")
        elif letter.endswith(_NUKTA):
            parts.append(_NUKTA_SIMPLE.get(letter[0], _CONSONANTS_SIMPLE[letter[0]]))
        else:
            parts.append(_CONSONANTS_SIMPLE[letter])
        index += 1
    return "".join(parts)


def _keeps_final_a(word: str, units: list[_Unit]) -> bool:
    last = units[-1]
    if word in _DROP_FINAL_A:
        return False
    if len(units) == 1 or len(last.consonants) != 1 or word in _KEEP_FINAL_A:
        return True
    before = units[-2]
    if _ANUSVARA in before.marks or _VISARGA in before.marks:
        return True
    if last.consonants in (["य"], ["छ"]):
        return True
    if last.consonants == ["न"] and before.vowel in ("ै", "इ", "ए"):
        return True  # negative verb forms: छैन, होइन, थिएन
    return len(units) >= 3 and last.consonants == ["र"] and before.vowel in ("ए", "े")


def _word_simple(word: str, *, split: bool = True) -> str:
    if split:
        for final in _COMPOUND_FINALS:
            if word.endswith(final) and len(word) > len(final):
                first = word[: -len(final)]
                if first[-1] not in _WORD_SIGNS or first[-1] in _MATRAS_SIMPLE:
                    return _word_simple(first, split=False) + _word_simple(final, split=False)
    units = _units(word)
    out: list[str] = []
    last_index = len(units) - 1
    for index, unit in enumerate(units):
        out.append(_cluster_simple(unit.consonants))
        if unit.inherent:
            is_final = index == last_index and not unit.marks
            if not is_final or _keeps_final_a(word, units):
                out.append("a")
        elif unit.vowel:
            out.append(_VOWELS_SIMPLE.get(unit.vowel) or _MATRAS_SIMPLE[unit.vowel])
        for mark in unit.marks:
            if mark == _VISARGA:
                if index == last_index:  # silent inside a word: दुःख is "dukha"
                    out.append("h")
            elif mark == _CHANDRABINDU:
                out.append("n")
            elif index == last_index:
                out.append("m" if unit.inherent else "n")
            else:
                following = units[index + 1].consonants
                out.append("m" if following and following[0][0] in _LABIALS else "n")
    return "".join(out)


def _is_word_char(ch: str) -> bool:
    return ch in _CONSONANTS_SIMPLE or ch in _VOWELS_SIMPLE or ch in _WORD_SIGNS


def _simple_from_devanagari(text: str, digits: bool) -> str:
    out: list[str] = []
    pos = 0
    size = len(text)
    while pos < size:
        ch = text[pos]
        if _is_word_char(ch):
            end = pos
            while end < size and _is_word_char(text[end]):
                end += 1
            word = text[pos:end].replace(_ZWJ, "").replace(_ZWNJ, "")
            out.append(_word_simple(word))
            pos = end
            continue
        if ch == _DANDA:
            out.append(".")
        elif ch == _DOUBLE_DANDA:
            out.append("||")
        elif ch == _AVAGRAHA:
            out.append("'")
        elif digits and ch in _DEV_DIGITS:
            out.append(_ASCII_DIGITS[_DEV_DIGITS.index(ch)])
        else:
            out.append(ch)
        pos += 1
    return "".join(out)


# --------------------------------------------------------------------------
# simple -> Devanagari
# --------------------------------------------------------------------------

# Roman token -> consonant letters (joined with virama when more than one).
_SIMPLE_CONSONANT_TOKENS: dict[str, tuple[str, ...]] = {
    "ksh": ("क", "ष"),
    "chh": ("छ",),
    "ch": ("च",),
    "kh": ("ख",),
    "gh": ("घ",),
    "jh": ("झ",),
    "th": ("थ",),
    "dh": ("ध",),
    "ph": ("फ",),
    "bh": ("भ",),
    "sh": ("श",),
    "k": ("क",),
    "g": ("ग",),
    "c": ("क",),
    "j": ("ज",),
    "t": ("त",),
    "d": ("द",),
    "n": ("न",),
    "p": ("प",),
    "f": ("फ",),
    "b": ("ब",),
    "m": ("म",),
    "y": ("य",),
    "r": ("र",),
    "l": ("ल",),
    "v": ("व",),
    "w": ("व",),
    "s": ("स",),
    "h": ("ह",),
    "z": ("ज",),
    "q": ("क",),
    "x": ("क", "स"),
}

# Roman token -> (independent vowel, vowel sign).
_SIMPLE_VOWEL_TOKENS: dict[str, tuple[str, str]] = {
    "aa": ("आ", "ा"),
    "ai": ("ऐ", "ै"),
    "au": ("औ", "ौ"),
    "ee": ("ई", "ी"),
    "ii": ("ई", "ी"),
    "oo": ("ऊ", "ू"),
    "uu": ("ऊ", "ू"),
    "a": ("अ", ""),
    "i": ("इ", "ि"),
    "u": ("उ", "ु"),
    "e": ("ए", "े"),
    "o": ("ओ", "ो"),
}

_SIMPLE_TOKENS: dict[str, tuple[str, str]] = {
    **dict.fromkeys(_SIMPLE_CONSONANT_TOKENS, (_C, "")),
    **dict.fromkeys(_SIMPLE_VOWEL_TOKENS, (_V, "")),
}
_SIMPLE_MAX = max(len(token) for token in _SIMPLE_TOKENS)
_VELAR_TOKENS = frozenset({"k", "kh", "g", "gh"})
_ASCII_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyz")


def _simple_tokens(word: str) -> list[str]:
    tokens: list[str] = []
    pos = 0
    size = len(word)
    while pos < size:
        if word.startswith("ng", pos) and (pos + 2 == size or word[pos + 2] not in "aeiouh"):
            tokens.append("ng")
            pos += 2
            continue
        token = _match(_SIMPLE_TOKENS, _SIMPLE_MAX, word, pos)
        if token is None:  # pragma: no cover - every ASCII letter starts a token
            token = word[pos]
        tokens.append(token)
        pos += len(token)
    return tokens


def _word_from_simple(word: str) -> str:
    tokens = _simple_tokens(word)
    out: list[str] = []
    pending = False
    for index, token in enumerate(tokens):
        if token in _SIMPLE_VOWEL_TOKENS:
            independent, sign = _SIMPLE_VOWEL_TOKENS[token]
            out.append(sign if pending else independent)
            pending = False
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        if token == "ng":
            letters: tuple[str, ...] = ("ङ",)
        elif token == "g" and index == 0 and following == "y":
            letters = ("ज",)  # word-initial "gy" is read as ज्ञ
        elif token == "y" and index == 1 and tokens[0] == "g":
            letters = ("ञ",)
        elif token == "n" and following in _VELAR_TOKENS:
            letters = ("ङ",)
        else:
            letters = _SIMPLE_CONSONANT_TOKENS[token]
        for letter in letters:
            if pending:
                out.append(_VIRAMA)
            out.append(letter)
            pending = True
    return "".join(out)


def _simple_to_devanagari(text: str, digits: bool) -> str:
    low = _lower(text)
    out: list[str] = []
    after_word = False
    pos = 0
    size = len(text)
    while pos < size:
        ch = low[pos]
        if ch in _ASCII_LETTERS:
            end = pos
            while end < size and low[end] in _ASCII_LETTERS:
                end += 1
            out.append(_word_from_simple(low[pos:end]))
            after_word = True
            pos = end
            continue
        if ch == "." and after_word and (pos + 1 == size or text[pos + 1].isspace()):
            out.append(_DANDA)
        elif ch == "|":
            if low.startswith("||", pos):
                out.append(_DOUBLE_DANDA)
                pos += 1
            else:
                out.append(_DANDA)
        elif digits and ch in _ASCII_DIGITS:
            out.append(_DEV_DIGITS[_ASCII_DIGITS.index(ch)])
        else:
            out.append(text[pos])
        after_word = False
        pos += 1
    return "".join(out)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def to_roman(text: str, scheme: str = "iast", *, digits: bool = True) -> str:
    """Write Devanagari ``text`` in Roman letters.

    ``scheme="iast"`` is reversible with :func:`to_devanagari`;
    ``scheme="simple"`` is plain ASCII and approximate. With ``digits=True``
    Devanagari digits become ASCII digits. Characters the scheme does not
    cover (Latin letters, most punctuation) are passed through unchanged.
    The input is NFC-normalised first.
    """
    _check_scheme(scheme)
    text = unicodedata.normalize("NFC", text)
    if scheme == "iast":
        return _iast_from_devanagari(text, digits)
    return _simple_from_devanagari(text, digits)


def to_devanagari(text: str, scheme: str = "iast", *, digits: bool = True) -> str:
    """Write Roman ``text`` in Devanagari.

    ``scheme="iast"`` reads exactly what :func:`to_roman` writes (upper-case
    letters are accepted). ``scheme="simple"`` is a best-effort reading of
    chat-style romanised Nepali: it cannot know ``t`` from ``ṭ``, ``d`` from
    ``ḍ``, ``s`` from ``ś``/``ṣ`` or short vowels from long ones, so it picks
    the defaults listed in ``docs/transliteration.md``. With ``digits=True``
    ASCII digits become Devanagari digits.
    """
    _check_scheme(scheme)
    text = unicodedata.normalize("NFC", text)
    if scheme == "iast":
        return _iast_to_devanagari(text, digits)
    return _simple_to_devanagari(text, digits)
