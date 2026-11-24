"""Added in 0.5: date patterns, dates with month names, ordinals, the र्इ repair, the CLI."""

from __future__ import annotations

import io

import pytest

import aksharkit
from aksharkit import (
    BSDate,
    DateRangeError,
    DisputedDateError,
    dates,
    format_bs,
    normalize,
    ordinal_to_words,
    parse_bs,
)
from aksharkit.cli import main
from aksharkit.normalize import repair_reph_i
from aksharkit.words import MAX_ORDINAL, ORDINALS_IRREGULAR, UNITS

DAY = BSDate(2083, 8, 7)  # Monday 23 November 2026

# --- format_bs patterns -------------------------------------------------------


@pytest.mark.parametrize(
    ("pattern", "roman", "nepali"),
    [
        ("%Y", "2083", "२०८३"),
        ("%y", "83", "८३"),
        ("%m", "08", "०८"),
        ("%-m", "8", "८"),
        ("%d", "07", "०७"),
        ("%-d", "7", "७"),
        ("%B", "Mangsir", "मंसिर"),
        ("%A", "Sombar", "सोमबार"),
        ("%a", "Som", "सोम"),
        ("%%", "%", "%"),
        ("%Y-%m-%d", "2083-08-07", "२०८३-०८-०७"),
        ("%-d %B %Y", "7 Mangsir 2083", "७ मंसिर २०८३"),
        ("%Y %B %-d, %A", "2083 Mangsir 7, Sombar", "२०८३ मंसिर ७, सोमबार"),
        ("%d/%m/%y", "07/08/83", "०७/०८/८३"),
        # Text outside the tokens is copied as it is, digits included.
        ("मिति: %Y साल %B %-d गते", "मिति: 2083 साल Mangsir 7 गते", "मिति: २०८३ साल मंसिर ७ गते"),
        ("no. 12 = %-d", "no. 12 = 7", "no. 12 = ७"),
        ("100%% %Y%m", "100% 208308", "100% २०८३०८"),
        ("%%Y", "%Y", "%Y"),
    ],
)
def test_format_bs_pattern(pattern: str, roman: str, nepali: str) -> None:
    assert format_bs(DAY, pattern) == roman
    assert format_bs(DAY, pattern, devanagari=True) == nepali
    assert format_bs((2083, 8, 7), pattern) == roman


def test_patterns_match_the_named_styles() -> None:
    for flag in (False, True):
        assert format_bs(DAY, "%Y-%m-%d", devanagari=flag) == format_bs(DAY, "iso", devanagari=flag)
        assert format_bs(DAY, "%Y %B %-d", devanagari=flag) == format_bs(
            DAY, "long", devanagari=flag
        )
        assert format_bs(DAY, "%Y %B %-d, %A", devanagari=flag) == format_bs(
            DAY, "full", devanagari=flag
        )


def test_every_month_and_weekday_name_comes_out() -> None:
    assert [format_bs((2083, m, 1), "%B") for m in range(1, 13)] == list(dates.BS_MONTHS_ROMAN)
    assert [format_bs((2083, m, 1), "%B", devanagari=True) for m in range(1, 13)] == list(
        dates.BS_MONTHS
    )
    week = [BSDate(2083, 8, day) for day in range(6, 13)]  # Sunday to Saturday
    assert [format_bs(day, "%A") for day in week] == list(dates.WEEKDAYS_ROMAN)
    assert [format_bs(day, "%A", devanagari=True) for day in week] == list(dates.WEEKDAYS)
    assert [format_bs(day, "%a") for day in week] == [
        "Aai",
        "Som",
        "Man",
        "Bud",
        "Bih",
        "Shu",
        "Sha",
    ]
    assert [format_bs(day, "%a", devanagari=True) for day in week] == [
        "आइत", "सोम", "मङ्गल", "बुध", "बिही", "शुक्र", "शनि",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "pattern", ["%Q", "%H:%M", "%", "x%", "%-", "%-Y", "%e", "% d", "%b", "%j"]
)
def test_unknown_tokens_raise(pattern: str) -> None:
    with pytest.raises(ValueError, match="unknown token"):
        format_bs(DAY, pattern)


