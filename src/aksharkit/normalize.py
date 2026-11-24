"""Unicode normalisation for Devanagari (Nepali) text.

The goal is one canonical representation for text that *looks* identical, so
that searching, comparing and tokenising behave. Nothing here changes
spelling or meaning; every step is described in ``docs/normalisation.md``.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "ZWJ",
    "ZWNJ",
    "collapse_duplicate_marks",
    "compose_split_vowels",
    "fix_danda",
    "fix_joiners",
    "normalize",
    "normalize_whitespace",
    "repair_reph_i",
    "strip_invisible",
]

ZWJ = "\u200d"
ZWNJ = "\u200c"
_VIRAMA = "\u094d"
_DANDA = "\u0964"
_DOUBLE_DANDA = "\u0965"

_JOINER_POLICIES = ("safe", "strip", "keep")

# Sequences that render like a single vowel but are encoded as two code
# points. The Unicode Standard (Devanagari chapter) lists these as sequences
# that should not be used; NFC does not repair them, so we do.
_SPLIT_VOWELS: tuple[tuple[str, str], ...] = (
    ("\u0905\u093e", "\u0906"),  # अ + ा  -> आ
    ("\u0905\u094b", "\u0913"),  # अ + ो  -> ओ
    ("\u0905\u094c", "\u0914"),  # अ + ौ  -> औ
    ("\u0906\u0947", "\u0913"),  # आ + े  -> ओ
    ("\u0906\u0948", "\u0914"),  # आ + ै  -> औ
    ("\u090f\u0947", "\u0910"),  # ए + े  -> ऐ
    ("\u0909\u0941", "\u090a"),  # उ + ु  -> ऊ
    ("\u093e\u0947", "\u094b"),  # ा + े  -> ो
    ("\u093e\u0948", "\u094c"),  # ा + ै  -> ौ
    ("\u093e\u0945", "\u0949"),  # ा + ॅ  -> ॉ
)

# ``ई`` typed the typewriter way, as ``इ`` with a reph: र + virama + इ. A
# virama before an independent vowel does not make a conjunct, so the
# sequence has no reading of its own; it only looks like ``ई``. It is left
# alone when the र is itself the tail of a conjunct (``क्र्इ``, which shows no
# reph), and a joiner between the virama and the इ also keeps it apart.
_REPH_I = re.compile("(?<!\u094d)(?<!\u094d[\u200c\u200d])\u0930\u094d\u0907")

# Combining signs that never legitimately repeat: candrabindu, anusvara,
# visarga, nukta, dependent vowels, virama, stress marks. Avagraha (U+093D)
# is a letter and may repeat, so it is excluded.
_DUPLICATE_MARK = re.compile(
    "([\u0900-\u0903\u093a-\u093c\u093e-\u094f\u0951-\u0957\u0962\u0963])\\1+"
)

_DEVANAGARI_BEFORE_PIPE = "\u0900-\u0963\u0966-\u096f\u0970-\u097f"
_DOUBLE_PIPE = re.compile(f"([{_DEVANAGARI_BEFORE_PIPE}][ \t]*)\\|\\|(?=\\s|$)")
_SINGLE_PIPE = re.compile(f"([{_DEVANAGARI_BEFORE_PIPE}][ \t]*)\\|(?=\\s|$)")
_TWO_DANDAS = re.compile(f"{_DANDA}{_DANDA}")

_INVISIBLE = re.compile("[\u200b\u2060\ufeff\u00ad]")
_SPACE_LIKE = re.compile("[\t\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]")
_SPACE_RUN = re.compile(" {2,}")
_TRAILING_SPACE = re.compile(" +(?=\n)")


def _is_devanagari_letter(ch: str) -> bool:
    return "\u0904" <= ch <= "\u0939" or "\u0958" <= ch <= "\u0961" or "\u0972" <= ch <= "\u097f"


def compose_split_vowels(text: str) -> str:
    """Replace two-code-point look-alike vowels with the single code point."""
    for wrong, right in _SPLIT_VOWELS:
        if wrong in text:
            text = text.replace(wrong, right)
    return text


def repair_reph_i(text: str) -> str:
    """Replace ``र्इ`` (reph on ``इ``, an old way of typing ``ई``) with ``ई``."""
    if "\u094d\u0907" not in text:
        return text
    return _REPH_I.sub("\u0908", text)


def collapse_duplicate_marks(text: str) -> str:
    """Collapse an immediately repeated combining sign (``िि`` -> ``ि``)."""
    return _DUPLICATE_MARK.sub(r"\1", text)


def fix_joiners(text: str, policy: str = "safe") -> str:
    """Handle ZERO WIDTH JOINER / NON-JOINER.

    ``"safe"`` (default) keeps a single joiner that sits between a virama and
    a following Devanagari letter, because there it controls rendering
    (``र्‍य`` eyelash ra, explicit half forms, explicit halant). Every other
    joiner is stray and is removed. ``"strip"`` removes all joiners;
    ``"keep"`` leaves the text untouched.
    """
    if policy not in _JOINER_POLICIES:
        raise ValueError(f"unknown joiner policy {policy!r}; use one of {_JOINER_POLICIES}")
    if policy == "keep" or (ZWJ not in text and ZWNJ not in text):
        return text
    out: list[str] = []
    last = len(text) - 1
    for i, ch in enumerate(text):
        if ch in (ZWJ, ZWNJ):
            meaningful = (
                policy == "safe"
                and bool(out)
                and out[-1] == _VIRAMA
                and i < last
                and _is_devanagari_letter(text[i + 1])
            )
            if meaningful:
                out.append(ch)
            continue
        out.append(ch)
    return "".join(out)


def fix_danda(text: str) -> str:
    """Turn ASCII stand-ins into real dandas.

    ``|`` directly after Devanagari text (and before whitespace or the end)
    becomes ``।``; ``||`` and ``।।`` become ``॥``. A pipe anywhere else, for
    example in ``a | b`` or shell text, is left alone.
    """
    if "|" in text:
        text = _DOUBLE_PIPE.sub(f"\\1{_DOUBLE_DANDA}", text)
        text = _SINGLE_PIPE.sub(f"\\1{_DANDA}", text)
    if _DANDA in text:
        text = _TWO_DANDAS.sub(_DOUBLE_DANDA, text)
    return text


def strip_invisible(text: str) -> str:
    """Remove zero-width space, word joiner, BOM and soft hyphen."""
    return _INVISIBLE.sub("", text)


def normalize_whitespace(text: str) -> str:
    """Remove invisible characters and tidy spaces without joining lines."""
    text = strip_invisible(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _SPACE_LIKE.sub(" ", text)
    text = _SPACE_RUN.sub(" ", text)
    text = _TRAILING_SPACE.sub("", text)
    return text.strip()


def normalize(
    text: str,
    *,
    joiners: str = "safe",
    danda: bool = True,
    whitespace: bool = True,
) -> str:
    """Return ``text`` in aksharkit's canonical form.

    Steps, in order: joiner policy; invisible characters; NFC; split-vowel
    repair; ``र्इ`` to ``ई``; duplicate combining signs; whitespace; danda repair. Stray
    characters are removed first so that they cannot hide a sequence from
    the later steps. The function is idempotent:
    ``normalize(normalize(x)) == normalize(x)``.

    Note that NFC *decomposes* the precomposed nukta letters U+0958-U+095F
    (``क़`` and friends) into base letter + nukta, because Unicode excludes
    them from composition. That is the canonical form and is what you get.
    """
    text = fix_joiners(text, joiners)
    if whitespace:
        text = strip_invisible(text)
    text = unicodedata.normalize("NFC", text)
    text = compose_split_vowels(text)
    text = repair_reph_i(text)
    text = collapse_duplicate_marks(text)
    if whitespace:
        text = normalize_whitespace(text)
    if danda:
        text = fix_danda(text)
    return text
