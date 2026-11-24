"""Akshara segmentation: the rules in docs/aksharas.md, case by case."""

from __future__ import annotations

import pytest

import aksharkit
from aksharkit import Akshara, akshara_count, akshara_spans, aksharas, truncate

ZWJ = "\u200d"
ZWNJ = "\u200c"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", []),
        ("क", ["क"]),
        ("नमस्ते", ["न", "म", "स्ते"]),
        ("नेपाल", ["ने", "पा", "ल"]),
        ("काठमाडौँ", ["का", "ठ", "मा", "डौँ"]),
        ("स्त्री", ["स्त्री"]),
        ("राष्ट्रिय", ["रा", "ष्ट्रि", "य"]),
        ("विद्यार्थी", ["वि", "द्या", "र्थी"]),
        ("क्षत्रिय", ["क्ष", "त्रि", "य"]),
        ("ज्ञान", ["ज्ञा", "न"]),
        ("हुँ", ["हुँ"]),
        ("संसार", ["सं", "सा", "र"]),
        ("दुःख", ["दुः", "ख"]),
        ("आमा", ["आ", "मा"]),
        ("अँध्यारो", ["अँ", "ध्या", "रो"]),
        ("उकालो", ["उ", "का", "लो"]),
        ("गाउँ", ["गा", "उँ"]),
        ("ज़रूर", ["ज़", "रू", "र"]),
        ("क\u093c", ["क\u093c"]),
        ("\u0958", ["\u0958"]),  # precomposed क़
        ("ड\u093c्य", ["ड\u093c्य"]),
        # A dead consonant at the end is a unit of its own.
        ("श्रीमान्", ["श्री", "मा", "न्"]),
        ("जगत्", ["ज", "ग", "त्"]),
        # Joiners after a virama keep the cluster whole.
        (f"पर्{ZWJ}यो", ["प", f"र्{ZWJ}यो"]),
        (f"क्{ZWNJ}ष", [f"क्{ZWNJ}ष"]),
        (f"क्{ZWJ}", [f"क्{ZWJ}"]),
        # Other Devanagari characters.
        ("ॐ", ["ॐ"]),
        ("ऽ", ["ऽ"]),
        ("१२३", ["१", "२", "३"]),
        ("राम।", ["रा", "म", "।"]),
        # Not well formed, but nothing is lost and nothing floats free.
        ("कंा", ["कंा"]),
        ("अा", ["अा"]),
        ("किि", ["किि"]),
        ("ंक", ["ं", "क"]),
        ("्क", ["्", "क"]),
        (f"{ZWJ}क", [ZWJ, "क"]),
        ("क्ा", ["क्ा"]),
        # Outside Devanagari: one code point each, marks attached.
        ("abc", ["a", "b", "c"]),
        ("e\u0301a", ["e\u0301", "a"]),
        ("a\u0300\u0301", ["a\u0300\u0301"]),
        ("नेपाल 12 ok", ["ने", "पा", "ल", " ", "1", "2", " ", "o", "k"]),
        ("क\nख", ["क", "\n", "ख"]),
        ("ক\u09beখ", ["ক\u09be", "খ"]),  # Bengali: marks attach, no cluster rules
    ],
)
def test_aksharas(text: str, expected: list[str]) -> None:
    assert aksharas(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "नेपालको जनसंख्या २,९१,६४,५७८ छ।",
        f"आज पानी पर्{ZWJ}यो॥ Facebookमा photo",
        "श्रीमान् ज्ञानेन्द्र क्षेत्री\tस्त्री\r\n",
        "\u0902\u094d\u093c" + ZWNJ + "क",
        "e\u0301 🙂 ক্ষ",
    ],
)
def test_spans_cover_the_text_exactly(text: str) -> None:
    spans = akshara_spans(text)
    assert "".join(unit.text for unit in spans) == text
    position = 0
    for unit in spans:
        assert isinstance(unit, Akshara)
        assert unit.start == position
        assert unit.end > unit.start
        assert unit.text == text[unit.start : unit.end]
        position = unit.end
    assert position == len(text)


def test_spans_have_offsets() -> None:
    assert akshara_spans("नमस्ते") == [
        Akshara("न", 0, 1),
        Akshara("म", 1, 2),
        Akshara("स्ते", 2, 6),
    ]
    assert akshara_spans("") == []


def test_every_devanagari_code_point_alone_is_one_unit() -> None:
    for code in range(0x0900, 0x0980):
        assert aksharas(chr(code)) == [chr(code)], hex(code)


def test_no_unit_starts_with_a_combining_character_after_a_letter() -> None:
    marks = "\u0901\u0902\u0903\u093c\u093e\u093f\u0940\u0941\u0947\u094b\u094c\u094d" + ZWJ + ZWNJ
    for first in "कअ१a":
        for mark in marks:
            for second in marks:
                units = aksharas(first + mark + second + "क")
                assert units[0][0] == first
                assert all(unit[0] not in marks for unit in units), units


@pytest.mark.parametrize(
    ("text", "count", "without_spaces"),
    [
        ("", 0, 0),
        ("नमस्ते", 3, 3),
        ("काठमाडौँ उपत्यका", 9, 8),
        ("राम घर गयो।", 9, 7),
        ("  ", 2, 0),
    ],
)
def test_akshara_count(text: str, count: int, without_spaces: int) -> None:
    assert akshara_count(text) == count
    assert akshara_count(text, skip_whitespace=True) == without_spaces


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        (0, ""),
        (1, "वि"),
        (2, "विद्या"),
        (3, "विद्यार्थी"),
        (5, "विद्यार्थीहरू"),
        (6, "विद्यार्थीहरू "),
        (7, "विद्यार्थीहरू वि"),
        (10, "विद्यार्थीहरू विद्यालय"),
        (11, "विद्यार्थीहरू विद्यालय "),
        (12, "विद्यार्थीहरू विद्यालय ग"),
        (13, "विद्यार्थीहरू विद्यालय गए"),
        (500, "विद्यार्थीहरू विद्यालय गए"),
    ],
)
def test_truncate(limit: int, expected: str) -> None:
    assert truncate("विद्यार्थीहरू विद्यालय गए", limit) == expected


def test_truncate_never_cuts_inside_an_akshara() -> None:
    text = f"श्रीमान् पर्{ZWJ}यो ज़रूर स्त्री हुँ दुःख काठमाडौँ"
    units = aksharas(text)
    for limit in range(len(units) + 2):
        assert truncate(text, limit) == "".join(units[:limit])


def test_truncate_suffix() -> None:
    assert truncate("नमस्ते संसार", 3, suffix="…") == "नमस्ते…"
    assert truncate("नमस्ते संसार", 4, suffix="…") == "नमस्ते…"  # the space is dropped
    assert truncate("नमस्ते संसार", 5, suffix="...") == "नमस्ते सं..."
    assert truncate("नमस्ते", 3, suffix="…") == "नमस्ते"  # nothing cut, nothing added
    assert truncate("नमस्ते", 0, suffix="…") == "…"


def test_bad_arguments() -> None:
    with pytest.raises(ValueError, match="0 or more"):
        truncate("क", -1)
    for bad in (True, 1.0, "1", None):
        with pytest.raises(TypeError):
            truncate("क", bad)  # type: ignore[arg-type]
    for function in (aksharas, akshara_spans, akshara_count):
        with pytest.raises(TypeError):
            function(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        truncate(b"abc", 1)  # type: ignore[arg-type]


def test_exports() -> None:
    for name in ("Akshara", "akshara_count", "akshara_spans", "aksharas", "truncate"):
        assert name in aksharkit.__all__
        assert name in aksharkit.akshara.__all__
