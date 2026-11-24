from __future__ import annotations

import random
from decimal import Decimal

import pytest

from aksharkit import currency_to_words, integer_to_words, number_to_words, parse_words
from aksharkit.words import ALTERNATIVE_SPELLINGS, MAX_INTEGER, UNITS

SCALES = (10**2, 10**3, 10**5, 10**7, 10**9, 10**11)


@pytest.mark.parametrize("number", range(101))
def test_round_trip_0_to_100(number: int) -> None:
    assert parse_words(integer_to_words(number)) == number
    if number:
        assert parse_words(integer_to_words(-number)) == -number


def _boundaries() -> list[int]:
    out = {0, 1, 99, MAX_INTEGER, MAX_INTEGER - 1}
    for scale in SCALES:
        for count in (1, 2, 9, 10, 99):
            for delta in (-1, 0, 1):
                out.add(count * scale + delta)
    out.update(scale * 100 - 1 for scale in SCALES[1:])
    out.add(10**13 - 10**11)
    return sorted(n for n in out if 0 <= n <= MAX_INTEGER)


@pytest.mark.parametrize("number", _boundaries())
def test_round_trip_scale_boundaries(number: int) -> None:
    words = integer_to_words(number)
    result = parse_words(words)
    assert result == number
    assert type(result) is int
    assert parse_words("ऋण " + words) == -number


def test_round_trip_every_number_to_twenty_thousand() -> None:
    for number in range(20_001):
        assert parse_words(integer_to_words(number)) == number


def test_round_trip_random_sample_across_the_range() -> None:
    rng = random.Random(20261124)
    for _ in range(20_000):
        # Pick the size first so that small and large numbers are both covered.
        number = rng.randrange(10 ** rng.randint(1, 13))
        assert parse_words(integer_to_words(number)) == number
        assert parse_words(integer_to_words(-number)) == -number


def test_round_trip_random_decimals() -> None:
    rng = random.Random(7)
    for _ in range(3_000):
        whole = rng.randrange(10 ** rng.randint(1, 13))
        fraction = "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 8)))
        text = f"{rng.choice(['', '-'])}{whole}.{fraction}"
        result = parse_words(number_to_words(text))
        assert isinstance(result, Decimal)
        assert str(result) == str(Decimal(text))  # trailing zeros survive
        assert result == Decimal(text)


def test_round_trip_random_currency() -> None:
    rng = random.Random(11)
    for _ in range(3_000):
        paisa = rng.randrange(10 ** rng.randint(1, 15))
        amount = Decimal(paisa).scaleb(-2)
        for only in (False, True):
            result = parse_words(currency_to_words(amount, only=only))
            assert result == amount
            assert isinstance(result, int) == (paisa % 100 == 0)


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ("शून्य", 0),
        ("एक सय", 100),
        ("एक लाख पच्चिस हजार", 125_000),
        ("उनान्सय खर्ब उनान्सय अर्ब उनान्सय करोड उनान्सय लाख उनान्सय हजार नौ सय उनान्सय", MAX_INTEGER),
        ("ऋण पाँच", -5),
        ("  एक   सय\tएक \n", 101),
        ("बाह्र दशमलव पाँच शून्य", Decimal("12.50")),
        ("शून्य दशमलव शून्य पाँच", Decimal("0.05")),
        ("ऋण तीन दशमलव एक चार", Decimal("-3.14")),
        ("पाँच सय रुपैयाँ", 500),
        ("पाँच सय रुपैयाँ मात्र", 500),
        ("शून्य रुपैयाँ", 0),
        ("दुई सय रुपैयाँ पचास पैसा मात्र", Decimal("200.50")),
        ("पचास पैसा", Decimal("0.50")),
        ("एक रुपैयाँ एक पैसा", Decimal("1.01")),
        ("ऋण दस रुपैयाँ पाँच पैसा", Decimal("-10.05")),
    ],
)
def test_examples(words: str, expected: int | Decimal) -> None:
    result = parse_words(words)
    assert result == expected
    assert type(result) is type(expected)
    assert str(result) == str(expected)


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ("दश", 10),
        ("सुन्ना", 0),
        ("शुन्य", 0),
        ("बीस", 20),
        ("तीस", 30),
        ("चालीस", 40),
        ("पच्चीस", 25),
        ("एकत्तिस", 31),
        ("चौतिस", 34),
        ("उनसट्ठी", 59),
        ("चौँसट्ठी", 64),
        ("उनानब्बे", 89),
        ("बयानब्बे", 92),
        ("अन्ठानब्बे", 98),
        ("उनन्सय", 99),
        ("एक अरब", 10**9),
        ("एक खरब", 10**11),
        ("माइनस दश", -10),
        ("एक दशमलब पाँच", Decimal("1.5")),
        ("दश रुपियाँ", 10),
        ("सय", 100),
        ("हजार", 1000),
        ("सय रुपैयाँ", 100),
        ("पन्ध्र सय", 1500),
        ("दुई लाख बीस हजार दश", 220_010),
    ],
)
def test_documented_alternatives_are_read(words: str, expected: int | Decimal) -> None:
    assert parse_words(words) == expected


