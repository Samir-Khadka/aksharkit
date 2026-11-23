"""Numbers to Nepali words.

Nepali number words from 0 to 99 are irregular, so they come from a table,
not a rule. The table and every spelling choice in it are documented in
``docs/sources.md``.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .numerals import Number, to_decimal

__all__ = [
    "MAX_INTEGER",
    "UNITS",
    "currency_to_words",
    "integer_to_words",
    "number_to_words",
]

# 0-99. Cross-checked against two independent published lists; see
# docs/sources.md for the sources and for each place where they disagree.
UNITS: tuple[str, ...] = (
    "शून्य", "एक", "दुई", "तीन", "चार", "पाँच", "छ", "सात", "आठ", "नौ",
    "दस", "एघार", "बाह्र", "तेह्र", "चौध", "पन्ध्र", "सोह्र", "सत्र", "अठार", "उन्नाइस",
    "बिस", "एक्काइस", "बाइस", "तेइस", "चौबिस", "पच्चिस", "छब्बिस", "सत्ताइस", "अट्ठाइस", "उनन्तिस",
    "तिस", "एकतिस", "बत्तिस", "तेत्तिस", "चौँतिस", "पैँतिस", "छत्तिस", "सैँतिस", "अठतिस", "उनन्चालिस",
    "चालिस", "एकचालिस", "बयालिस", "त्रिचालिस", "चवालिस", "पैँतालिस", "छयालिस", "सतचालिस", "अठचालिस",
    "उनन्चास",
    "पचास", "एकाउन्न", "बाउन्न", "त्रिपन्न", "चवन्न", "पचपन्न", "छपन्न", "सन्ताउन्न", "अन्ठाउन्न", "उनन्साठी",
    "साठी", "एकसट्ठी", "बयसट्ठी", "त्रिसट्ठी", "चौसट्ठी", "पैँसट्ठी", "छयसट्ठी", "सतसट्ठी", "अठसट्ठी",
    "उनन्सत्तरी",
    "सत्तरी", "एकहत्तर", "बहत्तर", "त्रिहत्तर", "चौहत्तर", "पचहत्तर", "छयहत्तर", "सतहत्तर", "अठहत्तर",
    "उनासी",
    "असी", "एकासी", "बयासी", "त्रियासी", "चौरासी", "पचासी", "छयासी", "सतासी", "अठासी", "उनान्नब्बे",
    "नब्बे", "एकान्नब्बे", "बयान्नब्बे", "त्रियान्नब्बे", "चौरान्नब्बे", "पन्चान्नब्बे", "छयान्नब्बे",
    "सन्तान्नब्बे", "अन्ठान्नब्बे", "उनान्सय",
)  # fmt: skip

_SCALES: tuple[tuple[int, str], ...] = (
    (10**11, "खर्ब"),
    (10**9, "अर्ब"),
    (10**7, "करोड"),
    (10**5, "लाख"),
    (10**3, "हजार"),
    (10**2, "सय"),
)

#: Largest supported magnitude: 99 खर्ब 99 अर्ब 99 करोड 99 लाख 99 हजार 999.
MAX_INTEGER = 10**13 - 1

_MINUS = "ऋण"
_POINT = "दशमलव"
_RUPEES = "रुपैयाँ"
_PAISA = "पैसा"
_ONLY = "मात्र"


def _check_range(value: int) -> None:
    if abs(value) > MAX_INTEGER:
        raise ValueError(
            f"{value} is outside the supported range (up to {MAX_INTEGER}); "
            "units above खर्ब are not implemented"
        )


def _positive_integer_words(value: int) -> str:
    if value < 100:
        return UNITS[value]
    parts: list[str] = []
    rest = value
    for scale, name in _SCALES:
        count, rest = divmod(rest, scale)
        if count:
            parts.append(f"{UNITS[count]} {name}")
    if rest:
        parts.append(UNITS[rest])
    return " ".join(parts)


def integer_to_words(value: int) -> str:
    """Spell an integer in Nepali words using सय, हजार, लाख, करोड, अर्ब, खर्ब.

    ``integer_to_words(125000)`` -> ``"एक लाख पच्चिस हजार"``. Negative
    numbers are prefixed with ``ऋण``.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("integer_to_words expects an int")
    _check_range(value)
    if value < 0:
        return f"{_MINUS} {_positive_integer_words(-value)}"
    return _positive_integer_words(value)


def number_to_words(value: Number) -> str:
    """Spell any supported number in Nepali words.

    Whole numbers read as :func:`integer_to_words`. A fractional part is read
    digit by digit after ``दशमलव``, exactly as written:
    ``number_to_words("12.50")`` -> ``"बाह्र दशमलव पाँच शून्य"``.
    Strings may use Devanagari digits and grouping commas.
    """
    number = to_decimal(value)
    plain = format(abs(number), "f")
    whole_text, _, fraction = plain.partition(".")
    whole = int(whole_text)
    _check_range(whole)
    words = _positive_integer_words(whole)
    if fraction:
        digits = " ".join(UNITS[int(ch)] for ch in fraction)
        words = f"{words} {_POINT} {digits}"
    if number < 0:
        words = f"{_MINUS} {words}"
    return words


def currency_to_words(value: Number, *, only: bool = False) -> str:
    """Spell an amount in rupees and paisa.

    ``currency_to_words("1250.50")`` -> ``"एक हजार दुई सय पचास रुपैयाँ पचास पैसा"``.
    The amount is rounded half-up to two decimal places (whole paisa).
    ``only=True`` appends ``मात्र``, as written on cheques.
    """
    number = to_decimal(value)
    paisa_total = int((abs(number) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    rupees, paisa = divmod(paisa_total, 100)
    _check_range(rupees)
    parts: list[str] = []
    if rupees or not paisa:
        parts.append(f"{_positive_integer_words(rupees)} {_RUPEES}")
    if paisa:
        parts.append(f"{UNITS[paisa]} {_PAISA}")
    words = " ".join(parts)
    if number < 0 and paisa_total:
        words = f"{_MINUS} {words}"
    if only:
        words = f"{words} {_ONLY}"
    return words