def test_pattern_tokens_are_documented_and_all_work() -> None:
    assert list(dates.PATTERN_TOKENS) == [
        "%Y", "%y", "%m", "%-m", "%B", "%d", "%-d", "%A", "%a", "%%",
    ]  # fmt: skip
    for token in dates.PATTERN_TOKENS:
        assert format_bs(DAY, token)
    assert "PATTERN_TOKENS" in dates.__all__


def test_patterns_keep_the_range_guards() -> None:
    with pytest.raises(DateRangeError):
        format_bs((2084, 1, 1), "%Y")
    with pytest.raises(DateRangeError):
        format_bs((2083, 8, 30), "%d")
    with pytest.raises(ValueError, match="unknown style"):
        format_bs(DAY, "short")
    # As with the named styles, a weekday in the disputed span is the majority reading.
    assert format_bs((2062, 2, 10), "%A") == format_bs((2062, 2, 10), "full").split(", ")[1]


# --- parse_bs with month names ---------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("२०८३ मंसिर ८", (2083, 8, 8)),
        ("8 Mangsir 2083", (2083, 8, 8)),
        ("८ मंसिर २०८३", (2083, 8, 8)),
        ("2083 Mangsir 8", (2083, 8, 8)),
        ("2083 मंसिर 08", (2083, 8, 8)),
        ("  2083   mangsir   8  ", (2083, 8, 8)),
        ("2083 MANGSIR 8", (2083, 8, 8)),
        ("२०८३ साल मंसिर ७ गते", (2083, 8, 7)),
        ("७ गते मंसिर २०८३ साल", (2083, 8, 7)),
        ("२०८३ मंसिर ७, सोमबार", (2083, 8, 7)),
        ("2083 Mangsir 7, Sombar", (2083, 8, 7)),
        ("2083 Mangsir 7 sombar", (2083, 8, 7)),
        ("7 Mangsir 2083, सोमबार", (2083, 8, 7)),
        ("२०८३ साल मंसिर ७ गते, सोमबार", (2083, 8, 7)),
        ("2000 Baishakh 1", (2000, 1, 1)),
        ("30 Chaitra 2083", (2083, 12, 30)),
        ("२०६२ जेठ १०", (2062, 2, 10)),  # disputed, but parsing only checks the day exists
        ("2083-08-07", (2083, 8, 7)),
        ("२०८३/८/७", (2083, 8, 7)),
        ("2083.8.7", (2083, 8, 7)),
    ],
)
def test_parse_bs_accepts(text: str, expected: tuple[int, int, int]) -> None:
    assert parse_bs(text) == BSDate(*expected)


