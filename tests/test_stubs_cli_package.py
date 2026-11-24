from __future__ import annotations

import datetime as dt
import io
import json
from importlib import resources
from pathlib import Path

import pytest

import aksharkit
from aksharkit import DataNotVerifiedError, dates, legacy
from aksharkit._data import load_table, require_verified
from aksharkit.cli import main

# --- legacy fonts: Preeti is experimental, in both directions ---------------


def test_preeti_table_is_experimental_and_names_its_sources() -> None:
    table = load_table("font_preeti")
    assert table["status"] == "experimental"
    assert len(table["sources"]) == 4
    assert table["mapping"]


def test_unicode_to_preeti_reports_instead_of_guessing() -> None:
    result = legacy.encode_preeti("नेपाल abc")
    assert result.text == "g]kfn abc"
    assert result.unmapped_chars == ()
    assert [span.text for span in result.foreign] == ["abc"]
    assert legacy.encode_preeti("नेपाल-भारत").unmapped_chars == ("-",)


def test_unknown_font_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="unknown font"):
        legacy.to_unicode("x", "kantipur")


def test_dates_refuse_if_the_table_is_ever_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    draft = {**load_table("bs_calendar"), "status": "draft"}
    monkeypatch.setattr(dates, "load_table", lambda name: draft)
    dates._calendar.cache_clear()
    try:
        for call in (
            lambda: dates.bs_to_ad(2083, 8, 7),
            lambda: dates.ad_to_bs(dt.date(2026, 11, 23)),
            dates.load_calendar,
        ):
            with pytest.raises(DataNotVerifiedError, match="not available yet"):
                call()
    finally:
        monkeypatch.undo()
        dates._calendar.cache_clear()
    assert dates.bs_to_ad(2083, 8, 7) == dt.date(2026, 11, 23)


@pytest.mark.parametrize(
    "change",
    [
        {"years": {"2000": [30] * 12}},
        {"years": {"2000": [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30]}},
        {"epoch": {"bs": [2001, 1, 1], "ad": "1943-04-14"}},
    ],
)
def test_dates_reject_a_malformed_table(
    change: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = {**load_table("bs_calendar"), **change}
    monkeypatch.setattr(dates, "load_table", lambda name: broken)
    dates._calendar.cache_clear()
    try:
        with pytest.raises(ValueError, match="BS calendar table"):
            dates.load_calendar()
    finally:
        monkeypatch.undo()
        dates._calendar.cache_clear()


def test_dates_reject_a_table_with_a_missing_year(monkeypatch: pytest.MonkeyPatch) -> None:
    table = load_table("bs_calendar")
    years = {y: m for y, m in table["years"].items() if y != "2040"}
    monkeypatch.setattr(dates, "load_table", lambda name: {**table, "years": years})
    dates._calendar.cache_clear()
    try:
        with pytest.raises(ValueError, match="gap"):
            dates.load_calendar()
    finally:
        monkeypatch.undo()
        dates._calendar.cache_clear()


def test_not_verified_error_is_a_not_implemented_error() -> None:
    assert issubclass(DataNotVerifiedError, NotImplementedError)


def test_require_verified_rules() -> None:
    with pytest.raises(DataNotVerifiedError):
        require_verified(
            {"status": "draft", "mapping": {"a": "b"}, "sources": ["x"]}, "f", "mapping"
        )
    with pytest.raises(DataNotVerifiedError):
        require_verified({"status": "verified", "mapping": {}, "sources": ["x"]}, "f", "mapping")
    with pytest.raises(DataNotVerifiedError, match="no sources"):
        require_verified(
            {"status": "verified", "mapping": {"a": "b"}, "sources": []}, "f", "mapping"
        )
    ok = {"status": "verified", "mapping": {"a": "b"}, "sources": ["x"]}
    assert require_verified(ok, "f", "mapping") == {"a": "b"}


# --- packaging ---------------------------------------------------------------


def test_public_api_is_importable() -> None:
    for name in aksharkit.__all__:
        assert hasattr(aksharkit, name), name
    assert aksharkit.__version__


def test_package_ships_type_marker_and_data() -> None:
    root = resources.files("aksharkit")
    assert root.joinpath("py.typed").is_file()
    assert (root / "data" / "font_preeti.json").is_file()
    assert (root / "data" / "bs_calendar.json").is_file()


def test_no_runtime_dependencies_declared() -> None:
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text("utf-8")
    assert "\ndependencies = []\n" in pyproject


# --- command line -------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["words", "125000"], "एक लाख पच्चिस हजार"),
        (["words", "१२.५"], "बाह्र दशमलव पाँच"),
        (["words", "--currency", "1250.50"], "एक हजार दुई सय पचास रुपैयाँ पचास पैसा"),
        (["words", "--currency", "--only", "500"], "पाँच सय रुपैयाँ मात्र"),
        (["format", "1234567"], "12,34,567"),
        (["format", "--devanagari", "1234567.5"], "१२,३४,५६७.५"),
        (["digits", "2083-08-07"], "२०८३-०८-०७"),
        (["digits", "--to", "ascii", "२०८३"], "2083"),
        (["normalize", "  राम   घर गयो|  "], "राम घर गयो।"),
        (["normalize", "--no-danda", "राम|"], "राम|"),
        (["normalize", "--joiners", "strip", "र्\u200dयाल"], "र्याल"),
        (["tokenize", "म घर जान्छु।"], "म\nघर\nजान्छु\n।"),
        (["tokenize", "--sentences", "के छ? ठिक छ।"], "के छ?\nठिक छ।"),
    ],
)
def test_cli_output(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 0
    assert capsys.readouterr().out == expected + "\n"


def test_cli_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["tokenize", "--json", "म घर"]) == 0
    assert json.loads(capsys.readouterr().out) == ["म", "घर"]


@pytest.mark.parametrize("argv", [["words"], ["words", "-"]])
def test_cli_reads_stdin(
    argv: list[str], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("42\n"))
    assert main(argv) == 0
    assert capsys.readouterr().out == "बयालिस\n"


@pytest.mark.parametrize("argv", [["words", "abc"], ["format", "1.2.3"], ["words", "1" + "0" * 20]])
def test_cli_bad_input_exits_2(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("aksharkit: error:")


def test_cli_version_and_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert aksharkit.__version__ in capsys.readouterr().out
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2
