"""Alphabetical order for Nepali (Devanagari) text.

Python's default string order follows code points. For Devanagari that is
already close to the alphabet, but it files ``क्ष``, ``त्र`` and ``ज्ञ`` under
``क``, ``त`` and ``ज``, puts a nukta letter such as ``ज़`` after ``जह``, and puts
Devanagari digits after every letter. :func:`sort_key` gives an order built
on the alphabet instead: vowels, then consonants ``क`` to ``ह``, then ``क्ष``,
``त्र``, ``ज्ञ``.

Dictionaries do not agree with each other on several points (where anusvara
goes, whether ``क्ष`` is a letter of its own). The choices made here are
listed in ``docs/sorting.md``. The order is not claimed to match any
particular dictionary.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

__all__ = ["CONJUNCT_LETTERS", "CONSONANT_ORDER", "VOWEL_ORDER", "sort_key", "sorted_nepali"]

_NUKTA = "\u093c"
_VIRAMA = "\u094d"
_JOINERS = "\u200c\u200d"

#: Independent vowels in the order used. The first fourteen are the
#: traditional sequence; ``ऍ ऎ ऑ ऒ`` (used for loanwords) are placed next to
#: the vowel they resemble.
VOWEL_ORDER: tuple[str, ...] = (
    "अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ॠ", "ऌ", "ॡ", "ऍ", "ऎ", "ए", "ऐ", "ऑ", "ऒ", "ओ", "औ",
)  # fmt: skip

# The vowel sign for each of the vowels above, in the same order; अ has none.
_MATRA_ORDER: tuple[str, ...] = (
    "", "ा", "ि", "ी", "ु", "ू", "ृ", "ॄ", "ॢ", "ॣ", "ॅ", "ॆ", "े", "ै", "ॉ", "ॊ", "ो", "ौ",
)  # fmt: skip

#: Consonants ``क`` to ``ह`` in the order of the Devanagari block.
CONSONANT_ORDER: tuple[str, ...] = tuple(chr(cp) for cp in range(0x0915, 0x093A))

#: Conjuncts that are filed as letters of their own, after ``ह``.
CONJUNCT_LETTERS: tuple[str, ...] = ("क्ष", "त्र", "ज्ञ")

# An element of a key is ``(group, weight)``. Groups, lowest first:
_OTHER = 0  # spaces, punctuation, digits, other scripts: by code point
_SIGN = 1  # candrabindu, anusvara, visarga
_VOWEL_SLOT = 2  # the vowel a consonant carries; "no vowel" (virama) is last
_LETTER = 3  # independent vowels, then consonants

_SIGN_WEIGHT = {"\u0900": 0, "\u0901": 1, "\u0902": 2, "\u0903": 3}
_INHERENT = 0
_VOWEL_WEIGHT = {vowel: rank for rank, vowel in enumerate(VOWEL_ORDER)}
_MATRA_WEIGHT = {sign: rank for rank, sign in enumerate(_MATRA_ORDER) if sign}
_NO_VOWEL = 1000  # after every vowel sign, including the unlisted ones
_CONSONANT_BASE = 100
_CONSONANT_WEIGHT = {letter: _CONSONANT_BASE + rank for rank, letter in enumerate(CONSONANT_ORDER)}
_CONJUNCT_WEIGHT = {
    letter: _CONSONANT_BASE + len(CONSONANT_ORDER) + rank
    for rank, letter in enumerate(CONJUNCT_LETTERS)
}
_OTHER_LETTER_BASE = 2000  # any other Devanagari letter, by code point

_ASCII_ZERO = ord("0")
_DEVANAGARI_ZERO = 0x0966


def _is_matra(ch: str) -> bool:
    return (
        "\u093a" <= ch <= "\u093b"
        or "\u093e" <= ch <= "\u094c"
        or "\u094e" <= ch <= "\u094f"
        or "\u0955" <= ch <= "\u0957"
        or "\u0962" <= ch <= "\u0963"
    )


def _is_other_letter(ch: str) -> bool:
    """Devanagari letters outside the two ordered lists (ऄ, ऽ, ॐ, ॲ-ॿ)."""
    return ch in "\u0904\u093d\u0950" or "\u0972" <= ch <= "\u097f"


def _primary(text: str, conjunct_letters: bool) -> tuple[list[tuple[int, int]], list[int]]:
    """The key elements of ``text`` and the positions that carry a nukta."""
    elements: list[tuple[int, int]] = []
    nuktas: list[int] = []
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch in _CONSONANT_WEIGHT:
            weight = _CONSONANT_WEIGHT[ch]
            if conjunct_letters and text[i : i + 3] in _CONJUNCT_WEIGHT:
                weight = _CONJUNCT_WEIGHT[text[i : i + 3]]
                i += 2
            elements.append((_LETTER, weight))
            i += 1
            if i < length and text[i] == _NUKTA:
                nuktas.append(len(elements) - 1)
                i += 1
            if i < length and text[i] == _VIRAMA:
                elements.append((_VOWEL_SLOT, _NO_VOWEL))
                i += 1
            elif i < length and _is_matra(text[i]):
                elements.append((_VOWEL_SLOT, _MATRA_WEIGHT.get(text[i], ord(text[i]) - 0x0900)))
                i += 1
            else:
                elements.append((_VOWEL_SLOT, _INHERENT))
            continue
        i += 1
        if ch in _VOWEL_WEIGHT:
            elements.append((_LETTER, _VOWEL_WEIGHT[ch]))
        elif ch in _SIGN_WEIGHT:
            elements.append((_SIGN, _SIGN_WEIGHT[ch]))
        elif ch == _VIRAMA:
            elements.append((_VOWEL_SLOT, _NO_VOWEL))
        elif _is_matra(ch):
            elements.append((_VOWEL_SLOT, _MATRA_WEIGHT.get(ch, ord(ch) - 0x0900)))
        elif _is_other_letter(ch):
            elements.append((_LETTER, _OTHER_LETTER_BASE + ord(ch)))
        elif ch == _NUKTA:
            nuktas.append(len(elements) - 1)
        elif ch in _JOINERS or "\u0951" <= ch <= "\u0954":
            pass  # no weight of their own; the tie-break still sees them
        elif "\u0966" <= ch <= "\u096f":
            elements.append((_OTHER, ord(ch) - _DEVANAGARI_ZERO + _ASCII_ZERO))
        else:
            elements.extend((_OTHER, ord(folded)) for folded in ch.casefold())
    return elements, nuktas


def sort_key(
    text: str, *, conjunct_letters: bool = True
) -> tuple[tuple[tuple[int, int], ...], tuple[int, ...], str]:
    """A key that sorts Nepali text in alphabetical order.

    Use it as ``sorted(words, key=sort_key)``. With
    ``conjunct_letters=False`` the conjuncts ``क्ष``, ``त्र`` and ``ज्ञ`` are
    filed under ``क``, ``त`` and ``ज`` instead of after ``ह``.

    The key has three parts: the letters; which letters carry a nukta (so
    ``ज़`` sorts with ``ज``, the plain letter first); and the text itself, so
    that two different strings never compare equal.
    """
    if not isinstance(text, str):
        raise TypeError("sort_key expects a str")
    composed = unicodedata.normalize("NFC", text)
    elements, nuktas = _primary(composed, conjunct_letters)
    return tuple(elements), tuple(nuktas), composed


def sorted_nepali(
    items: Iterable[str], *, reverse: bool = False, conjunct_letters: bool = True
) -> list[str]:
    """Return ``items`` as a new list in Nepali alphabetical order."""
    return sorted(
        items,
        key=lambda item: sort_key(item, conjunct_letters=conjunct_letters),
        reverse=reverse,
    )
