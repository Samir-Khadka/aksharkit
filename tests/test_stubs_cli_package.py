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

# --- stubs: legacy fonts and dates must refuse, never guess -----------------


@pytest.mark.parametrize("name", ["font_preeti", "bs_calendar"])
def test_data_tables_are_marked_unverified_and_empty(name: str) -> None:
    table = load_table(name)
    assert table["status"] == "UNVERIFIED-EMPTY"
    assert table["sources"] == []
    payload = table["mapping"] if name == "font_preeti" else table["years"]
    assert payload == {}


def test_preeti_refuses_without_verified_data() -> None:
    for call in (
        lambda: legacy.preeti_to_unicode("g]kfn"),
        lambda: legacy.unicode_to_preeti("नेपाल"),
        lambda: legacy.to_unicode("g]kfn", "Preeti"),
        lambda: legacy.load_font_map("preeti"),
    ):
        with pytest.raises(DataNotVerifiedError, match="not available yet"):
            call()


def test_unknown_font_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="unknown font"):
        legacy.to_unicode("x", "kantipur")


def test_dates_refuse_without_verified_data() -> None:
    for call in (
        lambda: dates.bs_to_ad(2083, 8, 7),
        lambda: dates.ad_to_bs(dt.date(2026, 11, 23)),
        dates.load_calendar,
    ):
        with pytest.raises(DataNotVerifiedError, match="not available yet"):
            call()


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


def test_month_names() -> None:
    assert len(dates.BS_MONTHS) == 12
    assert len(set(dates.BS_MONTHS)) == 12


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


@pytest.mark.parametrize("argv", [["convert", "preeti", "g]kfn"], ["date", "2083-08-07"]])
def test_cli_unavailable_features_exit_3(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not available yet" in captured.err


def test_cli_version_and_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert aksharkit.__version__ in capsys.readouterr().out
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2