def test_parse_reads_back_what_format_writes() -> None:
    for year, month in ((2000, 1), (2050, 6), (2083, 12)):
        for day in (1, 15, dates.days_in_month(year, month)):
            bs = BSDate(year, month, day)
            for flag in (False, True):
                for style in ("iso", "long", "full", "%-d %B %Y", "%Y साल %B %-d गते, %A"):
                    assert parse_bs(format_bs(bs, style, devanagari=flag)) == bs
    for month in range(1, 13):
        assert parse_bs(f"2083 {dates.BS_MONTHS[month - 1]} 1").month == month
        assert parse_bs(f"1 {dates.BS_MONTHS_ROMAN[month - 1]} 2083").month == month


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("8 Mangsir 83", "four digits"),  # which century is not guessed
        ("83 Mangsir 8", "four digits"),
        ("2083 Mangsir 2083", "four digits"),
        ("8 Mangsir 8", "four digits"),
        ("2083 Mangsir 008", "four digits"),
        ("2083 Mangshir 8", "unknown month name 'Mangshir'"),  # no other spellings
        ("2083 मङ्सिर 8", "unknown month name"),
        ("2083 November 8", "unknown month name"),
        ("2083 Mang 8", "unknown month name"),
        ("Mangsir 8", "expected a year"),
        ("Mangsir 2083", "expected a year"),
        ("Mangsir 8 2083", "between the year and the day"),  # month first is not supported
        ("2083 8 Mangsir", "between the year and the day"),
        ("2083 Mangsir", "expected a year"),
        ("2083 Mangsir 8 9", "expected a year"),
        ("2083 Mangsir Mangsir 8", "expected a year"),
        ("गते 2083 मंसिर 8", "expected a year"),
        ("2083 गते मंसिर 8", "expected a year"),
        ("8 साल मंसिर 2083", "expected a year"),
        ("2083 Mangsir 8 BS", "expected a year"),
        ("Sombar 2083 Mangsir 7", "expected a year"),
        ("2083 8 7 गते", "write numeric dates as YYYY-MM-DD"),
        ("2083 08 07x", "write numeric dates as YYYY-MM-DD"),
        ("2083-Mangsir-8", "expected a year"),
        ("yesterday", "expected a year"),
        ("आज", "expected a year"),
    ],
)
def test_parse_bs_refuses_rather_than_guesses(text: str, fragment: str) -> None:
    with pytest.raises(ValueError, match=fragment) as caught:
        parse_bs(text)
    assert not isinstance(caught.value, DateRangeError)
    assert "YYYY-MM-DD" in str(caught.value)
    assert repr(text) in str(caught.value)


@pytest.mark.parametrize("text", ["", "   ", "2083", "2083-08", "20830807", "2083 8 7", "8/7"])
def test_numeric_input_keeps_its_old_message(text: str) -> None:
    with pytest.raises(ValueError, match="not a BS date in YYYY-MM-DD form"):
        parse_bs(text)


@pytest.mark.parametrize(
    "text",
    ["2083 Mangsir 30", "2083 Mangsir 0", "2084 Baishakh 1", "1999 Chaitra 30", "33 Asar 2082"],
)
def test_parse_bs_keeps_the_range_guards(text: str) -> None:
    with pytest.raises(DateRangeError):
        parse_bs(text)


def test_a_weekday_is_checked() -> None:
    with pytest.raises(ValueError, match=r"BS 2083-08-07 is a Sombar \(सोमबार\), not Shanibar"):
        parse_bs("2083 Mangsir 7, Shanibar")
    with pytest.raises(ValueError, match="not मङ्गलबार"):
        parse_bs("२०८३ मंसिर ७, मङ्गलबार")
    # Inside the disputed span a weekday cannot be checked, so it is refused.
    with pytest.raises(DisputedDateError):
        parse_bs("2062 Jestha 10, Sombar")
    assert parse_bs("2062 Jestha 10") == BSDate(2062, 2, 10)


# --- ordinals ---------------------------------------------------------------------


def test_the_first_twenty_ordinals() -> None:
    assert [ordinal_to_words(n) for n in range(1, 21)] == [
        "पहिलो", "दोस्रो", "तेस्रो", "चौथो", "पाँचौँ", "छैटौँ", "सातौँ", "आठौँ", "नवौँ", "दसौँ",
        "एघारौँ", "बाह्रौँ", "तेह्रौँ", "चौधौँ", "पन्ध्रौँ", "सोह्रौँ", "सत्रौँ", "अठारौँ", "उन्नाइसौँ", "बिसौँ",
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("value", "word"),
    [
        (21, "एक्काइसौँ"),
        (25, "पच्चिसौँ"),
        (30, "तिसौँ"),
        (40, "चालिसौँ"),
        (50, "पचासौँ"),
        (59, "उनन्साठीऔँ"),
        (60, "साठीऔँ"),
        (61, "एकसट्ठीऔँ"),
        (70, "सत्तरीऔँ"),
        (71, "एकहत्तरौँ"),
        (75, "पचहत्तरौँ"),
        (79, "उनासीऔँ"),
        (80, "असीऔँ"),
        (89, "उनान्नब्बेऔँ"),
        (90, "नब्बेऔँ"),
        (98, "अन्ठान्नब्बेऔँ"),
        (99, "उनान्सयौँ"),
        (100, "सयौँ"),
    ],
)
def test_ordinals_by_rule(value: int, word: str) -> None:
    assert ordinal_to_words(value) == word


