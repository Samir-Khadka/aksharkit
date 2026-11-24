"""Alphabetical order: every choice listed in docs/sorting.md has a test."""

from __future__ import annotations

import random

import pytest

import aksharkit
from aksharkit import sort_key, sorted_nepali
from aksharkit.collate import CONJUNCT_LETTERS, CONSONANT_ORDER, VOWEL_ORDER


def in_order(*items: str, conjunct_letters: bool = True) -> None:
    """Assert the items are already sorted, whatever order they arrive in."""
    expected = list(items)
    rng = random.Random(7)
    for _ in range(5):
        shuffled = expected[:]
        rng.shuffle(shuffled)
        assert sorted_nepali(shuffled, conjunct_letters=conjunct_letters) == expected


def test_the_alphabet() -> None:
    assert VOWEL_ORDER[:4] == ("अ", "आ", "इ", "ई")
    assert "".join(CONSONANT_ORDER[:5]) == "कखगघङ"
    assert CONSONANT_ORDER[-1] == "ह"
    assert len(CONSONANT_ORDER) == 37  # U+0915 to U+0939, ऩ ऱ ऴ included
    assert CONJUNCT_LETTERS == ("क्ष", "त्र", "ज्ञ")
    in_order(*VOWEL_ORDER, *CONSONANT_ORDER, *CONJUNCT_LETTERS)


def test_vowels_before_consonants() -> None:
    in_order("अ", "आमा", "इनार", "ईश्वर", "उकालो", "ऊन", "ऋषि", "एक", "ऐना", "ओखर", "औषधि", "कमल")


def test_vowel_signs_follow_the_vowel_order() -> None:
    in_order("क", "का", "कि", "की", "कु", "कू", "कृ", "के", "कै", "को", "कौ", "क्", "ख")


def test_a_following_letter_comes_before_a_vowel_sign() -> None:
    in_order("क", "कक", "कमल", "कह", "का", "काम", "कि")


def test_conjuncts_come_after_every_vowel_sign() -> None:
    in_order("कौ", "क्क", "क्या", "क्रम", "ख")
    in_order("मान", "माना", "मान्", "मान्छे")


def test_candrabindu_anusvara_visarga() -> None:
    # Right after the bare syllable, before any following letter; in that order.
    in_order("क", "कँ", "कं", "कः", "कई", "कक", "का", "काँ", "कां", "काक")
    in_order("अ", "अँ", "अं", "अंक", "अः", "अक", "आ")
    # Anusvara is not expanded to a nasal consonant.
    assert sort_key("अंक") != sort_key("अङ्क")
    in_order("अंक", "अक", "अङ्क")


def test_conjunct_letters_after_ha() -> None:
    in_order("हात", "हो", "क्षेत्र", "त्रिशूल", "ज्ञान")
    in_order("क्ष", "क्षा", "क्षि", "क्ष्म", "त्र", "ज्ञ")
    # Inside a word as well.
    in_order("कमल", "कह", "कक्षा", "का")
    in_order("पहर", "पत्र")
    in_order("ज्ज", "ज्ज्ञ")


def test_conjuncts_under_their_first_letter_when_asked() -> None:
    in_order("कौ", "क्या", "क्षेत्र", "खेत", conjunct_letters=False)
    in_order("जहाज", "ज्ञान", "झोला", "तारा", "त्रिशूल", "थाल", "हात", conjunct_letters=False)
    in_order("कक्षा", "कमल", conjunct_letters=False)
    in_order("पत्र", "पहर", conjunct_letters=False)


def test_a_joiner_or_nukta_stops_a_conjunct_letter() -> None:
    assert sort_key("क्\u200cष")[0] != sort_key("क्ष")[0]
    assert sort_key("क्\u200cष")[0] == sort_key("क्ष", conjunct_letters=False)[0]
    in_order("क्\u200cष", "खेत", "क्ष")


