"""The browser playground: its Python glue, its archive and its static files.

Nothing here runs a browser or WebAssembly. What is checked:

* ``site/playground.py`` (the only Python the page calls) against the library;
* ``scripts/build_site.py``: the archive holds the package exactly as it is in
  ``src/`` and works on its own, with no installed copy on the path;
* ``site/index.html``, ``app.js`` and ``style.css`` agree with each other;
* ``tests/js/playground.test.mjs`` (run with Node when it is installed), which
  drives ``app.js`` against a fake DOM and a fake Pyodide.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import aksharkit

ROOT = Path(__file__).parent.parent
SITE = ROOT / "site"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


glue = _load("aksharkit_playground", SITE / "playground.py")
build_site = _load("build_site", ROOT / "scripts" / "build_site.py")

INDEX = (SITE / "index.html").read_text("utf-8")
APP = (SITE / "app.js").read_text("utf-8")
STYLE = (SITE / "style.css").read_text("utf-8")


#: The tools the page calls, in tab order. Preeti has a tab but no tool.
PAGE_TOOLS = [
    "normalize",
    "aksharas",
    "numbers",
    "words",
    "dates",
    "calendar",
    "datemath",
    "tokenize",
    "sort",
    "detect",
    "translit",
]


def call(tool: str, **payload: Any) -> dict[str, Any]:
    answer = json.loads(glue.run(tool, json.dumps(payload)))
    assert isinstance(answer, dict)
    return answer


def result(tool: str, **payload: Any) -> dict[str, Any]:
    answer = call(tool, **payload)
    assert answer["ok"], answer
    data = answer["result"]
    assert isinstance(data, dict)
    return data


# --- the glue ------------------------------------------------------------------


def test_glue_uses_only_the_public_api() -> None:
    source = (SITE / "playground.py").read_text("utf-8")
    assert not re.search(r"\bak\._(?!_version__)|\bdates\._|aksharkit\._", source)
    for name in re.findall(r"\bak\.([A-Za-z_]+)", source):
        assert name in aksharkit.__all__, name
    for name in re.findall(r"\bdates\.([A-Za-z_]+)", source):
        assert name in aksharkit.dates.__all__, name


def test_info() -> None:
    info = result("info")
    assert info["version"] == aksharkit.__version__
    assert info["python"] == sys.version.split()[0]
    assert (info["ad_first"], info["ad_last"]) == ("1943-04-14", "2027-04-13")
    # Both are empty once today is past the end of the calendar table.
    assert re.fullmatch(r"(\d{4}-\d{2}-\d{2})?", info["today_ad"])
    assert re.fullmatch(r"(\d{4}-\d{2}-\d{2})?", info["today_bs"])
    assert bool(info["today_ad"]) == bool(info["today_bs"])


def test_info_survives_the_end_of_the_calendar_table(monkeypatch: pytest.MonkeyPatch) -> None:
    def out_of_range() -> aksharkit.BSDate:
        raise aksharkit.DateRangeError("AD 2027-04-14 is outside the verified table")

    monkeypatch.setattr(glue.ak, "today_bs", out_of_range)
    info = result("info")
    assert info["today_ad"] == info["today_bs"] == ""
    assert info["version"] == aksharkit.__version__


def test_normalize() -> None:
    out = result("normalize", text="  राम   घर गयो|  ", joiners="safe", danda=True)
    assert out == {"text": "राम घर गयो।", "changed": True, "before": 17, "after": 11}
    same = result("normalize", text="राम घर गयो।")
    assert same["changed"] is False
    assert result("normalize", text="राम|", danda=False)["text"] == "राम|"
    assert result("normalize", text="र्\u200dय", joiners="strip")["text"] == "र्य"
    assert result("normalize") == {"text": "", "changed": False, "before": 0, "after": 0}
    assert call("normalize", text="x", joiners="nope")["ok"] is False


def test_numbers() -> None:
    out = result("numbers", text="1250500.50", only=True)
    assert out["ascii"] == {"ok": True, "value": "1250500.50"}
    assert out["devanagari"] == {"ok": True, "value": "१२५०५००.५०"}
    assert out["grouped"] == {"ok": True, "value": "12,50,500.50"}
    assert out["grouped_devanagari"] == {"ok": True, "value": "१२,५०,५००.५०"}
    assert out["words"]["value"] == aksharkit.number_to_words("1250500.50")
    assert out["currency"]["value"] == aksharkit.currency_to_words("1250500.50", only=True)
    assert out["currency"]["value"].endswith("मात्र")
    assert not result("numbers", text="५००")["currency"]["value"].endswith("मात्र")
    assert result("numbers", text="१२,३४,५६७")["ascii"]["value"] == "12,34,567"


def test_numbers_report_a_failure_per_row() -> None:
    out = result("numbers", text="1" + "0" * 14)
    assert out["grouped"]["ok"] is True
    assert out["words"]["ok"] is False
    assert out["currency"]["ok"] is False


@pytest.mark.parametrize("text", ["", "   ", "abc", "1.2.3"])
def test_numbers_reject_bad_input(text: str) -> None:
    answer = call("numbers", text=text)
    assert answer["ok"] is False
    assert answer["kind"] == "ValueError"
    assert answer["error"]


def test_dates_both_directions() -> None:
    expected = {
        "bs_iso": "2083-08-07",
        "bs_iso_ne": "२०८३-०८-०७",
        "bs_long": "2083 Mangsir 7, Sombar",
        "bs_long_ne": "२०८३ मंसिर ७, सोमबार",
        "ad_iso": "2026-11-23",
        "ad_long": "23 November 2026, Monday",
        "fiscal_year": "2083/84",
        "fiscal_year_ne": "२०८३/८४",
        "pattern": {"ok": True, "value": "7 Mangsir 2083, Sombar"},
        "pattern_ne": {"ok": True, "value": "७ मंसिर २०८३, सोमबार"},
    }
    pattern = "%-d %B %Y, %A"
    assert result("dates", direction="ad2bs", text="2026-11-23", pattern=pattern) == expected
    assert result("dates", direction="bs2ad", text="२०८३/८/७", pattern=pattern) == expected
    assert result("dates", text=" २०२६-११-२३ ", pattern=pattern) == expected
    for named in ("२०८३ मंसिर ७", "7 Mangsir 2083", "२०८३ साल मंसिर ७ गते, सोमबार"):
        assert result("dates", direction="bs2ad", text=named, pattern=pattern) == expected


def test_dates_pattern_rows_fail_alone() -> None:
    for pattern in ("", "plain text", "%Q", "%"):
        out = result("dates", text="2026-11-23", pattern=pattern)
        assert out["bs_iso"] == "2083-08-07"
        assert out["pattern"]["ok"] is False and out["pattern_ne"]["ok"] is False
        assert out["pattern"]["value"]
    out = result("dates", text="2026-11-23", pattern="%d/%m/%y (%a)")
    assert out["pattern"] == {"ok": True, "value": "07/08/83 (Som)"}
    assert out["pattern_ne"] == {"ok": True, "value": "०७/०८/८३ (सोम)"}
    assert result("dates", text="2026-11-23")["pattern"]["ok"] is False  # no pattern sent


def test_aksharas() -> None:
    out = result("aksharas", text="नमस्ते संसार", limit="4", suffix=True)
    assert out == {
        "units": [
            {"text": "न", "start": 0, "end": 1},
            {"text": "म", "start": 1, "end": 2},
            {"text": "स्ते", "start": 2, "end": 6},
            {"text": " ", "start": 6, "end": 7},
            {"text": "सं", "start": 7, "end": 9},
            {"text": "सा", "start": 9, "end": 11},
            {"text": "र", "start": 11, "end": 12},
        ],
        "count": 7,
        "letters": 6,
        "characters": 12,
        "truncated": {"ok": True, "value": "नमस्ते…"},
    }
    assert [u["text"] for u in out["units"]] == aksharkit.aksharas("नमस्ते संसार")
    assert result("aksharas", text="नमस्ते संसार", limit="४", suffix=False)["truncated"] == {
        "ok": True,
        "value": "नमस्ते ",
    }
    assert result("aksharas", text="नमस्ते", limit="")["truncated"]["value"] == "नमस्ते"
    assert result("aksharas", text="नमस्ते")["truncated"]["value"] == "नमस्ते"
    assert result("aksharas", text="नमस्ते", limit="0")["truncated"]["value"] == "…"
    for bad in ("-1", "1.5", "two"):
        row = result("aksharas", text="नमस्ते", limit=bad)["truncated"]
        assert row["ok"] is False and "whole number" in row["value"]
    assert result("aksharas") == {
        "units": [],
        "count": 0,
        "letters": 0,
        "characters": 0,
        "truncated": {"ok": True, "value": ""},
    }


def test_sort() -> None:
    text = "हात\nकमल\n\nज्ञान\n  क्षेत्र  \nकाम\nकमल"
    out = result("sort", text=text)
    assert out["lines"] == ["कमल", "कमल", "काम", "हात", "क्षेत्र", "ज्ञान"]
    assert out["text"] == "\n".join(out["lines"])
    assert out["count"] == 6
    assert out["lines"] == aksharkit.sorted_nepali(["हात", "कमल", "ज्ञान", "क्षेत्र", "काम", "कमल"])
    under = result("sort", text=text, conjunct_letters=False, unique=True)
    assert under["lines"] == ["कमल", "काम", "क्षेत्र", "ज्ञान", "हात"]
    assert result("sort", text=text, reverse=True)["lines"] == out["lines"][::-1]
    assert result("sort") == {"text": "", "lines": [], "count": 0}
    assert result("sort", text=" \n\n ")["count"] == 0


def test_numbers_ordinal_row() -> None:
    assert result("numbers", text="1", ordinal="5")["ordinal"] == {"ok": True, "value": "पाँचौँ"}
    assert result("numbers", text="1", ordinal=" १०० ")["ordinal"]["value"] == "सयौँ"
    for bad in ("", "0", "101", "1.5", "five", "-2"):
        row = result("numbers", text="1", ordinal=bad)["ordinal"]
        assert row["ok"] is False and row["value"], bad
    assert result("numbers", text="1")["ordinal"]["ok"] is False


@pytest.mark.parametrize(
    ("payload", "kind", "fragment"),
    [
        ({"direction": "ad2bs", "text": "2030-01-01"}, "DateRangeError", "outside"),
        ({"direction": "bs2ad", "text": "2090-01-01"}, "DateRangeError", "outside"),
        ({"direction": "bs2ad", "text": "2083-13-01"}, "DateRangeError", "month"),
        ({"direction": "ad2bs", "text": "23/11/2026"}, "ValueError", "YYYY-MM-DD"),
        ({"direction": "ad2bs", "text": ""}, "ValueError", "YYYY-MM-DD"),
        ({"direction": "bs2ad", "text": "2062-02-10"}, "DisputedDateError", "disagree"),
        ({"direction": "ad2bs", "text": "2005-05-20"}, "DisputedDateError", "disagree"),
        ({"direction": "sideways", "text": "2026-11-23"}, "ValueError", "direction"),
    ],
)
def test_dates_errors(payload: dict[str, Any], kind: str, fragment: str) -> None:
    answer = call("dates", **payload)
    assert answer["ok"] is False
    assert answer["kind"] == kind
    assert fragment in answer["error"]


def test_dates_disputed_span_can_be_allowed() -> None:
    out = result("dates", direction="bs2ad", text="2062-02-10", allow_disputed=True)
    assert out["ad_iso"] == "2005-05-23"


def test_tokenize() -> None:
    out = result("tokenize", text="डा. राम आए। मूल्य रु. 99.50 हो। ठिक छ?")
    assert out["sentences"] == ["डा. राम आए।", "मूल्य रु. 99.50 हो।", "ठिक छ?"]
    texts = [t["text"] for t in out["tokens"]]
    assert texts == aksharkit.tokenize("डा. राम आए। मूल्य रु. 99.50 हो। ठिक छ?")
    assert {t["kind"] for t in out["tokens"]} == {"word", "number", "punct"}
    assert [t["text"] for t in out["tokens"] if t["stop"]] == ["हो", "छ"]
    assert out["words"] == sum(1 for t in out["tokens"] if t["kind"] == "word")
    assert result("tokenize", text="") == {"tokens": [], "sentences": [], "words": 0}


def test_translit() -> None:
    text = "नमस्ते, नेपाल राम्रो छ। धन्यवाद!"
    iast = result("translit", text=text, scheme="iast", direction="roman")
    assert iast == {
        "text": "namaste, nepāla rāmro cha| dhanyavāda!",
        "approximate": False,
        "lang": "ne-Latn",
    }
    back = result("translit", text=iast["text"], scheme="iast", direction="devanagari")
    assert back["text"] == text
    assert back["lang"] == "ne"
    simple = result("translit", text=text, scheme="simple")
    assert simple["text"] == "namaste, nepal ramro chha. dhanyavad!"
    assert simple["approximate"] is True
    assert call("translit", text="क", scheme="hk")["kind"] == "ValueError"
    assert call("translit", text="क", direction="up")["kind"] == "ValueError"


def test_words_to_number() -> None:
    out = result("words", text="  एक लाख पच्चीस हजार ")
    assert out == {
        "number": {"ok": True, "value": "125000"},
        "grouped": {"ok": True, "value": "1,25,000"},
        "grouped_devanagari": {"ok": True, "value": "१,२५,०००"},
        "respelt": {"ok": True, "value": "एक लाख पच्चिस हजार"},
    }
    money = result("words", text="दुई सय रुपैयाँ पचास पैसा मात्र")
    assert money["number"]["value"] == "200.50"
    assert result("words", text="ऋण बाह्र दशमलव पाँच")["number"]["value"] == "-12.5"
    for bad in ("", "  ", "एक एक", "hello", "12"):
        answer = call("words", text=bad)
        assert answer["ok"] is False
        assert answer["kind"] == "ValueError"
        assert answer["error"]


def test_detect() -> None:
    out = result("detect", text="म school जान्छु 5")
    assert out["script"] == "mixed"
    assert out["counts"] == {"devanagari": 7, "latin": 6, "digit": 1, "other": 0}
    assert out["shares"]["devanagari"] == pytest.approx(0.5)
    assert out["tokens"] == [
        {"text": "म", "script": "devanagari"},
        {"text": "school", "script": "latin"},
        {"text": "जान्छु", "script": "devanagari"},
        {"text": "5", "script": "digits"},
    ]
    assert out["romanised"] is False
    assert out["romanised_score"] == 0.0
    chat = result("detect", text="timi kasto cha? malai ramro lagyo")
    assert chat["script"] == "latin"
    assert chat["romanised"] is True
    assert chat["romanised_score"] == pytest.approx(5 / 6)
    empty = result("detect")
    assert empty["script"] == "none"
    assert empty["tokens"] == []


def test_calendar() -> None:
    out = result("calendar", text="2083-08", devanagari=False)
    assert out["title"] == "Mangsir 2083"
    assert out["head"] == ["Aai", "Som", "Man", "Bud", "Bih", "Shu", "Sha"]
    assert out["weeks"][0] == ["", "", "1", "2", "3", "4", "5"]
    assert out["weeks"][-1] == ["27", "28", "29", "", "", "", ""]
    assert all(len(week) == 7 for week in out["weeks"])
    assert out["span"] == "29 days: 17 November 2026 to 15 December 2026"
    assert out["text"] == aksharkit.format_month_calendar(2083, 8)
    assert out["lang"] == "en"
    nepali = result("calendar", text=" २०८३/८ ")
    assert nepali["title"] == "मंसिर २०८३"
    assert nepali["weeks"][0] == ["", "", "१", "२", "३", "४", "५"]
    assert nepali["lang"] == "ne"
    allowed = result("calendar", text="2062-02", allow_disputed=True, devanagari=False)
    assert allowed["title"] == "Jestha 2062"


@pytest.mark.parametrize(
    ("text", "kind", "fragment"),
    [
        ("", "ValueError", "YYYY-MM"),
        ("2083", "ValueError", "YYYY-MM"),
        ("2083-08-07", "ValueError", "YYYY-MM"),
        ("2083-13", "DateRangeError", "month"),
        ("2084-01", "DateRangeError", "outside"),
        ("2062-01", "DisputedDateError", "disagree"),
    ],
)
def test_calendar_errors(text: str, kind: str, fragment: str) -> None:
    answer = call("calendar", text=text)
    assert answer["ok"] is False
    assert answer["kind"] == kind
    assert fragment in answer["error"]


def test_datemath() -> None:
    out = result("datemath", text="2059-05-12", months="1", days="30", until="2083-08-07")
    assert {key: row["value"] for key, row in out.items()} == {
        "moved": "2059-07-11",
        "moved_ne": "२०५९ कात्तिक ११, सोमबार",
        "moved_ad": "28 October 2002",
        "until": "2083-08-07",
        "gap": "24 years, 2 months, 25 days",
        "days": "8853",
        "age": "24",
    }
    assert all(row["ok"] for row in out.values())
    assert result("datemath", text="२०८३-०३-३२", months="१")["moved"]["value"] == "2083-04-31"
    back = result("datemath", text="2083-08-07", days="-7", until="2080-01-01")
    assert back["moved"] == {"ok": True, "value": "2083-07-30"}
    assert back["days"] == {"ok": True, "value": "-1319"}
    assert back["gap"]["ok"] is False and "before the start date" in back["gap"]["value"]
    assert back["age"]["ok"] is False
    far = result("datemath", text="2083-08-07", days="100000", until="2083-08-07")
    assert far["moved"]["ok"] is False and "outside" in far["moved"]["value"]
    assert far["gap"] == {"ok": True, "value": "0 years, 0 months, 0 days"}


def test_datemath_counts_up_to_today_when_no_end_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(glue.ak, "today_bs", lambda: aksharkit.BSDate(2083, 8, 8))
    out = result("datemath", text="2060-08-08")
    assert out["until"]["value"] == "2083-08-08"
    assert out["age"]["value"] == "23"


@pytest.mark.parametrize(
    ("payload", "kind"),
    [
        ({"text": ""}, "ValueError"),
        ({"text": "yesterday"}, "ValueError"),
        ({"text": "2090-01-01"}, "DateRangeError"),
        ({"text": "2083-08-07", "days": "1.5"}, "ValueError"),
        ({"text": "2083-08-07", "months": "two"}, "ValueError"),
    ],
)
def test_datemath_errors(payload: dict[str, Any], kind: str) -> None:
    answer = call("datemath", **payload)
    assert answer["ok"] is False
    assert answer["kind"] == kind


def test_datemath_disputed_rows_fail_one_by_one() -> None:
    out = result("datemath", text="2062-02-10", until="2083-08-07")
    assert out["moved"]["ok"] is False and "disagree" in out["moved"]["value"]
    assert out["age"]["ok"] is False
    allowed = result("datemath", text="2062-02-10", until="2083-08-07", allow_disputed=True)
    assert all(row["ok"] for row in allowed.values())


@pytest.mark.parametrize(
    ("tool", "payload"),
    [("nope", "{}"), ("normalize", "not json"), ("normalize", "[1, 2]"), ("numbers", "null")],
)
def test_run_never_raises(tool: str, payload: str) -> None:
    answer = json.loads(glue.run(tool, payload))
    assert answer["ok"] is False
    assert answer["error"]


def test_every_tool_the_page_uses_exists() -> None:
    tools = re.search(r"const TOOLS = \[([^\]]+)\]", APP)
    assert tools is not None
    names = re.findall(r'"([a-z]+)"', tools.group(1))
    assert names == PAGE_TOOLS
    assert set(names) | {"info"} == set(glue.TOOLS)


# --- the archive ------------------------------------------------------------------


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site") / "_site"
    build_site.build(out)
    return out


def test_build_copies_the_static_files_and_leaves_the_glue_out(built: Path) -> None:
    names = sorted(p.relative_to(built).as_posix() for p in built.rglob("*") if p.is_file())
    assert names == [
        ".nojekyll",
        "app.js",
        "index.html",
        "pkg/aksharkit.zip",
        "pkg/manifest.json",
        "style.css",
    ]
    for name in ("app.js", "style.css"):
        assert (built / name).read_bytes() == (SITE / name).read_bytes()


def test_built_page_stamps_its_assets_so_an_update_is_never_half_cached(built: Path) -> None:
    stamp = build_site.asset_stamp(built)
    assert re.fullmatch(r"[0-9a-f]{12}", stamp)
    page = (built / "index.html").read_text("utf-8")
    assert f'src="app.js?v={stamp}"' in page
    assert f'href="style.css?v={stamp}"' in page
    # Apart from the two stamps the page is the source page.
    assert page.replace("?v=" + stamp, "") == INDEX
    # app.js passes its own stamp on to the archive request.
    assert "fetch(PACKAGE_ARCHIVE + ASSET_QUERY)" in APP


def test_archive_is_the_package_as_it_is_in_src(built: Path) -> None:
    package = ROOT / "src" / "aksharkit"
    with zipfile.ZipFile(built / "pkg" / "aksharkit.zip") as archive:
        names = archive.namelist()
        assert archive.testzip() is None
        for name in names:
            source = (
                SITE / "playground.py"
                if name == "aksharkit_playground.py"
                else package / name.removeprefix("aksharkit/")
            )
            assert archive.read(name) == source.read_bytes(), name
    expected = {
        "aksharkit/" + p.relative_to(package).as_posix()
        for p in package.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert set(names) == expected | {"aksharkit_playground.py"}
    assert len(names) == len(set(names))
    assert {"aksharkit/py.typed", "aksharkit/data/bs_calendar.json"} <= set(names)
    assert not any(n.endswith((".pyc", ".pyo")) for n in names)


def test_manifest_matches_the_archive(built: Path) -> None:
    manifest = json.loads((built / "pkg" / "manifest.json").read_text("utf-8"))
    data = (built / "pkg" / "aksharkit.zip").read_bytes()
    assert manifest["version"] == aksharkit.__version__
    assert manifest["archive"] == "pkg/aksharkit.zip"
    assert manifest["sha256"] == hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(built / "pkg" / "aksharkit.zip") as archive:
        assert manifest["files"] == archive.namelist()


def test_build_is_reproducible(built: Path, tmp_path: Path) -> None:
    again = tmp_path / "again"
    build_site.build(again)
    first = (built / "pkg" / "aksharkit.zip").read_bytes()
    assert (again / "pkg" / "aksharkit.zip").read_bytes() == first


def test_archive_works_alone_without_an_installed_package(built: Path, tmp_path: Path) -> None:
    """Unpack it the way the page does and call the glue with a bare interpreter."""
    target = tmp_path / "unpacked"
    shutil.unpack_archive(built / "pkg" / "aksharkit.zip", target, "zip")
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import aksharkit_playground as g; "
        "import aksharkit; assert aksharkit.__file__.startswith(sys.argv[1]), aksharkit.__file__; "
        "sys.stdout.reconfigure(encoding='utf-8'); "
        "print(g.run('info', '{}')); print(g.run('dates', sys.argv[2])); "
        "print(g.run('translit', sys.argv[3])); print(g.run('aksharas', sys.argv[3])); "
        "print(g.run('sort', sys.argv[4]))"
    )
    done = subprocess.run(
        [sys.executable, "-S", "-E", "-c", code, str(target),
         json.dumps({"text": "2026-11-23"}), json.dumps({"text": "नेपाल"}),
         json.dumps({"text": "ज्ञ\nक"})],
        capture_output=True, encoding="utf-8", check=False,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    info, date, roman, units, ordered = (json.loads(line) for line in done.stdout.splitlines())
    assert units["result"]["count"] == 3
    assert ordered["result"]["lines"] == ["क", "ज्ञ"]
    assert info["result"]["version"] == aksharkit.__version__
    assert date["result"]["bs_iso"] == "2083-08-07"
    assert roman["result"]["text"] == "nepāla"


# --- the static files ----------------------------------------------------------------


def _ids() -> list[str]:
    return re.findall(r'\sid="([^"]+)"', INDEX)


def test_html_ids_are_unique_and_every_id_the_script_needs_exists() -> None:
    ids = _ids()
    assert len(ids) == len(set(ids))
    wanted = set(re.findall(r'byId\("([^"]+)"\)', APP))
    assert wanted, "app.js should look elements up by id"
    assert wanted <= set(ids), wanted - set(ids)
    for tool in PAGE_TOOLS:
        assert f"err-{tool}" in ids
        assert f"tab-{tool}" in ids
        assert f"panel-{tool}" in ids


def test_tabs_and_panels_are_wired_for_assistive_technology() -> None:
    tabs = re.findall(
        r'<button type="button" role="tab" id="([^"]+)" aria-controls="([^"]+)"', INDEX
    )
    panels = re.findall(
        r'<section class="panel" role="tabpanel" id="([^"]+)" aria-labelledby="([^"]+)"', INDEX
    )
    assert [t[0] for t in tabs] == [f"tab-{tool}" for tool in PAGE_TOOLS] + ["tab-preeti"]
    assert [(panel, tab) for tab, panel in tabs] == panels
    assert INDEX.count('aria-selected="true"') == 1
    assert INDEX.count('role="tablist"') == 1
    assert INDEX.count("<section") - INDEX.count('" hidden>\n      <h2>') == 1  # one panel visible
    assert "Coming soon — needs a verified mapping" in INDEX


def test_every_form_control_has_a_label() -> None:
    controls = re.findall(r"<(?:input|select|textarea)\b[^>]*>", INDEX)
    assert len(controls) >= 12
    labelled = set(re.findall(r'<label for="([^"]+)"', INDEX))
    for control in controls:
        match = re.search(r'\sid="([^"]+)"', control)
        assert match is not None, control
        wrapped = re.search(r'<label class="check">\s*' + re.escape(control), INDEX)
        assert match.group(1) in labelled or wrapped, control
    assert '<html lang="en">' in INDEX
    assert 'name="viewport"' in INDEX


def test_every_output_the_script_writes_has_a_place_on_the_page() -> None:
    outs = set(re.findall(r'data-out="([a-z_.]+)"', INDEX))
    for key in re.findall(r'setOut\(\s*"([a-z_.]+)"', APP):
        if key.endswith("."):  # a prefix: keys are added from the result
            continue
        assert key in outs, key
    row_tools = {
        "numbers": result("numbers", text="1"),
        "dates": result("dates", text="2026-11-23"),
        "aksharas": {"truncated": None},
        "words": result("words", text="एक"),
        "datemath": result("datemath", text="2083-08-07"),
    }
    for tool, rows in row_tools.items():
        for key in rows:
            assert f"{tool}.{key}" in outs, (tool, key)
    for key in ("calendar.title", "calendar.span", "calendar.text"):
        assert key in outs
    for key in ("detect.script", "detect.shares", "detect.romanised"):
        assert key in outs
    for key in ("aksharas.count", "sort.text", "sort.count"):
        assert key in outs
    for key in re.findall(r'data-copy="([a-z_.]+)"', INDEX):
        assert key in outs, key
    for tool, field in re.findall(r'data-tool="([a-z]+)" data-field="([a-z_]+)"', INDEX):
        assert tool in glue.TOOLS
        assert f'"{field}"' in (SITE / "playground.py").read_text("utf-8"), (tool, field)


def test_every_result_can_be_copied() -> None:
    copies = set(re.findall(r'data-copy="([a-z_.]+)"', INDEX))
    outputs = re.findall(r'<output\b[^>]*data-out="([a-z_.]+)"', INDEX)
    assert len(outputs) >= 35
    # The calendar title and span are captions; the grid is copied as calendar.text.
    assert set(outputs) - copies == {"calendar.title", "calendar.span"}
    lists = re.findall(r'data-copy-list="([a-z-]+)"', INDEX)
    assert sorted(lists) == [
        "out-aksharas-units",
        "out-detect-tokens",
        "out-tokenize-sentences",
        "out-tokenize-tokens",
    ]
    assert set(lists) <= set(_ids())
    for button in re.findall(r'<button type="button" class="copy"[^>]*>', INDEX):
        assert "aria-label=" in button, button
    assert 'id="btn-share"' in INDEX


def test_examples_fill_real_inputs() -> None:
    examples = re.findall(r'data-example="([a-z-]+)" data-value="([^"]+)"', INDEX)
    targets = {target for target, _ in examples}
    assert targets == {f"in-{tool}" for tool in PAGE_TOOLS}
    for target in targets:
        assert len([1 for t, _ in examples if t == target]) >= 3, target
        assert re.search(rf'<(?:input|textarea) id="{target}" data-tool="[a-z]+"', INDEX), target


@pytest.mark.parametrize(
    ("tool", "target"),
    [
        ("numbers", "in-numbers"),
        ("words", "in-words"),
        ("dates", "in-dates"),
        ("calendar", "in-calendar"),
        ("datemath", "in-datemath"),
        ("aksharas", "in-aksharas"),
        ("sort", "in-sort"),
    ],
)
def test_examples_are_accepted_by_the_library(tool: str, target: str) -> None:
    values = re.findall(rf'data-example="{target}" data-value="([^"]+)"', INDEX)
    assert values
    for value in values:
        assert call(tool, text=value.replace("&#10;", "\n"))["ok"], (tool, value)


def test_sort_examples_have_one_item_per_line() -> None:
    values = re.findall(r'data-example="in-sort" data-value="([^"]+)"', INDEX)
    assert len(values) == 3
    differ = 0
    for value in values:
        lines = value.split("&#10;")
        assert len(lines) >= 8
        assert result("sort", text="\n".join(lines))["count"] == len(lines)
        differ += sorted(lines) != aksharkit.sorted_nepali(lines)
    assert differ >= 2  # most examples show what a code-point sort gets wrong


def test_devanagari_output_is_marked_as_nepali() -> None:
    for tag in re.findall(r"<output\b[^>]*>", INDEX):
        key = re.search(r'data-out="([a-z_.]+)"', tag)
        assert key is not None
        nepali = key.group(1).endswith(
            ("_ne", "devanagari", ".words", ".currency", ".respelt", ".ordinal", ".truncated")
        )
        if nepali or key.group(1) in ("normalize.text", "sort.text"):
            assert 'lang="ne"' in tag, tag
    # Outputs whose script depends on the input get their lang from the script.
    assert 'setAttribute("lang", r.lang)' in APP
    assert 'chip.setAttribute("lang", "ne")' in APP
    for list_id in (
        "out-tokenize-tokens",
        "out-tokenize-sentences",
        "out-aksharas-units",
        "out-sort-lines",
    ):
        assert re.search(rf'id="{list_id}"[^>]*lang="ne"', INDEX)


def test_state_lives_in_the_address_and_nowhere_else() -> None:
    assert "history.replaceState" in APP
    assert "location.hash" in APP
    assert "hashchange" in APP
    # An edit only rewrites the address while its own tab is on screen.
    assert "if (fromUser && tool === currentTabName()) {" in APP
    for word in ("sessionStorage", "indexedDB", "document.cookie", "sendBeacon", "XMLHttpRequest"):
        assert word not in APP, word
    assert APP.count("fetch(") == 1  # only the package archive


def test_phone_layout_rules() -> None:
    def block(selector: str) -> str:
        match = re.search(rf"\n\n{re.escape(selector)} \{{\n(.*?)\n\}}", STYLE, re.DOTALL)
        assert match is not None, selector
        return match.group(1)

    assert "overflow-x: auto" in block(".tabs")
    assert "flex: none" in block('.tabs [role="tab"]')
    for selector in ('.tabs [role="tab"]', ".example", ".check"):
        assert "min-height: 2.75rem" in block(selector), selector  # 44px at 16px
    assert "min-height: 2.75rem" in STYLE.split(".button,\n.copy {")[1].split("}")[0]
    for rule in ("min-height: 2.75rem", "min-width: 2.75rem"):
        assert rule in block(".copy"), rule
    assert "overflow-wrap: anywhere" in block(".out")
    assert "overflow-x: auto" in block(".grid-wrap")
    # Nothing is given a fixed width that could be wider than a 360px screen.
    phone = STYLE.split("@media (min-width: 40rem)")[0]
    assert not re.search(r"(?<!max-)(?<!min-)width: \d{3,}px", phone)
    assert not re.search(r"min-width: (?:\d{3,}px|[2-9]\d(?:\.\d+)?rem)", phone)
    assert "white-space: nowrap" not in block(".out")


def test_preeti_help_wanted_link() -> None:
    link = '<a class="button ghost link" href="https://github.com/Samir-Khadka/aksharkit/issues">'
    assert link + "Preeti: help wanted</a>" in INDEX
    assert INDEX.count("https://github.com/Samir-Khadka/aksharkit/issues") == 2


def test_the_page_loads_nothing_from_other_sites_except_pyodide() -> None:
    for text in (INDEX, STYLE):
        assert "@import" not in text
        assert "fonts.googleapis" not in text and "gstatic" not in text
        assert not re.search(r'(?:src|href)="(?:https?:)?//(?!github\.com|pyodide\.org)', text)
        assert not re.search(r"url\(\s*['\"]?(?:https?:)?//", text)
    assert re.findall(r'<script[^>]*src="([^"]+)"', INDEX) == ["app.js"]
    assert re.findall(r'<link rel="stylesheet" href="([^"]+)"', INDEX) == ["style.css"]
    hosts = set(re.findall(r"https?://([a-z0-9.-]+)", APP))
    assert hosts == {"cdn.jsdelivr.net"}
    for word in ("analytics", "gtag", "cookie", "localStorage", "innerHTML", "eval("):
        assert word not in APP, word


def test_pyodide_is_pinned_to_one_exact_version() -> None:
    version = re.search(r'const PYODIDE_VERSION = "(\d+\.\d+\.\d+)";', APP)
    assert version is not None
    assert version.group(1) == "0.29.5"
    assert '"https://cdn.jsdelivr.net/pyodide/v" + PYODIDE_VERSION + "/full/"' in APP
    assert re.search(r'"sha384-[A-Za-z0-9+/]{64}"', APP)
    assert "latest" not in APP


def _luminance(colour: str) -> float:
    parts = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_palette_is_light_and_text_meets_wcag_aa() -> None:
    palette = dict(re.findall(r"--([a-z-]+): (#[0-9a-f]{6});", STYLE))
    for background in ("ivory", "paper", "violet-soft", "gold-soft", "error-soft"):
        assert _luminance(palette[background]) > 0.8, background  # no dark surfaces
    pairs = [
        ("ink", "ivory"),
        ("ink", "paper"),
        ("ink-soft", "ivory"),
        ("ink-soft", "paper"),
        ("violet", "ivory"),
        ("violet", "paper"),
        ("violet-deep", "violet-soft"),
        ("gold-deep", "ivory"),
        ("gold-deep", "paper"),
        ("gold-deep", "gold-soft"),
        ("error", "error-soft"),
    ]
    for text, background in pairs:
        ratio = _contrast(palette[text], palette[background])
        assert ratio >= 4.5, (text, background, round(ratio, 2))
    assert _contrast("#ffffff", palette["violet"]) >= 4.5
    assert "prefers-reduced-motion" in STYLE
    assert ":focus-visible" in STYLE


# --- the workflow -----------------------------------------------------------------


def test_pages_workflow_builds_with_the_same_script() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text("utf-8")
    for action in (
        "actions/checkout@",
        "actions/configure-pages@",
        "actions/upload-pages-artifact@",
        "actions/deploy-pages@",
    ):
        assert action in workflow, action
    assert "python scripts/build_site.py --out _site" in workflow
    assert "path: _site" in workflow
    assert "branches: [main]" in workflow
    assert "pages: write" in workflow and "id-token: write" in workflow


# --- app.js against a fake browser ------------------------------------------------


def test_app_js_in_node(built: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    check = subprocess.run(
        [node, "--check", str(SITE / "app.js")], capture_output=True, text=True, check=False
    )
    assert check.returncode == 0, check.stderr
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=False)
    if int(version.stdout.strip().lstrip("v").split(".")[0]) < 20:
        pytest.skip(f"Node.js {version.stdout.strip()} is too old for the page tests")
    done = subprocess.run(
        [node, "--test", str(ROOT / "tests" / "js" / "playground.test.mjs")],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "AKSHARKIT_SITE": str(built), "AKSHARKIT_PYTHON": sys.executable},
    )
    assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-2000:]