def test_the_rule_for_every_ordinal() -> None:
    assert sorted(ORDINALS_IRREGULAR) == [1, 2, 3, 4, 6, 9]
    assert MAX_ORDINAL == 100
    words = [ordinal_to_words(n) for n in range(1, 101)]
    assert len(set(words)) == 100
    letter = 0
    for value, word in enumerate(words, start=1):
        if value in ORDINALS_IRREGULAR:
            continue
        cardinal = "सय" if value == 100 else UNITS[value]
        assert word.startswith(cardinal)
        ending = word.removeprefix(cardinal)
        assert ending in ("ौँ", "औँ")
        # The letter form is used exactly when the cardinal ends in a vowel sign.
        assert (ending == "औँ") == (cardinal[-1] in "ीे")
        letter += ending == "औँ"
    assert letter == 32  # 59-70 and 79-98


@pytest.mark.parametrize("value", [0, -1, 101, 1000])
def test_ordinals_outside_the_range(value: int) -> None:
    with pytest.raises(ValueError, match="1 to 100"):
        ordinal_to_words(value)


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_ordinals_want_an_int(value: object) -> None:
    with pytest.raises(TypeError):
        ordinal_to_words(value)  # type: ignore[arg-type]


# --- the र्इ repair ------------------------------------------------------------------

RA, VIRAMA, SHORT_I, II = "\u0930", "\u094d", "\u0907", "\u0908"
REPH_I = RA + VIRAMA + SHORT_I


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (REPH_I, II),
        (REPH_I + "श्वर", "ईश्वर"),
        ("ग" + REPH_I, "गई"),
        ("आ" + REPH_I + "न", "आईन"),
        ("भा" + REPH_I + " र दा" + REPH_I, "भाई र दाई"),
        (REPH_I + "ं", "ईं"),
        ("र" + REPH_I, "रई"),
        (REPH_I + REPH_I, II + II),
    ],
)
def test_reph_i_is_repaired(text: str, expected: str) -> None:
    assert repair_reph_i(text) == expected
    assert normalize(text) == expected
    assert normalize(normalize(text)) == expected


@pytest.mark.parametrize(
    "text",
    [
        "रि",  # र with the vowel sign
        "रइ",  # two letters, no virama
        "पर्",  # a dead र at the end
        "पर् इ",  # a space in between
        "कर्म",  # reph on a consonant
        "गर्ई",  # reph before the long vowel
        "गर्उ",  # another vowel
        "क्र्इ",  # र is the tail of a conjunct: no reph is drawn
        "क्\u200dर्इ",
        "र्\u200cइ",  # a joiner keeps them apart on purpose
        "र्\u200dइ",
        "ईश्वर",
        "गई",
        "ऱ्इ",  # a different letter
    ],
)
def test_reph_i_repair_leaves_other_sequences_alone(text: str) -> None:
    assert repair_reph_i(text) == text
    assert normalize(text) == text


def test_reph_i_and_the_joiner_policies() -> None:
    assert normalize(REPH_I, joiners="keep") == II
    assert normalize("र्\u200cइ", joiners="strip") == II  # strip removes the joiner first


