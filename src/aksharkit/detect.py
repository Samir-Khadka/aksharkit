"""Which script a piece of text is written in.

Everything here looks at Unicode code points only. It tells Devanagari from
Latin letters and from digits; it does **not** identify a language. Nepali,
Hindi, Marathi, Maithili and Sanskrit all use Devanagari and all come out as
``"devanagari"``.

:func:`looks_romanised_nepali` is a separate, rough heuristic for Nepali typed
in Latin letters. It counts words from a short hand-written list and is easy
to fool; read its docstring before relying on it.
"""

from __future__ import annotations

import unicodedata

from .tokens import tokenize_spans

__all__ = [
    "ROMANISED_NEPALI_WORDS",
    "SCRIPTS",
    "char_script",
    "detect_script",
    "looks_romanised_nepali",
    "romanised_nepali_score",
    "script_counts",
    "script_shares",
    "token_scripts",
]

#: The classes a character can be counted under, in reporting order.
SCRIPTS: tuple[str, ...] = ("devanagari", "latin", "digit", "other")

_DANDAS = frozenset("\u0964\u0965")


def char_script(char: str) -> str | None:
    """Classify one character.

    Returns ``"devanagari"``, ``"latin"``, ``"digit"``, ``"other"`` (a letter
    of any other script) or ``None`` for characters that carry no script:
    spaces, punctuation, symbols, joiners and combining marks outside
    Devanagari. The danda (``।``, ``॥``) counts as punctuation. ASCII and
    Devanagari digits are both ``"digit"``.
    """
    if not isinstance(char, str) or len(char) != 1:
        raise TypeError("char_script expects a single character")
    code = ord(char)
    if 0x30 <= code <= 0x39 or 0x0966 <= code <= 0x096F:
        return "digit"
    if char in _DANDAS:
        return None
    if 0x0900 <= code <= 0x097F or 0xA8E0 <= code <= 0xA8FF:
        # Signs and matras count: they are part of the written word.
        return "devanagari" if unicodedata.category(char)[0] in "LM" else None
    if not char.isalpha():
        return "digit" if char.isdigit() else None
    if (
        code < 0x80
        or (0xC0 <= code <= 0x24F)
        or (0x1E00 <= code <= 0x1EFF)
        or unicodedata.name(char, "").startswith("LATIN")
    ):
        return "latin"
    return "other"


def script_counts(text: str) -> dict[str, int]:
    """Count the characters of each class in :data:`SCRIPTS`.

    Characters with no script (see :func:`char_script`) are not counted.
    """
    counts = dict.fromkeys(SCRIPTS, 0)
    for char in text:
        script = char_script(char)
        if script is not None:
            counts[script] += 1
    return counts


def script_shares(text: str) -> dict[str, float]:
    """Share of each class among the counted characters, from 0.0 to 1.0.

    The shares add up to 1.0, or are all 0.0 when nothing was counted.
    """
    counts = script_counts(text)
    total = sum(counts.values())
    if total == 0:
        return dict.fromkeys(SCRIPTS, 0.0)
    return {script: count / total for script, count in counts.items()}


def detect_script(text: str) -> str:
    """Name the script of ``text``.

    * ``"devanagari"``, ``"latin"`` or ``"other"`` when all letters belong to
      that one class. Digits next to letters do not change the answer.
    * ``"mixed"`` when letters of more than one class are present.
    * ``"digits"`` when there are digits and no letters.
    * ``"none"`` when there is nothing to classify (empty, spaces,
      punctuation, emoji).
    """
    counts = script_counts(text)
    letters = [script for script in ("devanagari", "latin", "other") if counts[script]]
    if len(letters) > 1:
        return "mixed"
    if letters:
        return letters[0]
    return "digits" if counts["digit"] else "none"


def token_scripts(text: str) -> list[tuple[str, str]]:
    """``(token, script)`` for every token of :func:`aksharkit.tokenize`.

    The tokeniser already breaks at script boundaries, so ``"mixed"`` is
    rare here; it can appear for URLs and e-mail addresses.
    """
    return [(token.text, detect_script(token.text)) for token in tokenize_spans(text)]


#: Common Nepali words as they are usually typed in Latin letters, used by
#: :func:`looks_romanised_nepali`. Hand-written for this project and not yet
#: reviewed by a native speaker. Words that are also ordinary English words,
#: or that romanised Hindi clearly shares (``hai``, ``ko``, ``ke``, ``ghar``),
#: were left out on purpose; some overlap with Hindi remains.
ROMANISED_NEPALI_WORDS: frozenset[str] = frozenset(
    {
        # "is / is not / am" and their chat spellings
        "cha", "chha", "xa", "chaina", "chhaina", "xaina", "chu", "chhu", "xu",
        "hoina", "huncha", "hunchha", "hunxa", "hudaina", "thiyo", "thiye", "thiena",
        "bhayo", "vayo", "bhako", "vako", "bhaeko",
        # common verb forms
        "garnu", "garne", "gareko", "garchu", "garxu", "garcha", "garxa", "garera",
        "bhanne", "vanne", "bhanera", "vanera", "aune", "parcha", "parxa",
        # postpositions and particles
        "lai", "sanga", "bata", "dekhi", "lagi", "pani",
        # pronouns and possessives
        "timi", "tapai", "hami", "malai", "timilai", "tapailai", "hamilai",
        "mero", "timro", "hamro", "tapaiko", "usko", "uniharu", "hamiharu",
        # question words
        "kasto", "kati", "kina", "kasari", "kahile",
        # frequent adjectives and adverbs
        "ramro", "naramro", "dherai", "thorai", "sabai", "aja", "bholi", "hijo", "ahile",
    }
)  # fmt: skip


def _latin_words(text: str) -> list[str]:
    return [token.text.lower() for token in tokenize_spans(text) if token.kind == "latin"]


def romanised_nepali_score(text: str) -> float:
    """Share of the Latin-letter words that are in :data:`ROMANISED_NEPALI_WORDS`.

    0.0 when the text has no Latin-letter words. This is a word-list count,
    not a language model.
    """
    words = _latin_words(text)
    if not words:
        return 0.0
    return sum(word in ROMANISED_NEPALI_WORDS for word in words) / len(words)


def looks_romanised_nepali(text: str, *, threshold: float = 0.2, min_hits: int = 2) -> bool:
    """Heuristic: does this Latin-letter text look like romanised Nepali?

    True when at least ``min_hits`` different listed words appear and they
    make up at least ``threshold`` of the Latin-letter words.

    Limits, stated plainly:

    * It is a guess from a list of fewer than 100 words. Accuracy has not been
      measured on any corpus.
    * Short texts, texts with unlisted spellings (people spell freely in
      chat) and formal vocabulary will be missed.
    * Romanised Hindi or Maithili that happens to use listed words can be
      accepted. This function cannot tell related languages apart.
    * Text in Devanagari is never matched; use :func:`detect_script` for that.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if min_hits < 1:
        raise ValueError("min_hits must be at least 1")
    words = _latin_words(text)
    if not words:
        return False
    hits = [word for word in words if word in ROMANISED_NEPALI_WORDS]
    return len(set(hits)) >= min_hits and len(hits) / len(words) >= threshold