def test_alternative_table() -> None:
    # Never the spelling this package writes, and never ambiguous.
    assert not set(ALTERNATIVE_SPELLINGS) & set(UNITS)
    assert all(0 <= value <= 99 for value in ALTERNATIVE_SPELLINGS.values())
    assert all(" " not in word for word in ALTERNATIVE_SPELLINGS)
    # The long-i rule stays inside the range the sources document (20-48).
    assert "उन्नाईस" not in ALTERNATIVE_SPELLINGS
    assert len(ALTERNATIVE_SPELLINGS) == 47
    assert "एकानब्बे" not in ALTERNATIVE_SPELLINGS  # not listed in docs/sources.md
    for word, value in ALTERNATIVE_SPELLINGS.items():
        assert parse_words(word) == value


def test_unnormalised_input_is_normalised_first() -> None:
    # A zero-width joiner and a non-breaking space are cleaned up before reading.
    assert parse_words("एक\u00a0सय\u200d") == 100


@pytest.mark.parametrize(
    ("words", "reason"),
    [
        ("", "nothing to read"),
        ("   ", "nothing to read"),
        ("ऋण", "number word is missing"),
        ("abc", "not a number word"),
        ("12", "not a number word"),
        ("एक दुई", "cannot follow each other"),
        ("एक सय एक सय", "out of order"),
        ("एक हजार एक लाख", "out of order"),
        ("एक हजार बाह्र सय", "out of order"),
        ("एक लाख हजार", "needs a number before it"),
        ("शून्य सय", "cannot count"),
        ("एक सय शून्य", "can only stand alone"),
        ("एक ऋण", "not a number word"),
        ("ऋण ऋण एक", "not a number word"),
        ("दशमलव पाँच", "number word is missing"),
        ("एक दशमलव", "at least one digit"),
        ("एक दशमलव दस", "single digit"),
        ("एक दशमलव पाँच दशमलव छ", "single digit"),
        ("एक दशमलव पाँच सय", "single digit"),
        ("पाँच मात्र", "मात्र is only read after"),
        ("रुपैयाँ", "number word is missing"),
        ("एक रुपैयाँ दुई रुपैयाँ", "may each appear once"),
        ("एक पैसा दुई पैसा", "may each appear once"),
        ("एक पैसा दुई रुपैयाँ", "not a number word"),
        ("एक रुपैयाँ दुई", "not expected after"),
        ("एक रुपैयाँ सय पैसा", "between 1 and 99"),
        ("एक रुपैयाँ शून्य पैसा", "between 1 and 99"),
        ("एक रुपैयाँ पैसा", "number word is missing"),
        ("एक रुपैयाँ मात्र पाँच पैसा", "not a number word"),
        ("एक दशमलव पाँच रुपैयाँ", "not a number word"),
        ("एक सय खर्ब", "needs a number before it"),
        ("एक हजार खर्ब", "needs a number before it"),
        ("पन्ध्र सय हजार", "needs a number before it"),
        ("एक हजार पन्ध्र सय", "out of order or too large"),
    ],
)
def test_malformed_input(words: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason) as info:
        parse_words(words)
    assert "cannot read" in str(info.value)


def test_nothing_above_the_range_can_be_written() -> None:
    # A count is at most 99, so 99 खर्ब is the largest leading group.
    assert parse_words("उनान्सय खर्ब") == 99 * 10**11
    with pytest.raises(ValueError, match="needs a number before it"):
        parse_words("एक सय खर्ब")


@pytest.mark.parametrize("value", [None, 5, 1.5, b"x", ["एक"]])
def test_rejects_non_strings(value: object) -> None:
    with pytest.raises(TypeError):
        parse_words(value)  # type: ignore[arg-type]
