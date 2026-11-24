"""Legacy (pre-Unicode) Nepali font conversion: Preeti and Unicode. EXPERIMENTAL.

Fonts such as Preeti draw Devanagari shapes on ASCII key positions, so
``g]kfn`` on disk displays as ``नेपाल``. Converting needs two things:

1. **A key table** — which key draws which letter. The table in
   ``data/font_preeti.json`` holds only entries that at least two of three
   permissively-licensed table families agree on (see ``docs/preeti.md`` and
   ``scripts/compare_preeti_sources.py``). It has **not** been checked
   against real Preeti documents or by a native reader.
2. **Reordering** — Preeti stores what the typist pressed, in typing order,
   and that order is not Unicode's. The rules below are written from how
   Devanagari is put together, not taken from another converter:

   * the short-i sign is typed *before* its consonant and belongs *after*
     the whole consonant cluster;
   * the reph (the hook for a leading ``र्``) is typed *after* the syllable
     and belongs *before* its consonant cluster;
   * a half form followed by the upright bar is the full letter
     (``ण्`` + ``ा`` is ``ण``);
   * the ``m`` key is a stroke that turns the letter before it into another
     letter (``प`` into ``फ``), even when a vowel sign was typed in between;
   * vowel signs come before a nasal sign, and ``ा`` before ``े``/``ै``, so
     that the normaliser can compose ``ो`` and ``ौ``.

A character with no agreed table entry is passed through unchanged and
reported. Nothing is guessed.

Stretches of the input can be protected from conversion: web and e-mail
addresses (on by default), anything matching a pattern the caller gives,
listed words, and text between a pair of markers. See :func:`convert_preeti`.

The other direction, :func:`encode_preeti`, writes Unicode text as Preeti
key codes. It checks its own work: every word it writes is converted back
and compared, and a word that does not come back exactly is left as it was
and reported. What it cannot check is how its keys look in the Preeti font.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache, lru_cache
from typing import Any

from ._data import load_table
from .normalize import normalize

__all__ = [
    "PREETI_LABEL",
    "SUPPORTED_FONTS",
    "ForeignSpan",
    "PreetiEncodeResult",
    "PreetiEncodeStats",
    "PreetiResult",
    "PreetiSegment",
    "PreetiStats",
    "ProtectedSpan",
    "SkippedSpan",
    "UnmappedChar",
    "convert_preeti",
    "encode_preeti",
    "load_font_map",
    "load_font_table",
    "preeti_to_unicode",
    "to_unicode",
    "unicode_to_preeti",
]

#: Fonts with a data file in the package.
SUPPORTED_FONTS: tuple[str, ...] = ("preeti",)

#: The only table status the converter accepts.
EXPERIMENTAL = "experimental"

_VIRAMA = "\u094d"
_NUKTA = "\u093c"
_AA = "\u093e"
_SHORT_I = "\u093f"
_RA = "\u0930"
_VISARGA = "\u0903"
_DANDA = "\u0964"
_DOUBLE_DANDA = "\u0965"
_NASALS = "\u0901\u0902"

# Markers for the two keys whose letter has to move. They are longer than
# one character, so they can never be confused with a character of the text.
_PRE_I = "<pre-i>"
_REPH = "<reph>"

_STROKE_KEY = "m"
_REPH_KEY = "{"


def _is_consonant(ch: str) -> bool:
    return "\u0915" <= ch <= "\u0939" or "\u0958" <= ch <= "\u095f"


def _is_independent_vowel(ch: str) -> bool:
    return "\u0904" <= ch <= "\u0914" or ch in "\u0960\u0961"


def _is_vowel_sign(ch: str) -> bool:
    return "\u093e" <= ch <= "\u094c"


def _is_sign(ch: str) -> bool:
    """A vowel sign, a nasal sign or the visarga: what follows a consonant cluster."""
    return _is_vowel_sign(ch) or ch in _NASALS or ch == _VISARGA


def _is_devanagari_digit(ch: str) -> bool:
    return "\u0966" <= ch <= "\u096f"


def _is_devanagari(ch: str) -> bool:
    return "\u0900" <= ch <= "\u097f" or ch in "\u200c\u200d"


@dataclass(frozen=True)
class UnmappedChar:
    """A character of the input that had no agreed table entry.

    Two of these are equal when ``char`` and ``offset`` are; the other fields
    say the same thing in other terms.
    """

    char: str
    #: Index of the character in the input string.
    offset: int
    #: Line of the input, counting from 1. Lines end at ``\n``.
    line: int = field(default=1, compare=False)
    #: Position in that line, counting characters (code points) from 1.
    column: int = field(default=1, compare=False)
    #: Index of the character in the result text, or -1 when not known.
    output_offset: int = field(default=-1, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "char": self.char,
            "codepoint": f"U+{ord(self.char):04X}",
            "offset": self.offset,
            "line": self.line,
            "column": self.column,
            "output_offset": self.output_offset,
        }


@dataclass(frozen=True)
class ProtectedSpan:
    """A stretch of the input that was left alone on purpose."""

    #: Where the stretch starts in the input (markers included).
    start: int
    #: Where it ends in the input, exclusive (markers included).
    end: int
    #: The text as it stands in the result (markers removed).
    text: str
    #: ``"link"``, ``"keep"``, ``"word"`` or ``"marker"``.
    reason: str
    #: Index of the stretch in the result text.
    output_offset: int = -1

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "reason": self.reason,
            "output_offset": self.output_offset,
        }


@dataclass(frozen=True)
class PreetiStats:
    """How many input characters went which way.

    ``agreed``, ``majority`` and ``unconfirmed`` count characters converted
    with a key of that tier of the table (the two stroke keys ``m`` and ``{``
    count as ``agreed`` when they found a letter to act on). ``unmapped``
    characters had no usable entry. ``untouched`` is white space and text
    that was already Devanagari; ``protected`` is text inside a protected
    stretch, markers included.
    """

    agreed: int = 0
    majority: int = 0
    unconfirmed: int = 0
    unmapped: int = 0
    untouched: int = 0
    protected: int = 0

    @property
    def converted(self) -> int:
        """Characters that were converted, whatever the tier."""
        return self.agreed + self.majority + self.unconfirmed

    @property
    def convertible(self) -> int:
        """Characters the converter had to decide about: converted plus unmapped."""
        return self.converted + self.unmapped

    @property
    def total(self) -> int:
        return self.convertible + self.untouched + self.protected

    def share(self, kind: str) -> float:
        """The share of ``convertible`` characters that are of ``kind``.

        ``kind`` is ``"agreed"``, ``"majority"``, ``"unconfirmed"``,
        ``"unmapped"`` or ``"converted"``. With nothing to convert the share
        is 0.0.
        """
        if kind not in ("agreed", "majority", "unconfirmed", "unmapped", "converted"):
            raise ValueError(f"unknown kind {kind!r}")
        if not self.convertible:
            return 0.0
        return float(getattr(self, kind)) / self.convertible

    def __add__(self, other: PreetiStats) -> PreetiStats:
        return PreetiStats(
            self.agreed + other.agreed,
            self.majority + other.majority,
            self.unconfirmed + other.unconfirmed,
            self.unmapped + other.unmapped,
            self.untouched + other.untouched,
            self.protected + other.protected,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "agreed": self.agreed,
            "majority": self.majority,
            "unconfirmed": self.unconfirmed,
            "unmapped": self.unmapped,
            "untouched": self.untouched,
            "protected": self.protected,
            "convertible": self.convertible,
            "share_agreed": round(self.share("agreed"), 4),
            "share_majority": round(self.share("majority"), 4),
            "share_unconfirmed": round(self.share("unconfirmed"), 4),
            "share_unmapped": round(self.share("unmapped"), 4),
        }


def _unmapped_counts(unmapped: Iterable[UnmappedChar]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in unmapped:
        counts[item.char] = counts.get(item.char, 0) + 1
    return [
        {"char": ch, "codepoint": f"U+{ord(ch):04X}", "count": count}
        for ch, count in counts.items()
    ]


@dataclass(frozen=True)
class PreetiResult:
    """The outcome of a Preeti to Unicode conversion.

    Two results are equal when ``text`` and ``unmapped`` are.
    """

    #: The converted text. Unmapped characters are in it unchanged.
    text: str
    #: Every input character that was passed through for want of an entry.
    unmapped: tuple[UnmappedChar, ...]
    #: Stretches that were left alone on purpose, in input order.
    protected: tuple[ProtectedSpan, ...] = field(default=(), compare=False)
    #: Counts of input characters by what happened to them.
    stats: PreetiStats = field(default=PreetiStats(), compare=False)

    @property
    def complete(self) -> bool:
        """True when every character had an agreed entry."""
        return not self.unmapped

    @property
    def unmapped_chars(self) -> tuple[str, ...]:
        """The distinct unmapped characters, in order of first appearance."""
        return tuple(dict.fromkeys(item.char for item in self.unmapped))

    def as_dict(self) -> dict[str, Any]:
        """Everything in the result as plain JSON-ready data."""
        return {
            "direction": "preeti-to-unicode",
            "status": PREETI_LABEL,
            "complete": self.complete,
            "text": self.text,
            "stats": self.stats.as_dict(),
            "unmapped": [item.as_dict() for item in self.unmapped],
            "unmapped_counts": _unmapped_counts(self.unmapped),
            "protected": [span.as_dict() for span in self.protected],
        }


@dataclass(frozen=True)
class SkippedSpan:
    """A word that :func:`encode_preeti` left in Unicode.

    Its Preeti keys did not convert back to the same text, so writing them
    would have changed the word.
    """

    start: int
    end: int
    text: str
    line: int = field(default=1, compare=False)
    column: int = field(default=1, compare=False)
    output_offset: int = field(default=-1, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "line": self.line,
            "column": self.column,
            "output_offset": self.output_offset,
        }


@dataclass(frozen=True)
class ForeignSpan:
    """A stretch :func:`encode_preeti` left alone because it holds no Devanagari.

    An English word, an ASCII number, a lone symbol between English words.
    Such text has no Preeti keys and is not Nepali, so it is not a failure
    and is kept apart from ``unmapped``.
    """

    start: int
    end: int
    text: str
    line: int = field(default=1, compare=False)
    column: int = field(default=1, compare=False)
    output_offset: int = field(default=-1, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "line": self.line,
            "column": self.column,
            "output_offset": self.output_offset,
        }


@dataclass(frozen=True)
class PreetiSegment:
    """One stretch of the input and what :func:`encode_preeti` made of it.

    The segments of a result cover the (normalised) input from start to end
    without gaps, and their ``text`` values joined give ``result.text`` when
    no ``mark_kept`` markers were asked for.
    """

    #: Where the stretch starts and ends (exclusive) in the normalised input.
    start: int
    end: int
    #: What stands for it in the result: keys, or the text as it was.
    text: str
    #: ``"keys"``, ``"space"``, ``"unmapped"``, ``"skipped"``, ``"foreign"``
    #: or ``"protected"``. Only ``"keys"`` text is meant for the Preeti font.
    kind: str

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "text": self.text, "kind": self.kind}


@dataclass(frozen=True)
class PreetiEncodeStats:
    """Counts for one Unicode to Preeti conversion.

    A *word* here is a stretch between white space that holds at least one
    Devanagari character. ``words_encoded`` are the words written wholly as
    keys. The character counts leave white space out.
    """

    words: int = 0
    words_encoded: int = 0
    #: Characters written as keys.
    encoded: int = 0
    #: Characters of Nepali words that have no key, left as they were.
    unmapped: int = 0
    #: Characters in words left in Unicode because the keys did not read back.
    skipped: int = 0
    #: Characters in stretches with no Devanagari (English, ASCII numbers).
    foreign: int = 0
    #: Characters in protected stretches.
    protected: int = 0

    @property
    def share_words(self) -> float:
        """Share of the Nepali words written wholly as keys; 1.0 with no words."""
        return self.words_encoded / self.words if self.words else 1.0

    @property
    def share_chars(self) -> float:
        """Share of the characters of Nepali words written as keys."""
        total = self.encoded + self.unmapped + self.skipped
        return self.encoded / total if total else 1.0

    def __add__(self, other: PreetiEncodeStats) -> PreetiEncodeStats:
        return PreetiEncodeStats(
            self.words + other.words,
            self.words_encoded + other.words_encoded,
            self.encoded + other.encoded,
            self.unmapped + other.unmapped,
            self.skipped + other.skipped,
            self.foreign + other.foreign,
            self.protected + other.protected,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "words": self.words,
            "words_encoded": self.words_encoded,
            "encoded": self.encoded,
            "unmapped": self.unmapped,
            "skipped": self.skipped,
            "foreign": self.foreign,
            "protected": self.protected,
            "share_words": round(self.share_words, 4),
            "share_chars": round(self.share_chars, 4),
        }


@dataclass(frozen=True)
class PreetiEncodeResult:
    """The outcome of a Unicode to Preeti conversion."""

    #: The Preeti key codes. Characters with no key are in it unchanged.
    text: str
    #: Characters of Nepali words that have no Preeti key in the table.
    unmapped: tuple[UnmappedChar, ...]
    #: Words left in Unicode because their keys did not convert back exactly.
    skipped: tuple[SkippedSpan, ...] = ()
    #: Stretches that were left alone on purpose, in input order.
    protected: tuple[ProtectedSpan, ...] = field(default=(), compare=False)
    #: Characters written as keys.
    encoded: int = field(default=0, compare=False)
    #: Stretches with no Devanagari in them (English, ASCII numbers), left alone.
    foreign: tuple[ForeignSpan, ...] = field(default=(), compare=False)
    #: The input cut into stretches, each with what was written for it.
    segments: tuple[PreetiSegment, ...] = field(default=(), compare=False)
    #: Word and character counts.
    stats: PreetiEncodeStats = field(default_factory=PreetiEncodeStats, compare=False)
    #: The markers put round kept text, when ``mark_kept`` was given.
    mark_kept: tuple[str, str] | None = field(default=None, compare=False)

    @property
    def complete(self) -> bool:
        """True when every Nepali word was written as keys that convert back exactly.

        Text with no Devanagari in it (``foreign``) does not count against this.
        """
        return not self.unmapped and not self.skipped

    @property
    def unmapped_chars(self) -> tuple[str, ...]:
        """The distinct characters with no key, in order of first appearance."""
        return tuple(dict.fromkeys(item.char for item in self.unmapped))

    def as_dict(self) -> dict[str, Any]:
        return {
            "direction": "unicode-to-preeti",
            "status": PREETI_LABEL,
            "complete": self.complete,
            "text": self.text,
            "encoded": self.encoded,
            "stats": self.stats.as_dict(),
            "unmapped": [item.as_dict() for item in self.unmapped],
            "unmapped_counts": _unmapped_counts(self.unmapped),
            "skipped": [span.as_dict() for span in self.skipped],
            "foreign": [span.as_dict() for span in self.foreign],
            "protected": [span.as_dict() for span in self.protected],
            "segments": [segment.as_dict() for segment in self.segments],
            "mark_kept": list(self.mark_kept) if self.mark_kept else None,
        }


def _check_font(font: str) -> str:
    key = font.strip().lower()
    if key not in SUPPORTED_FONTS:
        raise ValueError(f"unknown font {font!r}; known fonts: {', '.join(SUPPORTED_FONTS)}")
    return key


@cache
def _table(key: str) -> dict[str, Any]:
    table = load_table(f"font_{key}")
    if table.get("status") != EXPERIMENTAL or not table.get("mapping"):
        raise ValueError(
            f"font table for {key!r} is malformed: expected status {EXPERIMENTAL!r} "
            "and a non-empty 'mapping'"
        )
    if not table.get("sources"):
        raise ValueError(f"font table for {key!r} lists no sources")
    return table


def load_font_table(font: str = "preeti") -> dict[str, Any]:
    """Return the whole data table for ``font``: tiers, sources and label."""
    return dict(_table(_check_font(font)))


#: One-line description of how far the Preeti table can be trusted.
PREETI_LABEL: str = str(_table("preeti")["label"])


def _entries(table: dict[str, Any], section: str) -> dict[str, str]:
    payload = table.get(section, {})
    if not isinstance(payload, dict):
        raise ValueError(f"font table section {section!r} must be an object")
    return {str(key): str(entry["to"]) for key, entry in payload.items()}


@cache
def _maps(
    key: str, include_unconfirmed: bool, strict: bool
) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(single-key map, key-sequence map)`` for the chosen tiers."""
    table = _table(key)
    single = _entries(table, "mapping")
    sequences = _entries(table, "sequences")
    if not strict:
        single.update(_entries(table, "majority"))
    if include_unconfirmed:
        single.update(_entries(table, "unconfirmed"))
        sequences.update(_entries(table, "unconfirmed_sequences"))
    return single, sequences


def load_font_map(
    font: str = "preeti", *, include_unconfirmed: bool = False, strict: bool = False
) -> dict[str, str]:
    """Return the key-to-letter map for ``font``.

    By default: every entry that two table families agree on, including the
    few where a third table says something else. ``strict=True`` drops those
    few. ``include_unconfirmed=True`` adds entries only one family has.
    Entries the tables disagree on are never returned. The two stroke keys
    (``m`` and ``{``) are not letters and are not in the map.
    """
    single, _ = _maps(_check_font(font), include_unconfirmed, strict)
    return dict(single)


@cache
def _tiers(key: str) -> dict[str, str]:
    """Return which tier of the table each key or key sequence belongs to."""
    table = _table(key)
    tiers: dict[str, str] = {}
    for section, tier in (
        ("unconfirmed", "unconfirmed"),
        ("unconfirmed_sequences", "unconfirmed"),
        ("majority", "majority"),
        ("mapping", "agreed"),
        ("sequences", "agreed"),
    ):
        for entry in _entries(table, section):
            tiers[entry] = tier
    return tiers


@dataclass
class _Token:
    value: str
    offset: int
    key: str


def _is_carried_over(token: _Token) -> bool:
    """True for a token the ``m`` stroke may reach back across.

    The stroke is drawn on the base letter, so signs written after that
    letter, a subscript (``्र``, ``्य``) and a reph do not get in its way.
    """
    value = token.value
    if value == _REPH:
        return True
    if len(value) > 1 and value[0] == _VIRAMA:
        return True
    return bool(value) and all(_is_sign(ch) for ch in value)


def _tokenise(
    text: str, single: dict[str, str], sequences: dict[str, str], tiers: dict[str, str]
) -> tuple[list[_Token], list[UnmappedChar], list[str]]:
    """Split ``text`` into table entries.

    Returns the tokens, the characters with no entry, and for every input
    character what happened to it: a tier name, ``"unmapped"`` or
    ``"untouched"``.
    """
    strokes = {
        keys[0]: value
        for keys, value in sequences.items()
        if len(keys) == 2 and keys[1] == _STROKE_KEY
    }
    lengths = sorted({len(keys) for keys in sequences}, reverse=True)
    tokens: list[_Token] = []
    unmapped: list[UnmappedChar] = []
    kinds = ["untouched"] * len(text)
    i = 0
    while i < len(text):
        for length in lengths:
            chunk = text[i : i + length]
            if chunk in sequences:
                tokens.append(_Token(sequences[chunk], i, chunk))
                kinds[i : i + length] = [tiers.get(chunk, "agreed")] * length
                i += length
                break
        else:
            ch = text[i]
            if ch == _STROKE_KEY:
                target = None
                for token in reversed(tokens):
                    if _is_carried_over(token):
                        continue
                    if token.key in strokes:
                        target = token
                    break
                if target is None:
                    tokens.append(_Token(ch, i, ""))
                    unmapped.append(UnmappedChar(ch, i))
                    kinds[i] = "unmapped"
                else:
                    target.value = strokes[target.key]
                    target.key = target.key + _STROKE_KEY
                    kinds[i] = tiers.get(target.key, "agreed")
            elif ch == _REPH_KEY:
                tokens.append(_Token(_REPH, i, ch))
                kinds[i] = "agreed"
            elif ch in single:
                value = single[ch]
                tokens.append(_Token(_PRE_I if value == _SHORT_I else value, i, ch))
                kinds[i] = tiers.get(ch, "agreed")
            else:
                tokens.append(_Token(ch, i, ""))
                if not ch.isspace() and not _is_devanagari(ch):
                    unmapped.append(UnmappedChar(ch, i))
                    kinds[i] = "unmapped"
            i += 1
    return tokens, unmapped, kinds


def _units(tokens: list[_Token]) -> list[tuple[str, int]]:
    """Flatten tokens into ``(code point or marker, input offset)`` pairs."""
    units: list[tuple[str, int]] = []
    for token in tokens:
        if token.value in (_PRE_I, _REPH):
            units.append((token.value, token.offset))
        else:
            units.extend((ch, token.offset) for ch in token.value)
    return units


def _join_half_and_bar(units: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """A half form followed by the upright bar is the full letter."""
    out: list[tuple[str, int]] = []
    for unit in units:
        if unit[0] == _AA and out and out[-1][0] == _VIRAMA:
            out.pop()
            continue
        out.append(unit)
    return out


def _cluster_end(units: list[tuple[str, int]], start: int) -> int:
    """Return the index just past the consonant cluster starting at ``start``.

    A cluster is a consonant, an optional nukta, and any number of
    virama + consonant (+ nukta) after it. Returns ``start`` when no
    consonant is there.
    """
    n = len(units)
    if start >= n or not _is_consonant(units[start][0]):
        return start
    i = start + 1
    while True:
        if i < n and units[i][0] == _NUKTA:
            i += 1
        if i + 1 < n and units[i][0] == _VIRAMA and _is_consonant(units[i + 1][0]):
            i += 2
            continue
        return i


def _cluster_start(units: list[tuple[str, int]], end: int) -> int:
    """Return the index where the consonant cluster ending before ``end`` begins.

    Returns ``end`` when the unit before ``end`` is not the tail of a
    cluster. A lone independent vowel counts as a cluster of one, because
    Preeti writes ``ई`` as ``इ`` with a reph.
    """
    i = end
    if i > 0 and units[i - 1][0] == _NUKTA:
        i -= 1
    if i == 0:
        return end
    if _is_independent_vowel(units[i - 1][0]):
        return i - 1 if i == end else end
    if not _is_consonant(units[i - 1][0]):
        return end
    i -= 1
    while i >= 2 and units[i - 1][0] == _VIRAMA:
        j = i - 2
        if units[j][0] == _NUKTA and j >= 1:
            j -= 1
        if not _is_consonant(units[j][0]):
            break
        i = j
    return i


def _place_short_i(units: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Move each short-i typed before a cluster to just after that cluster."""
    out: list[tuple[str, int]] = []
    i = 0
    while i < len(units):
        ch, offset = units[i]
        if ch != _PRE_I:
            out.append(units[i])
            i += 1
            continue
        end = _cluster_end(units, i + 1)
        out.extend(units[i + 1 : end])
        out.append((_SHORT_I, offset))
        i = max(end, i + 1)
    return out


def _place_reph(
    units: list[tuple[str, int]], unmapped: list[UnmappedChar], kinds: list[str]
) -> list[tuple[str, int]]:
    """Move each reph typed after a syllable to before its consonant cluster."""
    out: list[tuple[str, int]] = []
    for ch, offset in units:
        if ch != _REPH:
            out.append((ch, offset))
            continue
        end = len(out)
        while end > 0 and _is_sign(out[end - 1][0]):
            end -= 1
        # A reph typed after a letter that ends in a halant (``र्क्``).
        if (
            end == len(out)
            and end >= 2
            and out[end - 1][0] == _VIRAMA
            and (_is_consonant(out[end - 2][0]) or out[end - 2][0] == _NUKTA)
        ):
            end -= 1
        start = _cluster_start(out, end)
        if start == end:
            out.append((_REPH_KEY, offset))
            unmapped.append(UnmappedChar(_REPH_KEY, offset))
            kinds[offset] = "unmapped"
            continue
        out[start:start] = [(_RA, offset), (_VIRAMA, offset)]
    return out


def _sign_rank(ch: str) -> int:
    if ch == _AA:
        return 0
    if _is_vowel_sign(ch):
        return 1
    if ch in _NASALS:
        return 2
    return 3


def _order_signs(units: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Within a run of signs: ``ा`` first, other vowel signs, nasal, visarga."""
    out: list[tuple[str, int]] = []
    i = 0
    while i < len(units):
        if not _is_sign(units[i][0]):
            out.append(units[i])
            i += 1
            continue
        j = i
        while j < len(units) and _is_sign(units[j][0]):
            j += 1
        out.extend(sorted(units[i:j], key=lambda unit: _sign_rank(unit[0])))
        i = j
    return out


def _join_dandas(units: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Two danda keys typed one straight after the other are a double danda."""
    out: list[tuple[str, int]] = []
    for ch, offset in units:
        if ch == _DANDA and out and out[-1] == (_DANDA, offset - 1):
            out[-1] = (_DOUBLE_DANDA, offset - 1)
            continue
        out.append((ch, offset))
    return out


def _loose_visarga(units: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """A visarga with no letter before it is a colon.

    The visarga belongs to the syllable before it. Typed after a space, a
    digit, a punctuation mark or at the very start it has no syllable, and
    in Preeti documents that key is what stands for a colon (``विषय :``,
    ``१०:३०``).
    """
    out: list[tuple[str, int]] = []
    for ch, offset in units:
        if ch == _VISARGA:
            before = out[-1][0] if out else ""
            if not before or not (_is_devanagari(before) and not _is_devanagari_digit(before)):
                out.append((":", offset))
                continue
        out.append((ch, offset))
    return out


# --- Protected stretches -----------------------------------------------------

# A web address: a scheme or "www." followed by printable ASCII. A Preeti
# document is ASCII too, so the address ends at white space, not at the first
# Devanagari letter.
_URL = re.compile(r"(?:https?://|www\.)[!-~]+", re.IGNORECASE)
# What may end a sentence or close a bracket after an address. "_" is the
# Preeti key for ")", so it is not taken as the end of the address either.
_URL_TAIL = ".,;:!?)]}'\"_"
# An e-mail address. "@" is also the Preeti key for the digit 2, so the part
# after it must look like a host name ending in two or more ASCII letters.
_EMAIL = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![A-Za-z0-9])"
)

Keep = str | re.Pattern[str]
# (start, end, start of the kept text, end of the kept text, reason)
_Span = tuple[int, int, int, int, str]


def _line_starts(text: str) -> list[int]:
    starts = [0]
    starts.extend(i + 1 for i, ch in enumerate(text) if ch == "\n")
    return starts


def _line_column(starts: list[int], offset: int) -> tuple[int, int]:
    line = bisect_right(starts, offset)
    return line, offset - starts[line - 1] + 1


def _as_patterns(keep: Keep | Iterable[Keep] | None) -> list[re.Pattern[str]]:
    if keep is None:
        return []
    items: Iterable[Keep] = [keep] if isinstance(keep, (str, re.Pattern)) else keep
    patterns: list[re.Pattern[str]] = []
    for item in items:
        if isinstance(item, re.Pattern):
            patterns.append(item)
            continue
        if not isinstance(item, str):
            raise TypeError("keep must be a pattern string, a compiled pattern or a list of them")
        try:
            patterns.append(re.compile(item))
        except re.error as error:
            raise ValueError(
                f"keep pattern {item!r} is not a valid regular expression: {error}"
            ) from error
    return patterns


def _check_markers(markers: tuple[str, str] | None) -> tuple[str, str] | None:
    if markers is None:
        return None
    if (
        len(markers) != 2
        or not all(isinstance(marker, str) for marker in markers)
        or not all(marker.strip() for marker in markers)
    ):
        raise ValueError("markers must be two non-empty strings: an opening and a closing one")
    return markers[0], markers[1]


def _protected_spans(
    text: str,
    keep_links: bool,
    keep: Keep | Iterable[Keep] | None,
    keep_words: Iterable[str] | None,
    markers: tuple[str, str] | None,
) -> list[_Span]:
    """Find the stretches to leave alone. They never overlap; first claim wins.

    Order of claims: marked text, ``keep`` patterns, ``keep_words``, then web
    and e-mail addresses.
    """
    candidates: list[_Span] = []
    pair = _check_markers(markers)
    if pair is not None:
        opening, closing = pair
        starts = _line_starts(text)
        i = text.find(opening)
        while i != -1:
            inner = i + len(opening)
            j = text.find(closing, inner)
            if j == -1:
                line, column = _line_column(starts, i)
                raise ValueError(
                    f"the marker {opening!r} at line {line}, column {column} is never "
                    f"closed with {closing!r}"
                )
            candidates.append((i, j + len(closing), inner, j, "marker"))
            i = text.find(opening, j + len(closing))
    for pattern in _as_patterns(keep):
        candidates.extend(
            (m.start(), m.end(), m.start(), m.end(), "keep")
            for m in pattern.finditer(text)
            if m.end() > m.start()
        )
    if keep_words is not None:
        if isinstance(keep_words, str):
            raise TypeError("keep_words must be a list of words, not a single string")
        for word in keep_words:
            if not isinstance(word, str) or not word:
                raise ValueError("keep_words must be non-empty strings")
            pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])")
            candidates.extend(
                (m.start(), m.end(), m.start(), m.end(), "word") for m in pattern.finditer(text)
            )
    if keep_links:
        for m in _URL.finditer(text):
            end = m.end()
            while end > m.start() and text[end - 1] in _URL_TAIL:
                end -= 1
            if end - m.start() > len("www."):
                candidates.append((m.start(), end, m.start(), end, "link"))
        candidates.extend(
            (m.start(), m.end(), m.start(), m.end(), "link") for m in _EMAIL.finditer(text)
        )
    claimed: list[_Span] = []
    starts_claimed: list[int] = []
    for span in candidates:
        at = bisect_right(starts_claimed, span[0])
        if at > 0 and claimed[at - 1][1] > span[0]:
            continue
        if at < len(claimed) and claimed[at][0] < span[1]:
            continue
        claimed.insert(at, span)
        starts_claimed.insert(at, span[0])
    return claimed


# --- Preeti to Unicode ---------------------------------------------------------


def _convert_plain(
    text: str, include_unconfirmed: bool, strict: bool, normalise: bool
) -> tuple[str, list[tuple[str, int, int]], list[str]]:
    """Convert one unprotected stretch.

    Returns the result, ``(char, input offset, output offset)`` for every
    unmapped character, and what happened to each input character.
    """
    single, sequences = _maps("preeti", include_unconfirmed, strict)
    tokens, unmapped, kinds = _tokenise(text, single, sequences, _tiers("preeti"))
    units = _units(tokens)
    units = _join_half_and_bar(units)
    units = _place_short_i(units)
    units = _place_reph(units, unmapped, kinds)
    units = _order_signs(units)
    units = _join_dandas(units)
    units = _loose_visarga(units)
    left_over = {item.offset for item in unmapped}
    parts: list[str] = []
    length = 0
    pending: list[str] = []
    where: dict[int, int] = {}

    def flush() -> None:
        nonlocal length
        if pending:
            piece = "".join(pending)
            if normalise:
                piece = normalize(piece, whitespace=False, danda=False)
            parts.append(piece)
            length += len(piece)
            pending.clear()

    # Unmapped characters are copied across as they are; only the converted
    # stretches between them are normalised. That keeps their place exact.
    for ch, offset in units:
        if offset in left_over and ch == text[offset]:
            flush()
            where[offset] = length
            parts.append(ch)
            length += len(ch)
        else:
            pending.append(ch)
    flush()
    found = [(item.char, item.offset, where[item.offset]) for item in unmapped]
    found.sort(key=lambda item: item[1])
    return "".join(parts), found, kinds


def _count(kinds: Iterable[str], protected: int) -> PreetiStats:
    counts = {"agreed": 0, "majority": 0, "unconfirmed": 0, "unmapped": 0, "untouched": 0}
    for kind in kinds:
        counts[kind] += 1
    return PreetiStats(protected=protected, **counts)


def convert_preeti(
    text: str,
    *,
    include_unconfirmed: bool = False,
    strict: bool = False,
    normalise: bool = True,
    keep_links: bool = True,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
    markers: tuple[str, str] | None = None,
) -> PreetiResult:
    """Convert Preeti-encoded ``text`` to Unicode and report what was left over.

    EXPERIMENTAL: the key table is agreed between permissively-licensed
    tables but has not been checked against real Preeti documents.

    ``include_unconfirmed`` also uses entries that only one table family
    has. ``strict`` leaves out the few entries where two families agree and
    a third table differs. ``normalise`` runs :func:`aksharkit.normalize`
    on the converted text (white space and danda are left alone), which
    composes ``ा`` + ``े`` into ``ो`` and repairs ``र्इ`` into ``ई``.

    Some stretches are left exactly as they are and listed in
    ``result.protected``:

    * ``keep_links`` (on by default): web addresses starting ``http://``,
      ``https://`` or ``www.``, and e-mail addresses;
    * ``keep``: a regular expression, or several; every match is left alone;
    * ``keep_words``: words to leave alone wherever they stand on their own
      (not next to another ASCII letter or digit);
    * ``markers``: an opening and a closing string, for example
      ``("[[", "]]")``. Text between them is left alone and the markers are
      removed. A marker that is opened and not closed is an error.

    No stretch is protected by guessing that it "looks English": plenty of
    Preeti words are made only of ASCII letters.

    Characters with no entry are passed through unchanged and listed in
    ``result.unmapped`` with their offset, line and column in the input and
    their offset in the result. White space and text that is already
    Devanagari pass through without being reported. ``result.stats`` counts
    the input characters by what happened to them.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    spans = _protected_spans(text, keep_links, keep, keep_words, markers)
    starts = _line_starts(text)
    parts: list[str] = []
    length = 0
    unmapped: list[UnmappedChar] = []
    protected: list[ProtectedSpan] = []
    kinds: list[str] = []
    protected_chars = 0

    def plain(start: int, end: int) -> None:
        nonlocal length
        if start == end:
            return
        piece, found, piece_kinds = _convert_plain(
            text[start:end], include_unconfirmed, strict, normalise
        )
        for ch, offset, out in found:
            line, column = _line_column(starts, start + offset)
            unmapped.append(UnmappedChar(ch, start + offset, line, column, length + out))
        kinds.extend(piece_kinds)
        parts.append(piece)
        length += len(piece)

    position = 0
    for start, end, inner_start, inner_end, reason in spans:
        plain(position, start)
        kept = text[inner_start:inner_end]
        protected.append(ProtectedSpan(start, end, kept, reason, length))
        protected_chars += end - start
        parts.append(kept)
        length += len(kept)
        position = end
    plain(position, len(text))
    return PreetiResult(
        "".join(parts), tuple(unmapped), tuple(protected), _count(kinds, protected_chars)
    )


def preeti_to_unicode(
    text: str,
    *,
    include_unconfirmed: bool = False,
    strict: bool = False,
    keep_links: bool = True,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
    markers: tuple[str, str] | None = None,
) -> str:
    """Convert Preeti-encoded ``text`` to Unicode. EXPERIMENTAL.

    Returns only the text; use :func:`convert_preeti` to also learn which
    characters had no agreed entry and were passed through unchanged.
    """
    return convert_preeti(
        text,
        include_unconfirmed=include_unconfirmed,
        strict=strict,
        keep_links=keep_links,
        keep=keep,
        keep_words=keep_words,
        markers=markers,
    ).text


def to_unicode(text: str, font: str = "preeti") -> str:
    """Convert legacy-font ``text`` to Unicode. Only Preeti is available."""
    _check_font(font)
    return preeti_to_unicode(text)


# --- Unicode to Preeti ---------------------------------------------------------

# Letters Preeti has no key of its own for, written as other letters.
_SPLIT_VOWELS = {
    "\u094b": "\u093e\u0947",  # ो = ा + े
    "\u094c": "\u093e\u0948",  # ौ = ा + ै
}
_VOWEL_KEYS_FROM = {
    "\u0906": "\u0905\u093e",  # आ = अ + ा
    "\u0910": "\u090f\u0947",  # ऐ = ए + े
    "\u0913": "\u0905\u093e\u0947",  # ओ = अ + ा + े
    "\u0914": "\u0905\u093e\u0948",  # औ = अ + ा + ै
}
_LONG_I = "\u0908"
_SHORT_I_VOWEL = "\u0907"
_SHORT_I_KEY = "l"
_RAKAR = _VIRAMA + _RA
# The second key for the ra stroke. The table has two keys for ``्र``; this
# one is used under the letters with a round foot and no upright bar.
_ROUND_RAKAR_KEY = "\u00ab"
_ROUND_LETTERS = frozenset("\u0919\u091b\u091f\u0920\u0921\u0922")  # ङ छ ट ठ ड ढ
_DOUBLE_DANDA_KEYS = ".."
_COLON_KEY = "M"

#: How ASCII digits are treated by :func:`encode_preeti`.
DIGIT_MODES: tuple[str, ...] = ("keep", "devanagari")
_ASCII_NUMBER = re.compile(r"(?<![A-Za-z0-9])[0-9]+(?![A-Za-z0-9])")
_TO_DEVANAGARI_DIGITS = {ord("0") + i: chr(0x0966 + i) for i in range(10)}
# Inside a Nepali word: an English word or an ASCII number, with the marks
# that hold such things together (3.5, 10:30, A-4, user@example).
_FOREIGN = re.compile(r"[A-Za-z0-9]+(?:[.,:/@_'+\-][A-Za-z0-9]+)*")


@dataclass(frozen=True)
class _Reverse:
    """The table read backwards: Unicode text to the key that writes it."""

    #: Text of any length to its key or keys.
    keys: dict[str, str]
    #: Consonant to the key of its half form.
    halves: dict[str, str]
    #: Longest text in ``keys``.
    longest: int
    #: Every character that can be written with some key.
    writable: frozenset[str]
    #: The key for ``्र`` under a round letter, when the table has it.
    round_rakar: str | None = None
    #: True when two danda keys read back as a double danda.
    double_danda: bool = False
    #: True when the visarga key reads back as a colon after a space or digit.
    colon: bool = False


def _key_rank(key: str, families: int) -> tuple[int, int, int, str]:
    """Order keys that write the same text; the rule is fixed, not learnt.

    More table families first, then a single key before a sequence, then an
    ASCII key, then the lower code point.
    """
    return (-families, len(key), 0 if key.isascii() else 1, key)


@cache
def _reverse(strict: bool, unconfirmed: bool = False) -> _Reverse:
    table = _table("preeti")
    best: dict[str, tuple[int, int, int, str]] = {}
    sections = ["mapping", "sequences"] if strict else ["mapping", "sequences", "majority"]
    if unconfirmed:
        sections += ["unconfirmed", "unconfirmed_sequences"]
    for section in sections:
        for key, entry in table.get(section, {}).items():
            value = str(entry["to"])
            families = len(entry.get("families", ())) if section == "mapping" else 1
            if section.startswith("unconfirmed"):
                # Last choice: only when nothing better writes the same text.
                families = 0
            rank = _key_rank(str(key), families)
            if value not in best or rank < best[value]:
                best[value] = rank
    keys = {value: rank[3] for value, rank in best.items()}
    halves = {
        value[0]: key
        for value, key in keys.items()
        if len(value) == 2 and value[1] == _VIRAMA and _is_consonant(value[0])
    }
    # A half form followed by the upright bar is the full letter. Three
    # letters have no key of their own and are written that way.
    for value, key in list(keys.items()):
        if len(value) >= 2 and value[-1] == _VIRAMA and value[:-1] not in keys:
            keys[value[:-1]] = key + keys[_AA]
    keys.pop(_SHORT_I, None)
    writable = set("".join(keys)) | {_SHORT_I, _LONG_I}
    writable.update(_SPLIT_VOWELS, _VOWEL_KEYS_FROM)
    single, _ = _maps("preeti", unconfirmed, strict)
    round_rakar = _ROUND_RAKAR_KEY if single.get(_ROUND_RAKAR_KEY) == _RAKAR else None
    double_danda = keys.get(_DANDA) == _DOUBLE_DANDA_KEYS[0]
    colon = keys.get(_VISARGA) == _COLON_KEY
    if double_danda:
        writable.add(_DOUBLE_DANDA)
    return _Reverse(
        keys,
        halves,
        max(len(value) for value in keys),
        frozenset(writable),
        round_rakar,
        double_danda,
        colon,
    )


def _encode_cluster(body: str, rev: _Reverse) -> list[tuple[str, str]]:
    """Write a consonant cluster as ``(text, keys)`` pairs.

    Longest table entry first (``द्ध``, ``क्ष्``, ``त्र``). Otherwise a letter
    before another letter is its half form when it has one, except before
    ``र``, which is written as the full letter and the ``्र`` stroke. Under
    a letter with a round foot the stroke is the table's second ``्र`` key.
    """
    out: list[tuple[str, str]] = []
    i = 0
    n = len(body)
    last = ""
    while i < n:
        matched = False
        for length in range(min(rev.longest, n - i), 2, -1):
            chunk = body[i : i + length]
            if chunk in rev.keys and _is_consonant(chunk[0]):
                out.append((chunk, rev.keys[chunk]))
                i += length
                last = chunk[-1] if _is_consonant(chunk[-1]) else ""
                matched = True
                break
        if matched:
            continue
        ch = body[i]
        if ch == _VIRAMA:
            tail = body[i : i + 2]
            if tail == _RAKAR and last in _ROUND_LETTERS and rev.round_rakar:
                out.append((tail, rev.round_rakar))
                i += 2
            elif len(tail) == 2 and tail in rev.keys:
                out.append((tail, rev.keys[tail]))
                i += 2
            else:
                out.append((ch, rev.keys[_VIRAMA]))
                i += 1
            last = ""
            continue
        if i + 1 < n and body[i + 1] == _NUKTA:
            # A nukta letter is written only when the table has it whole.
            out.append((body[i : i + 2], rev.keys[body[i : i + 2]]))
            i += 2
            last = ""
            continue
        after = body[i + 2] if i + 2 < n and body[i + 1] == _VIRAMA else ""
        if after and after != _RA and ch in rev.halves:
            out.append((ch + _VIRAMA, rev.halves[ch]))
            i += 2
            last = ""
        else:
            out.append((ch, rev.keys[ch]))
            i += 1
            last = ch
    return out


def _sign_keys(signs: Iterable[str], rev: _Reverse) -> list[str]:
    return [_SHORT_I_KEY if sign == _SHORT_I else rev.keys[sign] for sign in signs]


def _colon_fits(before: str) -> bool:
    """True where the visarga key reads back as a colon: not after a letter."""
    return not before or not (_is_devanagari(before) and not _is_devanagari_digit(before))


def _encode_piece(piece: str, rev: _Reverse) -> str:
    """Write a stretch of writable characters as Preeti keys, in typing order.

    Raises ``KeyError`` when a character turns out to have no key.
    """
    out: list[str] = []
    i = 0
    n = len(piece)
    while i < n:
        ch = piece[i]
        reph = False
        if ch == _RA and i + 2 < n and piece[i + 1] == _VIRAMA and _is_consonant(piece[i + 2]):
            reph = True
            i += 2
            ch = piece[i]
        body: list[tuple[str, str]]
        if _is_consonant(ch):
            j = i + 1
            if j < n and piece[j] == _NUKTA:
                j += 1
            while j + 1 < n and piece[j] == _VIRAMA and _is_consonant(piece[j + 1]):
                j += 2
                if j < n and piece[j] == _NUKTA:
                    j += 1
            if j < n and piece[j] == _VIRAMA:
                j += 1
            body = _encode_cluster(piece[i:j], rev)
            i = j
        elif _is_independent_vowel(ch):
            spelt = _VOWEL_KEYS_FROM.get(ch, _SHORT_I_VOWEL if ch == _LONG_I else ch)
            body = [(spelt[0], rev.keys[spelt[0]])]
            body.extend((sign, rev.keys[sign]) for sign in spelt[1:])
            reph = ch == _LONG_I
            i += 1
        elif ch == _DOUBLE_DANDA:
            if not rev.double_danda:
                raise KeyError(ch)
            out.append(_DOUBLE_DANDA_KEYS)
            i += 1
            continue
        elif ch == ":":
            if not rev.colon or not _colon_fits(piece[i - 1] if i else ""):
                raise KeyError(ch)
            out.append(_COLON_KEY)
            i += 1
            continue
        else:
            # A sign with no letter before it, a digit, a punctuation mark.
            out.extend(_sign_keys(_SPLIT_VOWELS.get(ch, ch), rev))
            i += 1
            continue
        signs: list[str] = []
        while i < n and _is_sign(piece[i]):
            signs.extend(_SPLIT_VOWELS.get(piece[i], piece[i]))
            i += 1
        vowels = [sign for sign in signs if _is_vowel_sign(sign)]
        others = [sign for sign in signs if not _is_vowel_sign(sign)]
        pre_i = _SHORT_I in vowels
        if pre_i:
            vowels.remove(_SHORT_I)
        # A letter and its sign drawn as one shape (रु, रू, हृ) have a key.
        if vowels and len(body[-1][0]) == 1 and (body[-1][0] + vowels[0]) in rev.keys:
            joined = body.pop()[0] + vowels.pop(0)
            body.append((joined, rev.keys[joined]))
        if pre_i:
            out.append(_SHORT_I_KEY)
        out.extend(keys for _, keys in body)
        out.extend(_sign_keys(vowels, rev))
        if reph:
            out.append(_REPH_KEY)
        out.extend(_sign_keys(others, rev))
    return "".join(out)


def _reads_back(keys: str, expected: str, strict: bool, unconfirmed: bool = False) -> bool:
    back = convert_preeti(keys, strict=strict, include_unconfirmed=unconfirmed, keep_links=False)
    return not back.unmapped and back.text == expected


@lru_cache(maxsize=65536)
def _encode_checked(piece: str, strict: bool, unconfirmed: bool = False) -> str | None:
    """Write ``piece`` as keys, or None when the keys do not convert back to it."""
    try:
        keys = _encode_piece(piece, _reverse(strict, unconfirmed))
    except KeyError:
        return None
    return keys if _reads_back(keys, piece, strict, unconfirmed) else None


def _can_write(text: str, i: int, rev: _Reverse) -> bool:
    """True when the character at ``i`` has a key where it stands."""
    ch = text[i]
    if ch == ":":
        return rev.colon and _colon_fits(text[i - 1] if i else "")
    return ch in rev.writable


def _encode_word(chunk: str, rev: _Reverse, strict: bool, unconfirmed: bool) -> str | None:
    """Write a word that holds unwritable Devanagari characters, checked whole.

    Such characters pass through both directions untouched, so the whole
    word can be converted back and compared. Returns None when it differs.
    """
    pieces: list[str] = []
    i = 0
    while i < len(chunk):
        if not _can_write(chunk, i, rev):
            pieces.append(chunk[i])
            i += 1
            continue
        j = i
        while j < len(chunk) and _can_write(chunk, j, rev):
            j += 1
        try:
            pieces.append(_encode_piece(chunk[i:j], rev))
        except KeyError:
            return None
        i = j
    whole = "".join(pieces)
    back = convert_preeti(whole, strict=strict, include_unconfirmed=unconfirmed, keep_links=False)
    return whole if back.text == chunk and not back.unmapped else None


def _has_devanagari_letter(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def encode_preeti(
    text: str,
    *,
    strict: bool = False,
    include_unconfirmed: bool = False,
    normalise: bool = True,
    keep_links: bool = True,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
    markers: tuple[str, str] | None = None,
    digits: str = "keep",
    whole_words: bool = False,
    mark_kept: tuple[str, str] | None = None,
) -> PreetiEncodeResult:
    """Write Unicode ``text`` as Preeti key codes and report what was left over.

    EXPERIMENTAL, like the table it reads backwards. What is promised and
    tested:

    * every stretch written as keys converts back, with
      :func:`convert_preeti`, to exactly the text it came from; a word whose
      keys do not is left in Unicode and listed in ``result.skipped``;
    * a character of a Nepali word with no key in the table (a hyphen, a
      nukta, ``ॉ``, a joiner, ...) is left as it is and listed in
      ``result.unmapped``; no near-enough key is chosen for it;
    * text with no Devanagari in it (an English word, an ASCII number, a web
      address) is not Nepali and is left alone; it is listed in
      ``result.foreign`` and is not counted as a failure;
    * with ``mark_kept``, ``convert_preeti(result.text, markers=mark_kept,
      keep_links=False).text`` equals the normalised input, always; without
      it the same holds when nothing was skipped, protected or foreign and
      every unmapped character is a Devanagari one.

    What is **not** promised: that the keys look right in the Preeti font.
    Where several keys write the same letter, one is chosen by a fixed rule,
    not by what a typist would press, and nobody has looked at the result in
    the font.

    Options:

    * ``strict`` uses only keys that every table family agrees on.
    * ``include_unconfirmed`` also uses keys only one table family has. It
      adds ``ड़``, ``ढ़`` and ``ॅ``; the result then reads back only with
      ``convert_preeti(..., include_unconfirmed=True)``.
    * ``digits``: ``"keep"`` leaves ASCII digits alone. ``"devanagari"``
      first rewrites every ASCII number on a line that has Devanagari on it
      (and is not part of an English word) in Devanagari digits, which have
      keys. That changes the text: it reads back with Devanagari digits.
    * ``whole_words``: a word holding a Devanagari character with no key is
      left in Unicode whole, instead of key codes round the one character.
    * ``mark_kept``: an opening and a closing string put round everything
      that was left as it was, so that plain text survives the round trip.
      Raises ``ValueError`` when the markers occur in the text.
    * ``normalise`` first runs :func:`aksharkit.normalize` on the text (white
      space and danda are left alone); offsets, lines and columns in the
      result refer to that normalised text.
    * The ``keep`` options work as in :func:`convert_preeti`.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if digits not in DIGIT_MODES:
        raise ValueError(f"digits must be one of {', '.join(DIGIT_MODES)}; got {digits!r}")
    pair = _check_markers(mark_kept)
    if normalise:
        text = normalize(text, whitespace=False, danda=False)
    if pair is not None and (pair[0] in text or pair[1] in text):
        raise ValueError(
            f"the mark_kept markers {pair[0]!r} and {pair[1]!r} occur in the text; choose others"
        )
    rev = _reverse(strict, include_unconfirmed)
    spans = _protected_spans(text, keep_links, keep, keep_words, markers)
    if digits == "devanagari":
        text = _rewrite_digits(text, spans)
    starts = _line_starts(text)
    segments: list[PreetiSegment] = []
    unmapped: list[UnmappedChar] = []
    skipped: list[SkippedSpan] = []
    foreign: list[ForeignSpan] = []
    protected: list[ProtectedSpan] = []
    words = 0
    words_encoded = 0
    length = 0

    def emit(start: int, end: int, piece: str, kind: str) -> None:
        nonlocal length
        if start == end:
            return
        segments.append(PreetiSegment(start, end, piece, kind))
        length += len(piece)

    def report(index: int, offset: int) -> None:
        line, column = _line_column(starts, index)
        unmapped.append(UnmappedChar(text[index], index, line, column, offset))

    def skip(start: int, end: int) -> None:
        line, column = _line_column(starts, start)
        skipped.append(SkippedSpan(start, end, text[start:end], line, column, length))
        emit(start, end, text[start:end], "skipped")

    def leave(start: int, end: int) -> None:
        line, column = _line_column(starts, start)
        foreign.append(ForeignSpan(start, end, text[start:end], line, column, length))
        emit(start, end, text[start:end], "foreign")

    def native(start: int, end: int) -> bool:
        """Write a stretch of Devanagari and marks. True when all of it became keys."""
        whole = True
        i = start
        while i < end:
            if not _can_write(text, i, rev) and not _is_devanagari(text[i]):
                report(i, length)
                emit(i, i + 1, text[i], "unmapped")
                whole = False
                i += 1
                continue
            j = i
            while j < end and (_can_write(text, j, rev) or _is_devanagari(text[j])):
                j += 1
            chunk = text[i:j]
            left = [k for k in range(i, j) if not _can_write(text, k, rev)]
            if not left:
                keys = _encode_checked(chunk, strict, include_unconfirmed)
                if keys is None:
                    skip(i, j)
                    whole = False
                else:
                    emit(i, j, keys, "keys")
            elif whole_words or pair is not None:
                for k in left:
                    report(k, length + k - i)
                emit(i, j, chunk, "unmapped")
                whole = False
            elif _encode_word(chunk, rev, strict, include_unconfirmed) is None:
                skip(i, j)
                whole = False
            else:
                whole = False
                k = i
                while k < j:
                    if not _can_write(text, k, rev):
                        report(k, length)
                        emit(k, k + 1, text[k], "unmapped")
                        k += 1
                        continue
                    m = k
                    while m < j and _can_write(text, m, rev):
                        m += 1
                    # Already checked as part of the whole word.
                    emit(k, m, _encode_piece(text[k:m], rev), "keys")
                    k = m
            i = j
        return whole

    def plain(start: int, end: int) -> None:
        nonlocal words, words_encoded
        tokens = [(m.start() + start, m.end() + start) for m in _TOKEN.finditer(text[start:end])]
        nepali = [_has_devanagari_letter(text[a:b]) for a, b in tokens]
        position = start
        for index, (a, b) in enumerate(tokens):
            emit(position, a, text[position:a], "space")
            position = b
            if nepali[index]:
                words += 1
                whole = True
                at = a
                for match in _FOREIGN.finditer(text, a, b):
                    whole = native(at, match.start()) and whole
                    leave(match.start(), match.end())
                    at = match.end()
                whole = native(at, b) and whole
                words_encoded += whole
                continue
            beside = (index > 0 and nepali[index - 1]) or (
                index + 1 < len(tokens) and nepali[index + 1]
            )
            keys = None
            if beside and all(_can_write(text, k, rev) for k in range(a, b)):
                keys = _encode_checked(text[a:b], strict, include_unconfirmed)
            if keys is None:
                leave(a, b)
            else:
                emit(a, b, keys, "keys")
        emit(position, end, text[position:end], "space")

    position = 0
    for start, end, inner_start, inner_end, reason in spans:
        plain(position, start)
        kept = text[inner_start:inner_end]
        protected.append(ProtectedSpan(start, end, kept, reason, length))
        emit(start, end, kept, "protected")
        position = end
    plain(position, len(text))

    counts = dict.fromkeys(("keys", "unmapped", "skipped", "foreign", "protected"), 0)
    for segment in segments:
        if segment.kind != "space":
            counts[segment.kind] += segment.end - segment.start
    stats = PreetiEncodeStats(
        words,
        words_encoded,
        counts["keys"],
        counts["unmapped"],
        counts["skipped"],
        counts["foreign"],
        counts["protected"],
    )
    if pair is None:
        result = "".join(segment.text for segment in segments)
        if (
            not skipped
            and not protected
            and not foreign
            and all(_is_devanagari(item.char) for item in unmapped)
            and convert_preeti(
                result, strict=strict, include_unconfirmed=include_unconfirmed, keep_links=False
            ).text
            != text
        ):
            # Should not happen: every word was checked on its own. Rather
            # than hand back keys that read differently, hand back the text.
            whole_span = SkippedSpan(0, len(text), text, 1, 1, 0)
            return PreetiEncodeResult(
                text,
                (),
                (whole_span,),
                segments=(PreetiSegment(0, len(text), text, "skipped"),),
                stats=PreetiEncodeStats(words, 0, 0, 0, len(text), 0, 0),
            )
    else:
        result = _with_marks(segments, pair)
        back = convert_preeti(
            result,
            strict=strict,
            include_unconfirmed=include_unconfirmed,
            keep_links=False,
            markers=pair,
        )
        if back.text != text:
            raise ValueError(
                f"the mark_kept markers {pair[0]!r} and {pair[1]!r} clash with the key codes "
                "of this text; choose others"
            )
    return PreetiEncodeResult(
        result,
        tuple(unmapped),
        tuple(skipped),
        tuple(protected),
        counts["keys"],
        tuple(foreign),
        tuple(segments),
        stats,
        pair,
    )


_TOKEN = re.compile(r"\S+")


def _rewrite_digits(text: str, spans: list[_Span]) -> str:
    """Rewrite ASCII numbers in Devanagari digits on lines that hold Devanagari.

    Protected stretches and numbers that touch an ASCII letter are left
    alone. The text keeps its length, so offsets stay true.
    """
    chars = list(text)
    shielded = [False] * len(text)
    for start, end, _, _, _ in spans:
        shielded[start:end] = [True] * (end - start)
    offset = 0
    for line in text.split("\n"):
        if _has_devanagari_letter(line):
            for match in _ASCII_NUMBER.finditer(line):
                a, b = offset + match.start(), offset + match.end()
                if not any(shielded[a:b]):
                    chars[a:b] = match.group().translate(_TO_DEVANAGARI_DIGITS)
        offset += len(line) + 1
    return "".join(chars)


def _with_marks(segments: Iterable[PreetiSegment], pair: tuple[str, str]) -> str:
    """Join the segments, with the markers round each kept stretch."""
    out: list[str] = []
    open_now = False
    for segment in segments:
        kept = segment.kind not in ("keys", "space")
        if kept and not open_now:
            out.append(pair[0])
        elif not kept and open_now:
            out.append(pair[1])
        open_now = kept
        out.append(segment.text)
    if open_now:
        out.append(pair[1])
    return "".join(out)


def unicode_to_preeti(text: str, *, strict: bool = False, include_unconfirmed: bool = False) -> str:
    """Write Unicode ``text`` as Preeti key codes. EXPERIMENTAL.

    Returns only the keys. Characters with no key, words whose keys do not
    convert back exactly, and text that is not Devanagari are left as they
    are; use :func:`encode_preeti` to learn which.
    """
    return encode_preeti(text, strict=strict, include_unconfirmed=include_unconfirmed).text
