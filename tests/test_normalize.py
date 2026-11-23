from __future__ import annotations

import random
import unicodedata

import pytest

from aksharkit import normalize
from aksharkit.normalize import (
    ZWJ,
    ZWNJ,
    collapse_duplicate_marks,
    compose_split_vowels,
    fix_danda,
    fix_joiners,
    normalize_whitespace,
)

V = "\u094d"  # virama


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # split vowels that only look right
        ("\u0905\u093e", "आ"),
        ("\u0905\u094b", "ओ"),
        ("\u0905\u094c", "औ"),
        ("\u0906\u0947", "ओ"),
        ("\u0906\u0948", "औ"),
        ("\u090f\u0947", "ऐ"),
        ("\u0909\u0941", "ऊ"),
        ("क\u093e\u0947", "को"),
        ("क\u093e\u0948", "कौ"),
        ("ड\u093e\u0945क्टर", "डॉक्टर"),
        ("\u0905\u093eम\u093e", "आमा"),
        ("नेप\u093e\u0947ल", "नेपोल"),
    ],
)
def test_split_vowels(raw: str, expected: str) -> None:
    assert compose_split_vowels(raw) == expected
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("किि", "कि"),
        ("काा", "का"),
        ("कुुु", "कु"),
        ("हुँँ", "हुँ"),
        ("संं", "सं"),
        ("दुःःख", "दुःख"),
        (f"क{V}{V}ष", "क्ष"),
        ("ज\u093c\u093c", "ज\u093c"),
        ("ऽऽ", "ऽऽ"),  # avagraha is a letter and may repeat
        ("कक", "कक"),
        ("११", "११"),
        ("किकि", "किकि"),
        ("कीि", "कीि"),  # different signs: not ours to judge
    ],
)
def test_duplicate_marks(raw: str, expected: str) -> None:
    assert collapse_duplicate_marks(raw) == expected
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (f"र{V}{ZWJ}याल", f"र{V}{ZWJ}याल"),  # eyelash ra: meaningful
        (f"क{V}{ZWNJ}ष", f"क{V}{ZWNJ}ष"),  # explicit halant: meaningful
        (f"श{V}{ZWJ}र", f"श{V}{ZWJ}र"),
        (f"नेपा{ZWJ}ल", "नेपाल"),
        (f"नेपा{ZWNJ}ल", "नेपाल"),
        (f"{ZWJ}क", "क"),
        (f"क{ZWNJ}", "क"),
        (f"क{V}{ZWJ}{ZWJ}ष", f"क{V}{ZWJ}ष"),
        (f"क{V}{ZWNJ}{ZWJ}ष", f"क{V}{ZWJ}ष"),
        (f"श्रीमान{V}{ZWNJ}", f"श्रीमान{V}"),  # nothing follows: redundant
        (f"क{V}{ZWNJ} ख", f"क{V} ख"),
        (f"क{V}{ZWJ}।", f"क{V}।"),
        (f"a{ZWJ}b", "ab"),
        (f"क{V}{ZWJ}a", f"क{V}a"),
    ],
)
def test_joiners_safe(raw: str, expected: str) -> None:
    assert fix_joiners(raw) == expected
    assert normalize(raw) == expected


def test_joiner_policies() -> None:
    raw = f"र{V}{ZWJ}याल {ZWNJ}क"
    assert fix_joiners(raw, "keep") == raw
    assert fix_joiners(raw, "strip") == f"र{V}याल क"
    assert normalize(raw, joiners="strip") == f"र{V}याल क"
    assert normalize(raw, joiners="keep") == raw
    with pytest.raises(ValueError, match="joiner policy"):
        fix_joiners(raw, "nope")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("\u0958", "क\u093c"),  # NFC decomposes composition-excluded nukta letters
        ("\u095b", "ज\u093c"),
        ("\u095e", "फ\u093c"),
        ("न\u093c", "\u0929"),
        ("र\u093c", "\u0931"),
        ("क\u093c", "क\u093c"),
        ("ज\u093cा", "ज\u093cा"),
    ],
)
def test_nukta_canonical_form(raw: str, expected: str) -> None:
    assert normalize(raw) == expected
    assert normalize(raw) == unicodedata.normalize("NFC", raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("म घर जान्छु|", "म घर जान्छु।"),
        ("म घर जान्छु |", "म घर जान्छु ।"),
        ("राम||", "राम॥"),
        ("राम ||", "राम ॥"),
        ("ॐ शान्ति।।", "ॐ शान्ति॥"),
        ("उमेर १२३|", "उमेर १२३।"),
        ("ऊ आयो| म गएँ|", "ऊ आयो। म गएँ।"),
        ("पहिलो|\nदोस्रो|", "पहिलो।\nदोस्रो।"),
        ("a | b", "a | b"),
        ("ls | grep x", "ls | grep x"),
        ("x || y", "x || y"),
        ("| सुरुमा", "| सुरुमा"),
        ("छ|तर", "छ|तर"),  # no space after: ambiguous, left alone
        ("राम।", "राम।"),
        ("राम॥", "राम॥"),
    ],
)
def test_danda(raw: str, expected: str) -> None:
    assert fix_danda(raw) == expected
    assert normalize(raw) == expected