def test_nukta_sorts_with_its_letter_plain_first() -> None:
    in_order("जरा", "ज़रा", "जरुर", "ज़रूर", "जल")
    assert sort_key("ज़")[0] == sort_key("ज")[0]
    # Precomposed and decomposed nukta letters are the same thing.
    assert sort_key("\u095b") == sort_key("ज\u093c")
    in_order("कल", "क़लम", "कला")


def test_digits_and_other_characters_come_first() -> None:
    in_order(" ", "!", "0", "10", "१२", "9", "apple", "Banana", "cat", "।", "अ", "क")
    # Devanagari and ASCII digits have the same weight; ASCII first on a tie.
    in_order("1", "१", "2", "२")
    assert sort_key("१२")[0] == sort_key("12")[0]
    # Digits are compared one by one, not as numbers.
    in_order("10", "2")


def test_spaces_sort_before_letters_so_short_phrases_come_first() -> None:
    in_order("राम", "राम बहादुर", "रामकृष्ण", "रामायण")


def test_other_devanagari_letters_come_last() -> None:
    in_order("ज्ञ", "ऽ", "ॐ")


def test_joiners_only_break_ties() -> None:
    assert sort_key("पर्\u200dयो")[0] == sort_key("पर्यो")[0]
    in_order("पर्यो", "पर्\u200dयो")


def test_key_is_total_and_stable() -> None:
    words = ["कमल", "काम", "क", "कं", "ज्ञान", "क्षेत्र", "अ", "ज़रूर", "जरा", "10", "९", "a"]
    once = sorted_nepali(words)
    assert sorted_nepali(once) == once
    assert sorted_nepali(reversed(once)) == once
    assert sorted_nepali(words, reverse=True) == once[::-1]
    assert len({sort_key(word) for word in words}) == len(words)
    assert sorted_nepali([]) == []
    assert sorted_nepali(iter(["ख", "क"])) == ["क", "ख"]
    assert sorted(words, key=sort_key) == once


def test_where_python_default_order_differs() -> None:
    # Code-point order agrees for plain letters, vowel signs and the three signs...
    plain = ["अ", "अंक", "अक", "आमा", "क", "कँ", "कं", "कः", "कक", "का", "कि", "कौ", "क्या", "ख"]
    assert sorted(plain) == sorted_nepali(plain) == plain
    # ...and differs for the conjunct letters, nukta letters and Devanagari digits.
    assert sorted(["ज्ञान", "झोला", "हात"]) == ["ज्ञान", "झोला", "हात"]
    assert sorted_nepali(["ज्ञान", "झोला", "हात"]) == ["झोला", "हात", "ज्ञान"]
    assert sorted(["ज़रा", "जहाज"]) == ["जहाज", "ज़रा"]
    assert sorted_nepali(["ज़रा", "जहाज"]) == ["ज़रा", "जहाज"]
    assert sorted(["१", "क"]) == ["क", "१"]
    assert sorted_nepali(["१", "क"]) == ["१", "क"]
    # With the conjuncts under their first letter only the last two differences remain.
    words = ["कमल", "कक्षा", "क्षेत्र", "ज्ञान", "त्रिशूल", "हात", "पत्र", "पहर"]
    assert sorted_nepali(words, conjunct_letters=False) == sorted(words)


def test_stray_marks_do_not_crash() -> None:
    for text in ("ा", "्", "ं", "\u093c", "क\u093c\u093c", "कंा", "\u0951", "ॲ", "ऄ", "ॿ", "क\u093a"):
        key = sort_key(text)
        assert key[2] == text
        assert sorted_nepali([text, "क"])


def test_bad_arguments() -> None:
    with pytest.raises(TypeError):
        sort_key(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sorted_nepali(["क", 1])  # type: ignore[list-item]


def test_exports() -> None:
    assert "sort_key" in aksharkit.__all__
    assert "sorted_nepali" in aksharkit.__all__