# --- the command line -----------------------------------------------------------------


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out.removesuffix("\n"), captured.err


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["aksharas", "नमस्ते"], "न\nम\nस्ते"),
        (["aksharas", "--sep", " | ", "नमस्ते"], "न | म | स्ते"),
        (["aksharas", "--sep", "", "नमस्ते"], "नमस्ते"),
        (["aksharas", "--count", "काठमाडौँ उपत्यका"], "9"),
        (["aksharas", "--count", ""], "0"),
        (["aksharas", "--truncate", "2", "नमस्ते संसार"], "नम"),
        (["aksharas", "--truncate", "4", "--suffix", "…", "नमस्ते संसार"], "नमस्ते…"),
        (["aksharas", "--truncate", "50", "--suffix", "…", "नमस्ते"], "नमस्ते"),
        (["aksharas", "--json", "स्त्री"], '[{"text": "स्त्री", "start": 0, "end": 6}]'),
        (["sort", "हात\nकमल\nज्ञान\nक्षेत्र\nकाम\nअंक"], "अंक\nकमल\nकाम\nहात\nक्षेत्र\nज्ञान"),
        (
            ["sort", "--conjuncts-under-first", "हात\nकमल\nज्ञान\nक्षेत्र\nकाम"],
            "कमल\nकाम\nक्षेत्र\nज्ञान\nहात",
        ),
        (["sort", "--reverse", "क\nग\nख"], "ग\nख\nक"),
        (["sort", "--unique", "ख\nक\nख\nक"], "क\nख"),
        (["sort", "ख\nक\nख"], "क\nख\nख"),
        (["sort", ""], ""),
        (["words", "--ordinal", "1"], "पहिलो"),
        (["words", "--ordinal", "५"], "पाँचौँ"),
        (["words", "--ordinal", "100"], "सयौँ"),
        (["date", "--to", "ad", "२०८३ मंसिर ८"], "2026-11-24"),
        (["date", "--to", "ad", "8 Mangsir 2083"], "2026-11-24"),
        (["date", "2026-11-23", "--pattern", "%-d %B %Y, %A"], "7 Mangsir 2083, Sombar"),
        (
            ["date", "2026-11-23", "--pattern", "%-d %B %Y, %A", "--devanagari"],
            "७ मंसिर २०८३, सोमबार",
        ),
        (["date", "2083 Mangsir 7", "--add-days", "30", "--pattern", "%d/%m/%y"], "08/09/83"),
        (
            ["date", "7 Mangsir 2083", "--until", "2083 Poush 1"],
            "0 years, 0 months, 23 days (23 days)",
        ),
        (["normalize", "र्इश्वर"], "ईश्वर"),
    ],
)
def test_cli(capsys: pytest.CaptureFixture[str], argv: list[str], expected: str) -> None:
    assert run(capsys, *argv) == (0, expected, "")


@pytest.mark.parametrize(
    ("argv", "fragment"),
    [
        (["aksharas", "--truncate", "-1", "क"], "0 or more"),
        (["aksharas", "--truncate", "1", "--count", "क"], "cannot be combined"),
        (["aksharas", "--suffix", "…", "क"], "needs --truncate"),
        (["words", "--ordinal", "0"], "1 to 100"),
        (["words", "--ordinal", "101"], "1 to 100"),
        (["words", "--ordinal", "1.5"], "not a whole number"),
        (["words", "--ordinal", "-3"], "not a whole number"),
        (["words", "--ordinal", "--currency", "5"], "cannot be combined"),
        (["date", "--to", "ad", "8 Mangsir 83"], "four digits"),
        (["date", "--to", "ad", "2083 Mangshir 8"], "unknown month name"),
        (["date", "2026-11-23", "--pattern", "%Q"], "unknown token"),
        (["date", "2026-11-23", "--pattern", "plain"], "no % token"),
        (["date", "--to", "ad", "2083-08-07", "--pattern", "%Y"], "BS dates only"),
        (["date", "2026-11-23", "--fiscal-year", "--pattern", "%Y"], "BS dates only"),
    ],
)
def test_cli_errors(capsys: pytest.CaptureFixture[str], argv: list[str], fragment: str) -> None:
    code, out, err = run(capsys, *argv)
    assert code == 2
    assert out == ""
    assert fragment in err


def test_cli_reads_standard_input(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("हात\nआमा\nकमल\n"))
    assert run(capsys, "sort") == (0, "आमा\nकमल\nहात", "")
    monkeypatch.setattr("sys.stdin", io.StringIO("नमस्ते\n"))
    assert run(capsys, "aksharas", "-", "--count") == (0, "3", "")


def test_version_is_0_5_0() -> None:
    assert aksharkit.__version__ == "0.5.0"
