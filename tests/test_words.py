from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from aksharkit import currency_to_words, integer_to_words, number_to_words
from aksharkit.words import MAX_INTEGER, UNITS

GOLDEN = Path(__file__).parent / "golden" / "number_words_0_100.tsv"


def _golden() -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for line in GOLDEN.read_text("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        number, words = line.split("\t")
        rows.append((int(number), words))
    return rows


def test_golden_file_is_complete() -> None:
    assert [n for n, _ in _golden()] == list(range(101))


@pytest.mark.parametrize(("number", "words"), _golden())
def test_every_number_0_to_100(number: int, words: str) -> None:
    assert integer_to_words(number) == words
    assert number_to_words(number) == words
    assert number_to_words(str(number)) == words


def test_units_table_shape() -> None:
    assert len(UNITS) == 100
    assert len(set(UNITS)) == 100
    assert all(" " not in word and word == word.strip() for word in UNITS)


# Typed here by hand from the published lists (docs/sources.md), independently
# of the table in the package, so a slip in either place is caught.
@pytest.mark.parametrize(
    ("number", "words"),
    [
        (1, "एक"), (2, "दुई"), (3, "तीन"), (5, "पाँच"), (6, "छ"), (9, "नौ"),
        (11, "एघार"), (12, "बाह्र"), (13, "तेह्र"), (14, "चौध"), (15, "पन्ध्र"),
        (16, "सोह्र"), (17, "सत्र"), (18, "अठार"), (19, "उन्नाइस"),
        (21, "एक्काइस"), (22, "बाइस"), (27, "सत्ताइस"), (28, "अट्ठाइस"), (29, "उनन्तिस"),
        (39, "उनन्चालिस"), (42, "बयालिस"), (44, "चवालिस"), (49, "उनन्चास"), (50, "पचास"),
        (51, "एकाउन्न"), (53, "त्रिपन्न"), (58, "अन्ठाउन्न"), (60, "साठी"),
        (61, "एकसट्ठी"), (69, "उनन्सत्तरी"), (70, "सत्तरी"), (71, "एकहत्तर"), (75, "पचहत्तर"),
        (79, "उनासी"), (80, "असी"), (84, "चौरासी"), (88, "अठासी"), (90, "नब्बे"),
        (91, "एकान्नब्बे"), (98, "अन्ठान्नब्बे"), (99, "उनान्सय"),
    ],
)  # fmt: skip
def test_spot_checks_against_sources(number: int, words: str) -> None:
    assert integer_to_words(number) == words


@pytest.mark.parametrize(
    ("number", "words"),
    [
        (100, "एक सय"),
        (101, "एक सय एक"),
        (110, "एक सय दस"),
        (200, "दुई सय"),
        (599, "पाँच सय उनान्सय"),
        (999, "नौ सय उनान्सय"),
        (1_000, "एक हजार"),
        (1_001, "एक हजार एक"),
        (1_100, "एक हजार एक सय"),
        (1_234, "एक हजार दुई सय चौँतिस"),
        (2_083, "दुई हजार त्रियासी"),
        (10_000, "दस हजार"),
        (12_345, "बाह्र हजार तीन सय पैँतालिस"),
        (99_999, "उनान्सय हजार नौ सय उनान्सय"),
        (100_000, "एक लाख"),
        (100_001, "एक लाख एक"),
        (125_000, "एक लाख पच्चिस हजार"),
        (123_456, "एक लाख तेइस हजार चार सय छपन्न"),
        (1_000_000, "दस लाख"),
        (1_234_567, "बाह्र लाख चौँतिस हजार पाँच सय सतसट्ठी"),
        (9_999_999, "उनान्सय लाख उनान्सय हजार नौ सय उनान्सय"),
        (10_000_000, "एक करोड"),
        (10_000_001, "एक करोड एक"),
        (25_050_000, "दुई करोड पचास लाख पचास हजार"),
        (100_000_000, "दस करोड"),
        (1_000_000_000, "एक अर्ब"),
        (1_500_000_000, "एक अर्ब पचास करोड"),
        (10_000_000_000, "दस अर्ब"),
        (100_000_000_000, "एक खर्ब"),
        (100_000_000_001, "एक खर्ब एक"),
        (
            MAX_INTEGER,
            "उनान्सय खर्ब उनान्सय अर्ब उनान्सय करोड उनान्सय लाख उनान्सय हजार नौ सय उनान्सय",
        ),
    ],
)
def test_composite_numbers(number: int, words: str) -> None:
    assert integer_to_words(number) == words


@pytest.mark.parametrize(
    ("value", "words"),
    [
        (-1, "ऋण एक"),
        (-125_000, "ऋण एक लाख पच्चिस हजार"),
        ("-५", "ऋण पाँच"),
        (Decimal("-0.5"), "ऋण शून्य दशमलव पाँच"),
        (0, "शून्य"),
        (-0, "शून्य"),
        ("12.5", "बाह्र दशमलव पाँच"),
        ("12.50", "बाह्र दशमलव पाँच शून्य"),
        ("3.14159", "तीन दशमलव एक चार एक पाँच नौ"),
        (0.25, "शून्य दशमलव दुई पाँच"),
        (0.1, "शून्य दशमलव एक"),
        (Decimal("100.01"), "एक सय दशमलव शून्य एक"),
        ("१,२३,४५६", "एक लाख तेइस हजार चार सय छपन्न"),
        ("१२३.४५", "एक सय तेइस दशमलव चार पाँच"),
        ("1,234", "एक हजार दुई सय चौँतिस"),
        (" 42 ", "बयालिस"),
        (7.0, "सात दशमलव शून्य"),
    ],
)
def test_number_to_words_inputs(value: object, words: str) -> None:
    assert number_to_words(value) == words  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "only", "words"),
    [
        (0, False, "शून्य रुपैयाँ"),
        (1, False, "एक रुपैयाँ"),
        (100, False, "एक सय रुपैयाँ"),
        ("1250.50", False, "एक हजार दुई सय पचास रुपैयाँ पचास पैसा"),
        ("1250.50", True, "एक हजार दुई सय पचास रुपैयाँ पचास पैसा मात्र"),
        ("0.50", False, "पचास पैसा"),
        ("0.05", False, "पाँच पैसा"),
        ("0.99", False, "उनान्सय पैसा"),
        ("10.1", False, "दस रुपैयाँ दस पैसा"),
        ("99.999", False, "एक सय रुपैयाँ"),
        ("0.005", False, "एक पैसा"),
        ("0.004", False, "शून्य रुपैयाँ"),
        ("2.675", False, "दुई रुपैयाँ अठसट्ठी पैसा"),
        (-5, False, "ऋण पाँच रुपैयाँ"),
        ("-0.25", False, "ऋण पच्चिस पैसा"),
        ("-0.001", False, "शून्य रुपैयाँ"),
        (100_000, True, "एक लाख रुपैयाँ मात्र"),
        ("१,००,०००.७५", True, "एक लाख रुपैयाँ पचहत्तर पैसा मात्र"),
        (Decimal("12345678.90"), False,
         "एक करोड तेइस लाख पैँतालिस हजार छ सय अठहत्तर रुपैयाँ नब्बे पैसा"),
    ],
)  # fmt: skip
def test_currency(value: object, only: bool, words: str) -> None:
    assert currency_to_words(value, only=only) == words  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [MAX_INTEGER + 1, -(MAX_INTEGER + 1), 10**20])
