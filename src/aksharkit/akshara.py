"""Akshara (orthographic syllable) segmentation for Devanagari text.

An akshara is the unit a reader sees as one written syllable: ``क्ष``, ``त्रि``,
``स्त्री``, ``हुँ``. Cutting a string between two code points can leave a matra
without its consonant or half a conjunct; cutting between aksharas cannot.

The rules are written from the structure of the Unicode Devanagari block
(U+0900-U+097F) and are described, with their limits, in ``docs/aksharas.md``.
They are orthographic, not phonetic: nothing here knows how a word is said.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

__all__ = ["Akshara", "akshara_count", "akshara_spans", "aksharas", "truncate"]


@dataclass(frozen=True)
class Akshara:
    """One akshara with its position in the original string.

    ``text == source[start:end]``.
    """

    text: str
    start: int
    end: int


# Character classes of the Devanagari block, written as regex ranges.
_CONSONANT = "\u0915-\u0939\u0958-\u095f\u0978-\u097f"
_VOWEL = "\u0904-\u0914\u0960\u0961\u0972-\u0977"
_NUKTA = "\u093c"
_VIRAMA = "\u094d"
_MATRA = "\u093a\u093b\u093e-\u094c\u094e\u094f\u0955-\u0957\u0962\u0963"
# Candrabindu, anusvara, visarga (and inverted candrabindu), then the Vedic
# stress marks U+0951-U+0954, which sit on the syllable in the same way.
_MODIFIER = "\u0900-\u0903\u0951-\u0954"
_JOINER = "\u200c\u200d"

_CLUSTER = re.compile(
    # A consonant cluster: consonants (each with an optional nukta) chained by
    # virama, an optional joiner allowed after each virama. It ends either in
    # a bare virama (a dead consonant, ``न्``) or in vowel signs and modifiers.
    f"[{_CONSONANT}][{_NUKTA}]?"
    f"(?:[{_VIRAMA}][{_JOINER}]?[{_CONSONANT}][{_NUKTA}]?)*"
    f"(?:[{_VIRAMA}]|[{_MATRA}]*[{_MODIFIER}]*)"
    # An independent vowel with its modifiers.
    f"|[{_VOWEL}][{_MATRA}]*[{_MODIFIER}]*"
)


def _attaches(ch: str) -> bool:
    """True for a character that belongs to whatever stands before it."""
    return ch in "\u200c\u200d" or unicodedata.category(ch)[0] == "M"


def akshara_spans(text: str) -> list[Akshara]:
    """Split ``text`` into aksharas, keeping character offsets.

    Every character of ``text`` belongs to exactly one akshara, so joining
    the pieces gives the input back. Outside Devanagari each code point is
    its own unit, with any combining marks that follow it attached.
    """
    if not isinstance(text, str):
        raise TypeError("akshara_spans expects a str")
    out: list[Akshara] = []
    pos = 0
    length = len(text)
    while pos < length:
        match = _CLUSTER.match(text, pos)
        end = match.end() if match is not None else pos + 1
        # Stray marks and joiners stay with the unit before them.
        while end < length and _attaches(text[end]):
            end += 1
        out.append(Akshara(text[pos:end], pos, end))
        pos = end
    return out


def aksharas(text: str) -> list[str]:
    """Split ``text`` into aksharas: ``"नमस्ते"`` -> ``["न", "म", "स्ते"]``."""
    return [unit.text for unit in akshara_spans(text)]


def akshara_count(text: str, *, skip_whitespace: bool = False) -> int:
    """Number of aksharas in ``text``.

    Spaces, digits and punctuation are one unit each and are counted. Pass
    ``skip_whitespace=True`` to leave whitespace out.
    """
    units = akshara_spans(text)
    if skip_whitespace:
        return sum(1 for unit in units if not unit.text.isspace())
    return len(units)


def truncate(text: str, limit: int, *, suffix: str = "") -> str:
    """Cut ``text`` to at most ``limit`` aksharas, never inside one.

    ``suffix`` (for example ``"…"``) is added only when something was cut
    off; it does not count towards ``limit``. Whitespace left at the cut is
    removed before the suffix is added.
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("truncate expects an int limit")
    if limit < 0:
        raise ValueError(f"limit must be 0 or more, not {limit}")
    units = akshara_spans(text)
    if len(units) <= limit:
        return text
    cut = units[limit].start
    if not suffix:
        return text[:cut]
    return text[:cut].rstrip() + suffix
