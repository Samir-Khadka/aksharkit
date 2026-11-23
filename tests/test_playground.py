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
    }
    assert result("dates", direction="ad2bs", text="2026-11-23") == expected
    assert result("dates", direction="bs2ad", text="२०८३/८/७") == expected
    assert result("dates", text=" २०२६-११-२३ ") == expected


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
    assert iast == {"text": "namaste, nepāla rāmro cha| dhanyavāda!", "approximate": False}
    back = result("translit", text=iast["text"], scheme="iast", direction="devanagari")
    assert back["text"] == text
    simple = result("translit", text=text, scheme="simple")
    assert simple == {"text": "namaste, nepal ramro chha. dhanyavad!", "approximate": True}
    assert call("translit", text="क", scheme="hk")["kind"] == "ValueError"
    assert call("translit", text="क", direction="up")["kind"] == "ValueError"


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
    assert names == ["normalize", "numbers", "dates", "tokenize", "translit"]
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
    for name in ("app.js", "index.html", "style.css"):
        assert (built / name).read_bytes() == (SITE / name).read_bytes()


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
        "print(g.run('translit', sys.argv[3]))"
    )
    done = subprocess.run(
        [sys.executable, "-S", "-E", "-c", code, str(target),
         json.dumps({"text": "2026-11-23"}), json.dumps({"text": "नेपाल"})],
        capture_output=True, encoding="utf-8", check=False,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    info, date, roman = (json.loads(line) for line in done.stdout.splitlines())
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
    for tool in ("normalize", "numbers", "dates", "tokenize", "translit"):
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
    assert [t[0] for t in tabs] == [
        "tab-normalize",
        "tab-numbers",
        "tab-dates",
        "tab-tokenize",
        "tab-translit",
        "tab-preeti",
    ]
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
    numbers = result("numbers", text="1")
    dates = result("dates", text="2026-11-23")
    for key in numbers:
        assert f"numbers.{key}" in outs
    for key in dates:
        assert f"dates.{key}" in outs
    for key in re.findall(r'data-copy="([a-z_.]+)"', INDEX):
        assert key in outs, key
    for tool, field in re.findall(r'data-tool="([a-z]+)" data-field="([a-z_]+)"', INDEX):
        assert tool in glue.TOOLS
        assert f'"{field}"' in (SITE / "playground.py").read_text("utf-8"), (tool, field)


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
