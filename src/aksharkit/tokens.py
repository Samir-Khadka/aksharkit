"""Word tokenisation and sentence splitting for Nepali and mixed text."""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["ABBREVIATIONS", "Token", "sentences", "tokenize", "tokenize_spans"]


@dataclass(frozen=True)
class Token:
    """A token with its position in the original string.

    ``kind`` is one of ``"word"`` (Devanagari), ``"latin"``, ``"number"``,
    ``"url"``, ``"email"`` or ``"punct"``. ``text == source[start:end]``.
    """

    text: str
    start: int
    end: int
    kind: str


_DEV = "\u0900-\u0963\u0970-\u097f"
_DIGIT = "0-9\u0966-\u096f"
_LATIN = "A-Za-z\u00c0-\u024f"

_TOKEN = re.compile(
    "|".join(
        (
            r"(?P<url>(?:https?://|www\.)[^\s<>\"]+)",
            r"(?P<email>[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)",
            rf"(?P<number>[{_DIGIT}]+(?:[.,][{_DIGIT}]+)*)",
            rf"(?P<word>[{_DEV}][{_DEV}\u200c\u200d]*)",
            rf"(?P<latin>[{_LATIN}]+(?:['\u2019\-][{_LATIN}]+)*)",
            r"(?P<space>\s+)",
            r"(?P<punct>.)",
        )
    ),
    re.DOTALL,
)

_URL_TRAILING = ".,;:!?\u0964\u0965)]}'\""


def tokenize_spans(text: str) -> list[Token]:
    """Split ``text`` into tokens, keeping character offsets.

    Whitespace is dropped; everything else is kept, so joining is lossless
    apart from spacing. Devanagari digits, decimals and grouped numbers stay
    whole (``१२,३४,५६७.५०`` is one token). A script change always starts a
    new token, so ``Facebookमा`` gives ``Facebook`` and ``मा``.
    """
    out: list[Token] = []
    pos = 0
    length = len(text)
    while pos < length:
        match = _TOKEN.match(text, pos)
        if match is None:  # pragma: no cover - the pattern matches any char
            raise AssertionError(f"tokenizer stalled at offset {pos}")
        kind = match.lastgroup or "punct"
        end = match.end()
        if kind == "url":
            while end - 1 > pos and text[end - 1] in _URL_TRAILING:
                end -= 1
        if kind != "space":
            out.append(Token(text[pos:end], pos, end, kind))
        pos = end
    return out


def tokenize(text: str) -> list[str]:
    """Split ``text`` into token strings. See :func:`tokenize_spans`."""
    return [token.text for token in tokenize_spans(text)]


#: Abbreviations after which a full stop does not end a sentence. Compared
#: without the trailing dot; Latin entries are matched case-insensitively.
ABBREVIATIONS: frozenset[str] = frozenset(
    {
        # Nepali
        "डा", "प्रा", "इ", "ई", "वि", "सं", "नं", "रु", "मि", "कि", "से", "ग्रा", "लि", "पृ",
        # English
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "vs", "etc", "no", "fig",
        "eg", "ie", "inc", "ltd", "co", "pvt", "govt", "dept", "approx", "rs", "nrs",
    }
)  # fmt: skip

_TERMINATOR = re.compile("[\u0964\u0965?!]+|\\.+")
_CLOSERS = "\"'\u201d\u2019)]}\u00bb"
_WORD_BEFORE = re.compile(r"\S+$")


def _is_digit(ch: str) -> bool:
    return ch.isdigit()


def _full_stop_ends_sentence(text: str, sentence_start: int, start: int, end: int) -> bool:
    """Decide whether the run of full stops ``text[start:end]`` ends a sentence."""
    after = end
    while after < len(text) and text[after] in _CLOSERS:
        after += 1
    if after < len(text) and not text[after].isspace():
        return False  # 3.14, example.com, वि.सं
    rest = text[after:].lstrip()
    if not rest:
        return True
    if rest[0].islower():
        return False
    if end - start > 1:
        return True  # an ellipsis followed by a new sentence
    before = _WORD_BEFORE.search(text[sentence_start:start])
    word = before.group(0).lstrip("\"'\u201c\u2018([{") if before else ""
    if not word:
        return False
    if "." in word:
        return False  # गा.वि.स. / U.S. / e.g.
    if word.lower() in ABBREVIATIONS:
        return False
    if len(word) == 1 and word.isascii() and word.isalpha():
        return False  # an initial: "B. P. Koirala"
    if all(_is_digit(ch) for ch in word) and before is not None:
        # "1. First point": a list marker at the very start of a sentence.
        return text[sentence_start:start].strip() != word
    return True


def sentences(text: str) -> list[str]:
    """Split ``text`` into sentences.

    ``।``, ``॥``, ``?`` and ``!`` always end a sentence. A full stop ends one
    only when it is not part of a decimal, a domain, a dotted abbreviation, a
    known abbreviation, an initial or a leading list number. Closing quotes
    and brackets stay with the sentence they close. Each sentence is
    stripped; empty pieces are dropped.
    """
    out: list[str] = []
    start = 0
    for match in _TERMINATOR.finditer(text):
        if match.start() < start:
            continue
        run = match.group(0)
        if run[0] == "." and not _full_stop_ends_sentence(text, start, match.start(), match.end()):
            continue
        end = match.end()
        while end < len(text) and text[end] in _CLOSERS:
            end += 1
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        start = end
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out
