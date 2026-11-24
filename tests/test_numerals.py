from __future__ import annotations

from decimal import Decimal

import pytest

from aksharkit import format_number, parse_number, to_ascii_digits, to_devanagari_digits
from aksharkit.numerals import group_digits, to_decimal


@pytest.mark.parametrize(
    ("ascii_text", "devanagari"),
    [
        ("0", "०"), ("1", "१"), ("2", "२"), ("3", "३"), ("4", "४"),
        ("5", "५"), ("6", "६"), ("7", "७"), ("8", "८"), ("9", "९"),
        ("0123456789", "०१२३४५६७८९"),
        ("2083-08-07", "२०८३-०८-०७"),
        ("Rs. 1,250.50", "Rs. १,२५०.५०"),
        ("फोन: 9800000000", "फोन: ९८००००००००"),
        ("", ""),
        ("no digits here", "no digits here"),
        ("वडा नं. 2", "वडा नं. २"),
    ],
)  # fmt: skip
def test_digit_conversion_both_ways(ascii_text: str, devanagari: str) -> None:
    assert to_devanagari_digits(ascii_text) == devanagari
    assert to_ascii_digits(devanagari) == ascii_text


@pytest.mark.parametrize("n", [*range(0, 120), 999, 1000, 12345, 10**6, 10**12 + 7, 9876543210])
def test_digit_round_trip(n: int) -> None:
    text = str(n)
    dev = to_devanagari_digits(text)
    assert len(dev) == len(text)
    assert not any(ch.isascii() for ch in dev)
    assert to_ascii_digits(dev) == text
    assert int(dev) == n  # Python itself reads Devanagari digits


def test_conversion_leaves_other_scripts_alone() -> None:
    mixed = "१२३ 456 ௧௨௩ ۱۲۳"
    assert to_ascii_digits(mixed) == "123 456 ௧௨௩ ۱۲۳"
    assert to_devanagari_digits(mixed) == "१२३ ४५६ ௧௨௩ ۱۲۳"


@pytest.mark.parametrize(
    ("digits", "grouped"),
    [
        ("0", "0"), ("7", "7"), ("42", "42"), ("999", "999"),
        ("1000", "1,000"), ("9999", "9,999"), ("10000", "10,000"), ("99999", "99,999"),
        ("100000", "1,00,000"), ("123456", "1,23,456"), ("1234567", "12,34,567"),
        ("10000000", "1,00,00,000"), ("123456789", "12,34,56,789"),
        ("1000000000", "1,00,00,00,000"), ("100000000000", "1,00,00,00,00,000"),
        ("1234567890123", "12,34,56,78,90,123"),
        ("007", "007"), ("0000", "0,000"),
    ],
)  # fmt: skip
def test_group_digits(digits: str, grouped: str) -> None:
    assert group_digits(digits) == grouped


@pytest.mark.parametrize("bad", ["", "12a", "-12", "1.2", "१२३", " 1"])
def test_group_digits_rejects_non_digits(bad: str) -> None:
    with pytest.raises(ValueError):
        group_digits(bad)


def _reference_grouping(n: int) -> str:
    """An independent, deliberately different implementation."""
    s = str(n)
    if len(s) <= 3:
        return s
    out = s[-3:]
    s = s[:-3]
    while s:
        out = s[-2:] + "," + out
        s = s[:-2]
    return out


@pytest.mark.parametrize("exponent", range(0, 14))
def test_grouping_matches_reference_around_powers_of_ten(exponent: int) -> None:
    base = 10**exponent
    for n in (base - 1, base, base + 1, base * 5, base * 9 + 4):
        if n < 0:
            continue
        expected = _reference_grouping(n)
        assert format_number(n) == expected
        assert format_number(-n) == (f"-{expected}" if n else expected)
        assert parse_number(expected, strict=True) == n
        assert parse_number(to_devanagari_digits(expected), strict=True) == n


@pytest.mark.parametrize(
    ("value", "devanagari", "expected"),
    [
        (1234567, False, "12,34,567"),
        (1234567, True, "१२,३४,५६७"),
        ("1234567.5", True, "१२,३४,५६७.५"),
        ("1234567.50", False, "12,34,567.50"),
        (Decimal("0.5"), False, "0.5"),
        (-1234.5, False, "-1,234.5"),
        ("१२३४५६७", False, "12,34,567"),
        ("1,234,567", False, "12,34,567"),
        (0, True, "०"),
        (Decimal("1E+5"), False, "1,00,000"),
        (Decimal("-0"), False, "0"),
        (100000.0, False, "1,00,000.0"),
        (29164578, True, "२,९१,६४,५७८"),
    ],
)
def test_format_number(value: object, devanagari: bool, expected: str) -> None:
    assert format_number(value, devanagari=devanagari) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0", 0), ("42", 42), ("१२३", 123), ("१२,३४,५६७", 1234567), ("1,234,567", 1234567),
        ("-5", -5), ("−५", -5), ("+7", 7), ("  १०  ", 10), ("- 3", -3),
        ("007", 7), ("1,2,3", 123),
    ],
)  # fmt: skip
def test_parse_integers(text: str, expected: int) -> None:
    result = parse_number(text)
    assert result == expected
    assert isinstance(result, int)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.5", Decimal("0.5")), ("१२.५०", Decimal("12.50")), ("1,234.5", Decimal("1234.5")),
        ("-0.25", Decimal("-0.25")), ("१,२३,४५६.७८", Decimal("123456.78")),
        ("3.0", Decimal("3.0")),
    ],
)  # fmt: skip
def test_parse_decimals(text: str, expected: Decimal) -> None:
    result = parse_number(text)
    assert isinstance(result, Decimal)
    assert result == expected
    assert str(result) == str(expected)  # trailing zeros survive


@pytest.mark.parametrize(
    "text",
    ["", "   ", "abc", "१२क", "1.2.3", ".5", "5.", "1e5", "--1", "+-1", ",1", "1,", "1,,2",
     "1 2", "-", "१२३।", "0x10"],
)  # fmt: skip
def test_parse_rejects(text: str) -> None:
    with pytest.raises(ValueError):
        parse_number(text)


@pytest.mark.parametrize(
    "text", ["12,34,567", "1,234,567", "1,000", "१,००,०००", "999", "1,23,456.5"]
)
def test_parse_strict_accepts_valid_grouping(text: str) -> None:
    assert parse_number(text, strict=True) == parse_number(text)


@pytest.mark.parametrize("text", ["1,2,3", "12,3456", "1234,567", "1,00,00", "12,345,67"])
def test_parse_strict_rejects_bad_grouping(text: str) -> None:
    with pytest.raises(ValueError, match="grouping"):
        parse_number(text, strict=True)
    parse_number(text)  # lenient mode still reads it


def test_to_decimal_is_exact_for_floats() -> None:
    assert to_decimal(0.1) == Decimal("0.1")
    assert to_decimal(1e22) == Decimal("1E+22")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), Decimal("Infinity")])
def test_to_decimal_rejects_non_finite(value: object) -> None:
    with pytest.raises(ValueError):
        to_decimal(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, None, 1j, b"1"])
def test_to_decimal_rejects_bad_types(value: object) -> None:
    with pytest.raises(TypeError):
        to_decimal(value)  # type: ignore[arg-type]
