"""Command-line tests for the commands added in 0.4: number, detect, date tools."""

from __future__ import annotations

import io
import json

import pytest

from aksharkit import BSDate, dates
from aksharkit.cli import main

CALENDAR = (
    "Mangsir 2083\n"
    "Aai\tSom\tMan\tBud\tBih\tShu\tSha\n"
    "\t\t1\t2\t3\t4\t5\n"
    "6\t7\t8\t9\t10\t11\t12\n"
    "13\t14\t15\t16\t17\t18\t19\n"
    "20\t21\t22\t23\t24\t25\t26\n"
    "27\t28\t29"
)


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["number", "एक लाख पच्चिस हजार"], "125000"),
        (["number", "एक लाख पच्चीस हजार"], "125000"),
        (["number", "--group", "एक लाख पच्चिस हजार"], "1,25,000"),
        (["number", "--devanagari", "एक लाख पच्चिस हजार"], "१२५०००"),
        (["number", "--group", "--devanagari", "ऋण बाह्र लाख दशमलव पाँच"], "-१२,००,०००.५"),
        (["number", "बाह्र दशमलव पाँच शून्य"], "12.50"),
        (["number", "पाँच सय रुपैयाँ मात्र"], "500"),
        (["number", "दुई सय रुपैयाँ पचास पैसा"], "200.50"),
        (
            ["detect", "Facebookमा photo 5 छ"],
            "script: mixed\ndevanagari: 17.6%\nlatin: 76.5%\ndigit: 5.9%\nother: 0.0%",
        ),
        (
            ["detect", "नेपाल"],
            "script: devanagari\ndevanagari: 100.0%\nlatin: 0.0%\ndigit: 0.0%\nother: 0.0%",
        ),
        (
            ["detect", "..."],
            "script: none\ndevanagari: 0.0%\nlatin: 0.0%\ndigit: 0.0%\nother: 0.0%",
        ),
        (["detect", "--tokens", "म school जान्छु"], "म\tdevanagari\nschool\tlatin\nजान्छु\tdevanagari"),
        (["date", "--calendar", "2083-08"], CALENDAR),
        (["date", "--calendar", "२०८३/८"], CALENDAR),
        (["date", "2083-08-07", "--add-days", "30"], "2083-09-08"),
        (["date", "2083-08-07", "--add-days", "-7", "--style", "long"], "2083 Kartik 30"),
        (["date", "2083-03-32", "--add-months", "1"], "2083-04-31"),
        (
            ["date", "2083-08-07", "--add-months", "1", "--add-days", "1", "--devanagari"],
            "२०८३-०९-०८",
        ),
        (
            ["date", "2059-05-12", "--until", "2083-08-07"],
            "24 years, 2 months, 25 days (8853 days)",
        ),
        (["date", "2059-05-12", "--age", "--until", "2083-08-07"], "24"),
        (["date", "2059-05-12", "--age", "--until", "2083-08-07", "--devanagari"], "२४"),
        (["date", "--calendar", "2062-02", "--allow-disputed"], None),
    ],
)
def test_cli_output(
    argv: list[str], expected: str | None, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == 0
    out = capsys.readouterr().out
    if expected is None:
        assert out.startswith("Jestha 2062\n")
    else:
        assert out == expected + "\n"


def test_calendar_in_devanagari(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["date", "--calendar", "2083-08", "--devanagari"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "मंसिर २०८३"
    assert lines[-1] == "२७\t२८\t२९"


def test_detect_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["detect", "--json", "timi kasto cha"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["script"] == "latin"
    assert report["counts"] == {"devanagari": 0, "latin": 12, "digit": 0, "other": 0}
    assert report["shares"]["latin"] == 1.0
    assert report["tokens"][0] == {"text": "timi", "script": "latin"}
    assert report["romanised_nepali_score"] == 1.0
    assert report["looks_romanised_nepali"] is True


@pytest.mark.parametrize(
    ("argv", "stdin", "expected"),
    [
        (["number"], "बयालिस\n", "42\n"),
        (["number", "-"], "बयालिस\n", "42\n"),
        (["detect"], "नेपाल Nepal\n", "script: mixed\n"),
    ],
)
def test_cli_reads_stdin(
    argv: list[str],
    stdin: str,
    expected: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    assert main(argv) == 0
    assert capsys.readouterr().out.startswith(expected)


def test_age_defaults_to_today(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dates, "today_bs", lambda: BSDate(2083, 8, 8))
    assert main(["date", "2060-08-08", "--age"]) == 0
    assert capsys.readouterr().out == "23\n"


@pytest.mark.parametrize(
    "argv",
    [
        ["number", "एक एक"],
        ["number", "42"],
        ["number", ""],
        ["date", "--calendar", "2083"],
        ["date", "--calendar", "2083-13"],
        ["date", "--calendar", "2084-01"],
        ["date", "--calendar", "2062-01"],
        ["date", "--calendar", "2083-08", "2083-08-07"],
        ["date", "--calendar", "2083-08", "--add-days", "1"],
        ["date", "--add-days", "1"],
        ["date", "2083-12-30", "--add-days", "1"],
        ["date", "2083-08-07", "--add-months", "5"],
        ["date", "2083-08-07", "--add-days", "1", "--to", "ad"],
        ["date", "2083-08-07", "--add-days", "1", "--age"],
        ["date", "2083-08-07", "--until", "2083-08-06"],
        ["date", "2083-08-07", "--until", "tomorrow"],
        ["date", "2062-02-10", "--add-days", "1"],
    ],
)
def test_cli_bad_input_exits_2(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("aksharkit: error:")


def test_add_days_must_be_a_whole_number(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["date", "2083-08-07", "--add-days", "1.5"])
    assert info.value.code == 2
    assert "invalid int value" in capsys.readouterr().err