def test_out_of_range(value: int) -> None:
    with pytest.raises(ValueError, match="outside the supported range"):
        integer_to_words(value)
    with pytest.raises(ValueError, match="outside the supported range"):
        number_to_words(value)
    with pytest.raises(ValueError, match="outside the supported range"):
        currency_to_words(value)


@pytest.mark.parametrize("value", [True, False, 1.0, "1", None, Decimal(1)])
def test_integer_to_words_rejects_non_int(value: object) -> None:
    with pytest.raises(TypeError):
        integer_to_words(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, None, [1], b"1"])
def test_number_to_words_rejects_bad_types(value: object) -> None:
    with pytest.raises(TypeError):
        number_to_words(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value", ["", "abc", "1.2.3", "१२क", float("nan"), float("inf"), Decimal("NaN"), "1e5"]
)
def test_number_to_words_rejects_bad_values(value: object) -> None:
    with pytest.raises(ValueError):
        number_to_words(value)  # type: ignore[arg-type]


def test_all_three_digit_numbers_are_two_or_three_parts() -> None:
    # Structural check over a full range: "<1-9> सय [<1-99>]".
    for n in range(100, 1000):
        parts = integer_to_words(n).split(" ")
        assert parts[0] == UNITS[n // 100]
        assert parts[1] == "सय"
        assert parts[2:] == ([UNITS[n % 100]] if n % 100 else [])


def test_words_are_unique_up_to_a_lakh() -> None:
    seen = {integer_to_words(n) for n in range(0, 100_000, 7)}
    assert len(seen) == len(range(0, 100_000, 7))
