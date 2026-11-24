"""Numbers to Nepali words, and Nepali words back to numbers.

Nepali number words from 0 to 99 are irregular, so they come from a table,
not a rule. The table and every spelling choice in it are documented in
``docs/sources.md``. :func:`parse_words` reads the same table backwards and
also accepts the alternative spellings listed there.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .normalize import normalize
from .numerals import Number, to_decimal

__all__ = [
    "ALTERNATIVE_SPELLINGS",
    "MAX_INTEGER",
    "UNITS",
    "currency_to_words",
    "integer_to_words",
    "number_to_words",
    "parse_words",
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


# --- words to numbers -------------------------------------------------------


def _long_i(word: str) -> str | None:
    """The "also written" long-i form of a 20-48 word: बिस -> बीस, बाइस -> बाईस."""
    if word.endswith("िस"):
        return word[:-2] + "ीस"
    if word.endswith("इस"):
        return word[:-2] + "ईस"
    return None


def _alternative_units() -> dict[str, int]:
    """Spellings other than the ones in :data:`UNITS` that are read on input.

    They follow the "Alternative(s)" column in docs/sources.md: the named
    variants, plus two families produced by rule from the chosen spellings
    rather than copied from a list: long-i forms of 20-48 (also applied to
    the named variants एकत्तिस and चौतिस) and single-न forms of 89 and 92-98.
    """
    named = {
        "सुन्ना": 0,
        "शुन्य": 0,
        "दश": 10,
        "एकत्तिस": 31,
        "चौतिस": 34,
        "उनसट्ठी": 59,
        "चौँसट्ठी": 64,
        "उनन्सय": 99,
    }
    out = dict(named)
    for value, word in enumerate(UNITS):
        if value != 91 and word.endswith("ान्नब्बे"):  # 91 is not a documented variant
            out[word.removesuffix("ान्नब्बे") + "ानब्बे"] = value
    for word, value in [*_unit_items(), *named.items()]:
        longer = _long_i(word) if 20 <= value <= 48 else None
        if longer is not None:
            out[longer] = value
    return out


def _unit_items() -> list[tuple[str, int]]:
    """``(word, value)`` for the 100 spellings this package writes."""
    return [(word, value) for value, word in enumerate(UNITS)]


#: Alternative spellings of 0-99 that :func:`parse_words` accepts. The
#: package never writes these; see docs/sources.md for where each comes from.
ALTERNATIVE_SPELLINGS: dict[str, int] = _alternative_units()

_UNIT_VALUES: dict[str, int] = {**ALTERNATIVE_SPELLINGS, **dict(_unit_items())}
_SCALE_VALUES: dict[str, int] = {
    **{name: scale for scale, name in _SCALES},
    "अरब": 10**9,
    "खरब": 10**11,
}
_MINUS_WORDS = frozenset({_MINUS, "माइनस"})
_POINT_WORDS = frozenset({_POINT, "दशमलब"})
_RUPEE_WORDS = frozenset({_RUPEES, "रुपियाँ"})


def _fail(text: str, reason: str) -> ValueError:
    return ValueError(f"cannot read {text!r} as a number in words: {reason}")


def _parse_integer_words(tokens: list[str], text: str) -> int:
    """Read ``[count] scale ... [rest]`` with scales going from large to small."""
    if not tokens:
        raise _fail(text, "a number word is missing")
    total = 0
    ceiling = MAX_INTEGER + 1  # what is still to come must be smaller than this
    pending: int | None = None
    pending_word = ""
    for index, token in enumerate(tokens):
        if token in _SCALE_VALUES:
            scale = _SCALE_VALUES[token]
            if pending is None:
                if index != 0:
                    raise _fail(text, f"{token!r} needs a number before it")
                count = 1  # a bare सय or हजार at the start means one of them
            elif pending == 0:
                raise _fail(text, f"{pending_word!r} cannot count {token!r}")
            else:
                count = pending
            if scale >= ceiling or count * scale >= ceiling:
                raise _fail(text, f"{token!r} is out of order or too large here")
            total += count * scale
            ceiling = scale
            pending = None
        elif token in _UNIT_VALUES:
            if pending is not None:
                raise _fail(text, f"{pending_word!r} and {token!r} cannot follow each other")
            pending = _UNIT_VALUES[token]
            pending_word = token
        else:
            raise _fail(text, f"{token!r} is not a number word this package knows")
    if pending is not None:
        if pending == 0 and len(tokens) > 1:
            raise _fail(text, f"{pending_word!r} can only stand alone")
        total += pending
    return total


def _parse_currency_words(tokens: list[str], text: str) -> int | Decimal:
    """Read ``<n> रुपैयाँ [<1-99> पैसा]`` or ``<1-99> पैसा``."""
    rupee_at = [i for i, token in enumerate(tokens) if token in _RUPEE_WORDS]
    paisa_at = [i for i, token in enumerate(tokens) if token == _PAISA]
    if len(rupee_at) > 1 or len(paisa_at) > 1:
        raise _fail(text, "रुपैयाँ and पैसा may each appear once")
    rupees = 0
    rest = tokens
    if rupee_at:
        rupees = _parse_integer_words(tokens[: rupee_at[0]], text)
        rest = tokens[rupee_at[0] + 1 :]
    if not paisa_at:
        if rest:
            raise _fail(text, f"{rest[0]!r} is not expected after रुपैयाँ")
        return rupees
    if rest[-1] != _PAISA:
        raise _fail(text, "पैसा must end the amount")
    paisa = _parse_integer_words(rest[:-1], text)
    if not 1 <= paisa <= 99:
        raise _fail(text, "पैसा must be between 1 and 99")
    return Decimal(rupees * 100 + paisa).scaleb(-2)


def parse_words(text: str) -> int | Decimal:
    """Read a number written in Nepali words. The inverse of the functions above.

    ``parse_words("एक लाख पच्चिस हजार")`` -> ``125000``. The range is the same
    as :func:`integer_to_words` (up to :data:`MAX_INTEGER`).

    * ``ऋण`` (or ``माइनस``) first makes the number negative.
    * ``दशमलव`` is followed by single digits, kept exactly as written:
      ``"बाह्र दशमलव पाँच शून्य"`` -> ``Decimal("12.50")``.
    * Amounts in ``रुपैयाँ`` and ``पैसा``, with an optional final ``मात्र``,
      give an ``int`` when there is no paisa and a two-place ``Decimal`` when
      there is: ``"दुई सय रुपैयाँ पचास पैसा मात्र"`` -> ``Decimal("200.50")``.

    Besides the spellings this package writes, the alternatives listed in
    ``docs/sources.md`` are read (``दश``, ``बीस``, ``सुन्ना``, ``अरब`` ...); see
    :data:`ALTERNATIVE_SPELLINGS`. Two spoken shortcuts are read as well: a
    bare ``सय`` or ``हजार`` at the start means one of them, and the hundreds
    may be counted past nine when nothing larger comes first
    (``"पन्ध्र सय"`` -> ``1500``).

    Returns ``int`` for whole numbers, otherwise ``Decimal`` (never ``float``).
    Raises ``ValueError`` with the offending word for anything else.
    """
    if not isinstance(text, str):
        raise TypeError("parse_words expects a str")
    tokens = normalize(text).split()
    if not tokens:
        raise _fail(text, "there is nothing to read")
    negative = tokens[0] in _MINUS_WORDS
    if negative:
        tokens = tokens[1:]
    is_currency = any(token in _RUPEE_WORDS or token == _PAISA for token in tokens)
    value: int | Decimal
    if is_currency:
        if tokens[-1] == _ONLY:
            tokens = tokens[:-1]
        value = _parse_currency_words(tokens, text)
    elif tokens and tokens[-1] == _ONLY:
        raise _fail(text, "मात्र is only read after an amount in रुपैयाँ or पैसा")
    elif any(token in _POINT_WORDS for token in tokens):
        at = next(i for i, token in enumerate(tokens) if token in _POINT_WORDS)
        whole = _parse_integer_words(tokens[:at], text)
        digits: list[str] = []
        for token in tokens[at + 1 :]:
            digit = _UNIT_VALUES.get(token)
            if digit is None or digit > 9:
                raise _fail(text, f"after दशमलव each word must be a single digit, not {token!r}")
            digits.append(str(digit))
        if not digits:
            raise _fail(text, "दशमलव must be followed by at least one digit")
        value = Decimal(f"{whole}.{''.join(digits)}")
    else:
        value = _parse_integer_words(tokens, text)
    return -value if negative else value
