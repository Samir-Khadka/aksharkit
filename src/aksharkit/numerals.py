"""Devanagari and ASCII digits, Nepali digit grouping, and number parsing."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Union

__all__ = [
    "Number",
    "format_number",
    "group_digits",
    "parse_number",
    "to_ascii_digits",
    "to_decimal",
    "to_devanagari_digits",
]

Number = Union[int, float, Decimal, str]

_ASCII = "0123456789"
_DEVANAGARI = "०१२३४५६७८९"
_TO_DEVANAGARI = str.maketrans(_ASCII, _DEVANAGARI)
_TO_ASCII = str.maketrans(_DEVANAGARI, _ASCII)

_PLAIN = re.compile(r"\d+(?:\.\d+)?")
_GROUPED_NEPALI = re.compile(r"\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d+)?")
_GROUPED_WESTERN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
_MINUS_SIGNS = ("-", "\u2212")


def to_devanagari_digits(text: str) -> str:
    """Replace ASCII digits with Devanagari digits; leave everything else."""
    return text.translate(_TO_DEVANAGARI)


def to_ascii_digits(text: str) -> str:
    """Replace Devanagari digits with ASCII digits; leave everything else."""
    return text.translate(_TO_ASCII)


def group_digits(digits: str) -> str:
    """Group a string of ASCII digits the Nepali way (3, then 2, 2, ...).

    ``"1234567"`` becomes ``"12,34,567"``.
    """
    if not digits.isascii() or not digits.isdigit():
        raise ValueError(f"expected ASCII digits only, got {digits!r}")
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.append(head[-2:])
        head = head[:-2]
    parts.append(head)
    parts.reverse()
    parts.append(tail)
    return ",".join(parts)


def parse_number(text: str, *, strict: bool = False) -> int | Decimal:
    """Parse a number written with ASCII or Devanagari digits.

    Accepts an optional sign, grouping commas and one decimal point.
    Returns ``int`` when there is no decimal point, otherwise ``Decimal``
    (never ``float``, so no digits are invented or lost).

    With ``strict=True`` the commas must form valid Nepali (``12,34,567``) or
    western (``1,234,567``) grouping; otherwise commas are simply ignored.
    """
    cleaned = to_ascii_digits(text.strip())
    negative = False
    if cleaned[:1] in _MINUS_SIGNS:
        negative = True
        cleaned = cleaned[1:].lstrip()
    elif cleaned[:1] == "+":
        cleaned = cleaned[1:].lstrip()
    if not cleaned:
        raise ValueError(f"not a number: {text!r}")
    if "," in cleaned:
        if strict and not (
            _GROUPED_NEPALI.fullmatch(cleaned) or _GROUPED_WESTERN.fullmatch(cleaned)
        ):
            raise ValueError(f"invalid digit grouping: {text!r}")
        if cleaned.startswith(",") or cleaned.endswith(",") or ",," in cleaned:
            raise ValueError(f"not a number: {text!r}")
        cleaned = cleaned.replace(",", "")
    if not _PLAIN.fullmatch(cleaned):
        raise ValueError(f"not a number: {text!r}")
    if "." in cleaned:
        value = Decimal(cleaned)
        return -value if negative else value
    whole = int(cleaned)
    return -whole if negative else whole


def to_decimal(value: Number) -> Decimal:
    """Convert any supported number input to an exact, finite ``Decimal``.

    Floats go through ``repr`` so ``0.1`` stays ``0.1``. Booleans are
    rejected because ``True`` is almost never meant as the number one.
    """
    if isinstance(value, bool):
        raise TypeError("bool is not accepted as a number")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        result = Decimal(repr(value))
    elif isinstance(value, Decimal):
        result = value
    elif isinstance(value, str):
        return Decimal(parse_number(value))
    else:
        raise TypeError(f"unsupported number type: {type(value).__name__}")
    if not result.is_finite():
        raise ValueError(f"not a finite number: {value!r}")
    return result


def format_number(value: Number, *, devanagari: bool = False) -> str:
    """Format a number with Nepali digit grouping (लाख / करोड style).

    ``format_number(1234567)`` -> ``"12,34,567"``;
    ``format_number("1234567.5", devanagari=True)`` -> ``"१२,३४,५६७.५"``.
    Decimal places are kept exactly as given; nothing is rounded.
    """
    try:
        number = to_decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise ValueError(f"not a number: {value!r}") from exc
    plain = format(number, "f")
    negative = plain.startswith("-")
    if negative:
        plain = plain[1:]
    whole, _, fraction = plain.partition(".")
    out = group_digits(whole)
    if fraction:
        out = f"{out}.{fraction}"
    if negative and number != 0:
        out = f"-{out}"
    return to_devanagari_digits(out) if devanagari else out