def test_danda_can_be_switched_off() -> None:
    assert normalize("राम|", danda=False) == "राम|"
    assert normalize("शान्ति।।", danda=False) == "शान्ति।।"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  नमस्ते   संसार  ", "नमस्ते संसार"),
        ("नमस्ते\u00a0संसार", "नमस्ते संसार"),
        ("नमस्ते\tसंसार", "नमस्ते संसार"),
        ("नम\u200bस्ते", "नमस्ते"),
        ("\ufeffनमस्ते", "नमस्ते"),
        ("नम\u00adस्ते", "नमस्ते"),
        ("नम\u2060स्ते", "नमस्ते"),
        ("क\r\nख\rग", "क\nख\nग"),
        ("क  \nख", "क\nख"),
        ("क\n\nख", "क\n\nख"),
        ("क\u2003ख\u3000ग", "क ख ग"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_whitespace(raw: str, expected: str) -> None:
    assert normalize_whitespace(raw) == expected
    assert normalize(raw) == expected


def test_whitespace_can_be_switched_off() -> None:
    assert normalize("  क  ख  ", whitespace=False) == "  क  ख  "
    assert normalize("नम\u200bस्ते", whitespace=False) == "नम\u200bस्ते"


def test_hidden_character_cannot_shield_a_sequence() -> None:
    # A stray joiner or zero-width space between the two halves of a split
    # vowel must not stop the repair.
    assert normalize(f"\u0905{ZWJ}\u093e") == "आ"
    assert normalize("क\u093e\u200b\u0947") == "को"
    assert normalize(f"कि{ZWNJ}ि") == "कि"
    assert normalize(f"न{ZWJ}\u093c") == "\u0929"


@pytest.mark.parametrize(
    "text",
    [
        "नेपाल एक सुन्दर देश हो।",
        "श्री ५ को सरकार",
        "क्षत्रिय, त्रिभुवन, ज्ञान, श्रद्धा",
        "रु. १,२५०.५० मात्र",
        "Kathmandu, Nepal — काठमाडौँ",
        "ॐ भूर्भुवः स्वः॥",
        "हुँदैन, गर्दिनँ, आउँछु",
        f"र{V}{ZWJ}याल र प{V}{ZWJ}याज",
        "English only text, with punctuation!",
        "१२३४५६७८९०",
    ],
)
def test_clean_text_is_unchanged(text: str) -> None:
    assert normalize(text) == text


_ALPHABET = [
    "क", "ष", "र", "न", "अ", "आ", "ए", "उ", "ा", "ि", "े", "ै", "ो", "ु", "ँ", "ं", "ः",
    V, "\u093c", ZWJ, ZWNJ, "\u200b", "\ufeff", " ", "  ", "\t", "\n", "|", "।", "a", "1", "१",
    "\u0958", "\u00a0", "\u093e\u0945",
]  # fmt: skip


@pytest.mark.parametrize("seed", range(60))
def test_idempotent_on_random_noise(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(40):
        raw = "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(0, 24)))
        once = normalize(raw)
        assert normalize(once) == once, repr(raw)
        assert unicodedata.normalize("NFC", once) == once, repr(raw)
        assert "\u200b" not in once and "\ufeff" not in once
        assert "  " not in once and once == once.strip()
        for policy in ("strip", "keep"):
            again = normalize(raw, joiners=policy)
            assert normalize(again, joiners=policy) == again, repr(raw)
