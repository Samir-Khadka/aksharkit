"""Legacy (pre-Unicode) Nepali font conversion: Preeti to Unicode. EXPERIMENTAL.

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
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any

from ._data import load_table
from .normalize import normalize

__all__ = [
    "PREETI_LABEL",
    "SUPPORTED_FONTS",
    "PreetiResult",
    "UnmappedChar",
    "convert_preeti",
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


def _is_devanagari(ch: str) -> bool:
    return "\u0900" <= ch <= "\u097f" or ch in "\u200c\u200d"


@dataclass(frozen=True)
class UnmappedChar:
    """A character of the input that had no agreed table entry."""

    char: str
    #: Index of the character in the input string.
    offset: int


@dataclass(frozen=True)
class PreetiResult:
    """The outcome of a Preeti conversion."""

    #: The converted text. Unmapped characters are in it unchanged.
    text: str
    #: Every input character that was passed through for want of an entry.
    unmapped: tuple[UnmappedChar, ...]

    @property
    def complete(self) -> bool:
        """True when every character had an agreed entry."""
        return not self.unmapped

    @property
    def unmapped_chars(self) -> tuple[str, ...]:
        """The distinct unmapped characters, in order of first appearance."""
        return tuple(dict.fromkeys(item.char for item in self.unmapped))


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
    text: str, single: dict[str, str], sequences: dict[str, str]
) -> tuple[list[_Token], list[UnmappedChar]]:
    strokes = {
        keys[0]: value
        for keys, value in sequences.items()
        if len(keys) == 2 and keys[1] == _STROKE_KEY
    }
    lengths = sorted({len(keys) for keys in sequences}, reverse=True)
    tokens: list[_Token] = []
    unmapped: list[UnmappedChar] = []
    i = 0
    while i < len(text):
        for length in lengths:
            chunk = text[i : i + length]
            if chunk in sequences:
                tokens.append(_Token(sequences[chunk], i, chunk))
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
                else:
                    target.value = strokes[target.key]
                    target.key = target.key + _STROKE_KEY
            elif ch == _REPH_KEY:
                tokens.append(_Token(_REPH, i, ch))
            elif ch in single:
                value = single[ch]
                tokens.append(_Token(_PRE_I if value == _SHORT_I else value, i, ch))
            else:
                tokens.append(_Token(ch, i, ""))
                if not ch.isspace() and not _is_devanagari(ch):
                    unmapped.append(UnmappedChar(ch, i))
            i += 1
    return tokens, unmapped


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
    units: list[tuple[str, int]], unmapped: list[UnmappedChar]
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
        start = _cluster_start(out, end)
        if start == end:
            out.append((_REPH_KEY, offset))
            unmapped.append(UnmappedChar(_REPH_KEY, offset))
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


def convert_preeti(
    text: str,
    *,
    include_unconfirmed: bool = False,
    strict: bool = False,
    normalise: bool = True,
) -> PreetiResult:
    """Convert Preeti-encoded ``text`` to Unicode and report what was left over.

    EXPERIMENTAL: the key table is agreed between permissively-licensed
    tables but has not been checked against real Preeti documents.

    ``include_unconfirmed`` also uses entries that only one table family
    has. ``strict`` leaves out the few entries where two families agree and
    a third table differs. ``normalise`` runs :func:`aksharkit.normalize`
    on the result (white space and danda are left alone), which composes
    ``ा`` + ``े`` into ``ो`` and repairs ``र्इ`` into ``ई``.

    Characters with no entry are passed through unchanged and listed in
    ``result.unmapped`` with their position in the input. White space and
    text that is already Devanagari pass through without being reported.
    """
    single, sequences = _maps("preeti", include_unconfirmed, strict)
    tokens, unmapped = _tokenise(text, single, sequences)
    units = _units(tokens)
    units = _join_half_and_bar(units)
    units = _place_short_i(units)
    units = _place_reph(units, unmapped)
    units = _order_signs(units)
    result = "".join(ch for ch, _ in units)
    if normalise:
        result = normalize(result, whitespace=False, danda=False)
    unmapped.sort(key=lambda item: item.offset)
    return PreetiResult(result, tuple(unmapped))


def preeti_to_unicode(text: str, *, include_unconfirmed: bool = False, strict: bool = False) -> str:
    """Convert Preeti-encoded ``text`` to Unicode. EXPERIMENTAL.

    Returns only the text; use :func:`convert_preeti` to also learn which
    characters had no agreed entry and were passed through unchanged.
    """
    return convert_preeti(text, include_unconfirmed=include_unconfirmed, strict=strict).text


def to_unicode(text: str, font: str = "preeti") -> str:
    """Convert legacy-font ``text`` to Unicode. Only Preeti is available."""
    _check_font(font)
    return preeti_to_unicode(text)


def unicode_to_preeti(text: str) -> str:
    """Convert Unicode ``text`` to Preeti key codes. Not implemented.

    The reverse direction needs choices the table does not settle (which of
    several keys to use for a conjunct, when to use a half form) and has no
    real documents to be tested against, so it is left out for now.
    """
    raise NotImplementedError("Unicode to Preeti conversion is not implemented")
