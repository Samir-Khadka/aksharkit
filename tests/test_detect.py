from __future__ import annotations

import pytest

from aksharkit import (
    detect_script,
    looks_romanised_nepali,
    romanised_nepali_score,
    script_counts,
    script_shares,
    to_roman,
    token_scripts,
)
from aksharkit.detect import ROMANISED_NEPALI_WORDS, SCRIPTS, char_script


@pytest.mark.parametrize(
    ("char", "expected"),
    [
        ("क", "devanagari"),
        ("ा", "devanagari"),  # matra
        ("्", "devanagari"),  # virama
        ("ँ", "devanagari"),
        ("ॐ", "devanagari"),
        ("a", "latin"),
        ("Z", "latin"),
        ("é", "latin"),
        ("ā", "latin"),
        ("ṭ", "latin"),  # Latin Extended Additional, used by the iast scheme
        ("5", "digit"),
        ("५", "digit"),
        ("я", "other"),
        ("中", "other"),
        ("ب", "other"),
        (" ", None),
        ("\n", None),
        (".", None),
        ("।", None),
        ("॥", None),
        ("-", None),
        ("\u200d", None),
        ("\u0301", None),  # combining acute
        ("×", None),
        ("😀", None),
    ],
)
def test_char_script(char: str, expected: str | None) -> None:
    assert char_script(char) == expected


@pytest.mark.parametrize("value", ["", "ab", None, 5])
def test_char_script_wants_one_character(value: object) -> None:
    with pytest.raises(TypeError):
        char_script(value)  # type: ignore[arg-type]


def test_whole_devanagari_block_is_never_latin_or_other() -> None:
    for code in range(0x0900, 0x0980):
        assert char_script(chr(code)) in ("devanagari", "digit", None)
    assert [chr(c) for c in range(0x0900, 0x0980) if char_script(chr(c)) == "digit"] == list(
        "०१२३४५६७८९"
    )


def test_ascii_letters_and_digits() -> None:
    for code in range(0x80):
        char = chr(code)
        expected = "latin" if char.isalpha() else "digit" if char.isdigit() else None
        assert char_script(char) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("नेपाल राम्रो छ।", "devanagari"),
        ("२०८३ साल मंसिर ७", "devanagari"),
        ("Hello, world!", "latin"),
        ("Room 5", "latin"),
        ("nepāla rāmro cha", "latin"),
        ("Facebookमा photo राख्नुहोस्", "mixed"),
        ("नेपाल Nepal", "mixed"),
        ("Привет नमस्ते", "mixed"),
        ("Привет", "other"),
        ("२०८३-08-07", "digits"),
        ("12,34,567.50", "digits"),
        ("", "none"),
        ("  \n", "none"),
        ("...!?।", "none"),
        ("😀", "none"),
    ],
)
def test_detect_script(text: str, expected: str) -> None:
    assert detect_script(text) == expected


def test_counts_and_shares() -> None:
    text = "म school जान्छु 5"
    counts = script_counts(text)
    assert counts == {"devanagari": 7, "latin": 6, "digit": 1, "other": 0}
    assert tuple(counts) == SCRIPTS
    shares = script_shares(text)
    assert tuple(shares) == SCRIPTS
    assert shares["devanagari"] == pytest.approx(0.5)
    assert shares["latin"] == pytest.approx(6 / 14)
    assert sum(shares.values()) == pytest.approx(1.0)


def test_shares_of_nothing_are_zero() -> None:
    assert script_shares("") == dict.fromkeys(SCRIPTS, 0.0)
    assert script_shares(" ... ") == dict.fromkeys(SCRIPTS, 0.0)


def test_token_scripts() -> None:
    assert token_scripts("Facebookमा 5G छ। a@b.com") == [
        ("Facebook", "latin"),
        ("मा", "devanagari"),
        ("5", "digits"),
        ("G", "latin"),
        ("छ", "devanagari"),
        ("।", "none"),
        ("a@b.com", "latin"),
    ]
    assert token_scripts("") == []


def test_transliteration_output_is_latin() -> None:
    # iast output uses diacritics; it must still be seen as Latin.
    for word in ("ज्ञान", "कृष्ण", "काठमाडौँ", "दुःख"):
        assert detect_script(to_roman(word, "iast")) == "latin"
        assert detect_script(to_roman(word, "simple")) == "latin"


# --- the romanised-Nepali heuristic ------------------------------------------


def test_word_list_shape() -> None:
    assert 50 <= len(ROMANISED_NEPALI_WORDS) < 100
    for word in ROMANISED_NEPALI_WORDS:
        assert word == word.lower()
        assert word.isascii() and word.isalpha()
    # Left out on purpose: English words and words romanised Hindi shares.
    assert not ROMANISED_NEPALI_WORDS & {"ma", "ho", "to", "hai", "ko", "ke", "ka", "ghar", "the"}


@pytest.mark.parametrize(
    "text",
    [
        "timi kasto cha?",
        "malai ramro lagyo, tapai lai kasto cha",
        "Mero ghar Urlabari ma cha, timro kaha ho?",
        "aja dherai kaam xa",
        "hami bholi jane ho, timi pani aune?",
    ],
)
def test_looks_romanised_nepali_true(text: str) -> None:
    assert looks_romanised_nepali(text)
    assert 0.0 < romanised_nepali_score(text) <= 1.0


@pytest.mark.parametrize(
    "text",
    [
        "",
        "How are you doing today, my friend?",
        "The quick brown fox jumps over the lazy dog.",
        "aap kaise hai",
        "नेपाल राम्रो छ",  # Devanagari is never matched
        "cha",  # one hit is not enough
        "cha cha cha",  # the same word repeated is still one distinct hit
        "12345",
    ],
)
def test_looks_romanised_nepali_false(text: str) -> None:
    assert not looks_romanised_nepali(text)


def test_score_and_thresholds() -> None:
    assert romanised_nepali_score("") == 0.0
    assert romanised_nepali_score("नेपाल") == 0.0
    assert romanised_nepali_score("timi kasto cha") == 1.0
    assert romanised_nepali_score("TIMI Kasto") == 1.0  # case-insensitive
    text = "timi and I went to the market and then we came back home cha"
    assert romanised_nepali_score(text) == pytest.approx(2 / 14)
    assert not looks_romanised_nepali(text)  # two hits but under the 20% share
    assert looks_romanised_nepali(text, threshold=0.1)
    assert looks_romanised_nepali("cha", min_hits=1)
    assert not looks_romanised_nepali("timi kasto cha", min_hits=4)


@pytest.mark.parametrize("kwargs", [{"threshold": -0.1}, {"threshold": 1.5}, {"min_hits": 0}])
def test_bad_heuristic_settings(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        looks_romanised_nepali("timi kasto cha", **kwargs)  # type: ignore[arg-type]
