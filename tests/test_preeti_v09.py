"""Preeti in 0.9: what real documents changed.

The 0.8 table was the part on which other projects' tables agree. For 0.9
nine public PDFs that embed a font named Preeti were converted and compared
by eye with their page images (see ``docs/preeti.md``, "Tested on real
documents"). These tests pin what that changed:

* keys the tables left open and the documents settle;
* typing habits of real typists the converter now follows;
* the real excerpts in ``tests/golden/preeti_samples.tsv``, in both directions;
* the evidence file, the table built from it, and the script that recounts.

The PDFs are not in the repository, so nothing here needs them.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import aksharkit
from aksharkit import convert_preeti, encode_preeti, legacy
from aksharkit._data import load_table
from aksharkit.cli import main

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"
TABLE: dict[str, Any] = load_table("font_preeti")
EVIDENCE: dict[str, Any] = json.loads(
    (ROOT / "scripts" / "preeti_evidence.json").read_text("utf-8")
)


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORPUS = _script("preeti_corpus")


def _samples() -> list[tuple[str, str, str]]:
    rows = []
    for line in (GOLDEN / "preeti_samples.tsv").read_text("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            keys, text, origin = line.split("\t")
            rows.append((keys, text, origin))
    return rows


SAMPLES = _samples()

# --- keys the documents settle -----------------------------------------------------


@pytest.mark.parametrize(
    ("keys", "text"),
    [
        ("u¥of]", "गर्\u200dयो"),
        ("k'¥ofpg", "पुर्\u200dयाउन"),
        ("e¥ofª", "भर्\u200dयाङ"),
        ("…sÚ", "‘क’"),
        ("hft–hflt", "जात–जाति"),
        ("d'2fM—", "मुद्दाः—"),
        ("ztmL", "शक्ती"),
        (";+o'tm", "संयुक्त"),
    ],
)
def test_settled_keys_convert_both_ways(keys: str, text: str) -> None:
    forward = convert_preeti(keys)
    assert forward.text == text and forward.complete
    back = encode_preeti(text)
    assert back.complete
    assert convert_preeti(back.text, keep_links=False).text == text


def test_settled_keys_are_written_with_their_own_key() -> None:
    assert encode_preeti("गर्\u200dयो").text == "u¥of]"
    assert encode_preeti("‘क’").text == "…sÚ"
    assert encode_preeti("क–ख क—ख").text == "s–v s—v"
    # Two key sequences write क्त; the one from the tables is still the one written.
    assert encode_preeti("शक्ति").text == "zlQm"


def test_strict_leaves_the_settled_keys_out() -> None:
    result = convert_preeti("u¥of] …sÚ", strict=True)
    assert [item.char for item in result.unmapped] == ["¥", "Ú"]
    assert "¥" not in legacy.load_font_map(strict=True)
    assert legacy.load_font_map()["¥"] == "र्\u200d"
    assert legacy.load_font_map()["Ú"] == "’"


def test_keys_still_open_stay_unmapped() -> None:
    assert sorted(TABLE["disputed"]) == ["°", "Ì", "Ý"]
    result = convert_preeti("s ° Ì Ý")
    assert [item.char for item in result.unmapped] == ["°", "Ì", "Ý"]
    # The nukta key was never seen in a document: ड़ and ढ़ stay unconfirmed.
    assert sorted(TABLE["unconfirmed_sequences"]) == ["8Þ", "9Þ"]
    assert not encode_preeti("पढ़").complete


# --- typing habits of real typists ---------------------------------------------------


@pytest.mark.parametrize(
    ("keys", "text", "why"),
    [
        ("pk]|tL", "उप्रेती", "the ra stroke typed after the vowel sign"),
        ("6]«g", "ट्रेन", "the same with the stroke for round letters"),
        ("pTk]|/0ff", "उत्प्रेरणा", "in a longer word"),
        ("kªl\\Qm", "पङ्क्ति", "short i typed between a letter and its halant"),
        ("a'e\\mg", "बुझ्न", "the stroke key typed after the halant"),
        ("jfli{fs", "वार्षिक", "reph typed between a half form and its bar"),
        ("sf]]", "को", "a sign with no width typed twice prints once"),
        ("k||ltlglw", "प्रतिनिधि", "the ra stroke typed twice"),
        ("nfO{{", "लाई", "the reph typed twice"),
        ("s'' g++", "कु नं", "other signs typed twice"),
        ("atfcf,] u", "बताओ, ग", "a sign typed after the comma lands before it"),
    ],
)
def test_typing_habits_seen_in_real_documents(keys: str, text: str, why: str) -> None:
    result = convert_preeti(keys)
    assert result.text == text, why
    assert result.complete, why


def test_habits_do_not_reach_further_than_the_evidence() -> None:
    # Two different signs are both kept: only the same key twice is merged.
    assert convert_preeti("s]}").text == "केै"
    # A sign after a comma that follows a space has no letter to land on.
    assert convert_preeti("s ,]").text == "क ,े"
    # A doubled key is counted as converted, not as unmapped.
    stats = convert_preeti("sf]]").stats
    assert (stats.agreed, stats.unmapped) == (4, 0)
    # A ra stroke with no vowel sign before it stays where it was typed.
    assert convert_preeti("k|]d").text == "प्रेम" == convert_preeti("k]|d").text


def test_two_ra_strokes_in_a_row_are_not_written_as_one_key_twice() -> None:
    result = encode_preeti("क्र्र")
    assert result.complete and "||" not in result.text
    assert convert_preeti(result.text, keep_links=False).text == "क्र्र"


def test_conjuncts_with_a_never_seen_key_are_spelt_with_keys_that_were_seen() -> None:
    unseen = set(TABLE["sight"]["never_seen"])
    for text in ("हृदय", "बुझ्न", "शृङ्खला", "पद्म", "ध्रुव", "झ्याल"):
        result = encode_preeti(text)
        assert result.complete, text
        assert not unseen.intersection(result.text), (text, result.text)
        assert convert_preeti(result.text, keep_links=False).text == text
    # Reading is unchanged: the never-seen keys still convert.
    assert convert_preeti("Åbo").text == "हृदय"
    assert convert_preeti("a'‰g").text == "बुझ्न"


# --- the real excerpts ----------------------------------------------------------------


def test_real_samples_come_from_seven_publishers() -> None:
    assert len(SAMPLES) == 26
    publishers = {origin.split(",")[0] for _, _, origin in SAMPLES}
    assert len(publishers) == 7
    for _, _, origin in SAMPLES:
        assert re.search(r"https://\S+, page \d+$", origin), origin
        assert any(doc["url"] in origin for doc in TABLE["documents"]), origin


@pytest.mark.parametrize(("keys", "text", "origin"), SAMPLES)
def test_real_sample_converts_to_what_the_page_prints(keys: str, text: str, origin: str) -> None:
    result = convert_preeti(keys)
    assert result.text == text, origin
    assert result.complete, origin
    assert convert_preeti(keys, include_unconfirmed=True).text == text, origin


@pytest.mark.parametrize(("keys", "text", "origin"), SAMPLES)
def test_real_sample_goes_back_to_keys_that_read_the_same(
    keys: str, text: str, origin: str
) -> None:
    result = encode_preeti(text)
    assert result.complete, origin
    assert convert_preeti(result.text, keep_links=False).text == text, origin


def test_how_often_the_keys_written_are_the_typists_own() -> None:
    same = sum(1 for keys, text, _ in SAMPLES if encode_preeti(text).text == keys)
    # The rest differ only in spelling habits (s]Gb| / s]G›, hUUff / hUuf) or
    # in the typing slips the converter tidies; all read back the same.
    assert same == 15


# --- evidence file, table and scripts ---------------------------------------------------


def test_evidence_names_nine_documents_from_seven_publishers() -> None:
    documents = EVIDENCE["documents"]
    assert len(documents) == 9
    assert len({doc["publisher"] for doc in documents}) == 7
    for doc in documents:
        assert doc["url"].startswith("https://") and doc["pages"] > 0
        assert doc["font"].endswith("+Preeti")
    assert [doc["url"] for doc in TABLE["documents"]] == [doc["url"] for doc in documents]


def test_everything_settled_has_evidence_from_three_publishers() -> None:
    by_id = {doc["id"]: doc["publisher"] for doc in EVIDENCE["documents"]}
    for section in ("settled", "sequences"):
        for key, entry in EVIDENCE[section].items():
            publishers = {by_id[item["document"]] for item in entry["evidence"]}
            assert len(publishers) >= 3, key
            for item in entry["evidence"]:
                assert key in item["keys"], (key, item)
                assert convert_preeti(item["keys"]).complete
    for key, entry in TABLE["settled"].items():
        assert entry["to"] == EVIDENCE["settled"][key]["to"]
        assert all(item["url"].startswith("https://") for item in entry["evidence"])


def test_sight_lists_cover_every_key_once() -> None:
    sight = TABLE["sight"]
    lists = [sight["confirmed"], sight["seen"], sight["never_seen"]]
    assert [len(keys) for keys in lists] == [108, 11, 21]
    every = [key for keys in lists for key in keys]
    assert len(every) == len(set(every)) == 140
    table_keys = {"m", "{"}
    for section in ("mapping", "majority", "unconfirmed", "disputed", "settled"):
        table_keys.update(TABLE[section])
    assert set(every) == table_keys
    assert sight["lines_read"] == 166 and sight["publishers"] == 7
    for key in sight["confirmed"]:
        assert EVIDENCE["keys"][key]["publishers"] >= 3
    # Nothing the documents show is left unused, and nothing unseen was promoted.
    assert not set(sight["never_seen"]) & set(TABLE["settled"])
    assert set(TABLE["disputed"]) <= set(sight["never_seen"])
    assert set(TABLE["unconfirmed"]) <= set(sight["never_seen"])


def test_documents_may_not_overrule_the_tables() -> None:
    compare = _script("compare_preeti_sources")
    sources = compare.load_sources()
    evidence = json.loads(json.dumps(EVIDENCE))
    evidence["settled"]["s"] = {"to": "ख", "why": "no", "evidence": []}
    with pytest.raises(ValueError, match="only settle a key the tables left open"):
        compare.build_table(sources, evidence)


def test_loader_accepts_both_statuses_and_nothing_else(monkeypatch: pytest.MonkeyPatch) -> None:
    assert legacy.STATUSES == (legacy.EXPERIMENTAL, legacy.TESTED)
    for status, fine in (("experimental", True), ("tested", True), ("verified", False)):
        table = {**TABLE, "status": status}
        monkeypatch.setattr(legacy, "load_table", lambda name, table=table: table)
        legacy._table.cache_clear()
        try:
            if fine:
                assert legacy.load_font_table()["status"] == status
            else:
                with pytest.raises(ValueError, match="malformed"):
                    legacy.load_font_table()
        finally:
            monkeypatch.undo()
            legacy._table.cache_clear()
    assert legacy.load_font_table()["status"] == "tested"


def test_corpus_script_skips_cleanly_without_a_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(CORPUS.ENV, raising=False)
    assert CORPUS.main([]) == 0
    assert capsys.readouterr().out.startswith("skipped: no folder given")
    assert CORPUS.main([str(tmp_path / "absent")]) == 0
    assert "is not a folder" in capsys.readouterr().out
    assert CORPUS.main([str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("skipped:")


def test_corpus_script_keeps_only_text_in_the_preeti_font() -> None:
    xml = (
        '<page number="1" position="absolute" top="0" left="0" height="1188" width="918">\n'
        '<fontspec id="0" size="16" family="ABCDEE+Preeti" color="#000000"/>\n'
        '<fontspec id="1" size="12" family="Times" color="#000000"/>\n'
        '<text top="100" left="50" width="40" height="18" font="0">g]kfn</text>\n'
        '<text top="100" left="95" width="30" height="18" font="1">Nepal</text>\n'
        '<text top="100" left="130" width="60" height="18" font="0"><b>/fi6« a}+s</b></text>\n'
        '<text top="100" left="400" width="30" height="18" font="0">@)&amp;&amp;</text>\n'
        '<text top="140" left="50" width="30" height="14" font="1">page 1</text>\n'
        "</page>\n"
    )
    lines = CORPUS.preeti_lines(xml)
    assert lines == ["g]kfn /fi6« a}+s", "@)&&"]
    counts = CORPUS.measure(lines)
    assert (counts["lines"], counts["characters"], counts["words"]) == (2, 18, 4)
    assert counts["unmapped"] == 0
    assert CORPUS.measure(["s ° m"])["unmapped_by_character"] == {"°": 1, "m": 1}


# --- what the package, the command line and the documents say -----------------------------


def test_version_is_0_9_0() -> None:
    assert aksharkit.__version__ == "0.9.0"
    assert 'version = "0.9.0"' in (ROOT / "pyproject.toml").read_text("utf-8")


def test_cli_note_states_the_status(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["convert", "preeti", "u¥of]"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "गर्\u200dयो\n"
    assert "Preeti conversion is tested on real documents" in captured.err
    assert "not reviewed by a native reader" in captured.err


def test_docs_state_the_numbers_and_what_is_not_verified() -> None:
    doc = (ROOT / "docs" / "preeti.md").read_text("utf-8")
    for needle in (
        "## Tested on real documents",
        "409,081",
        "75,928",
        "0.2278%",
        "0.0005%",
        "166 lines",
        "12 of the 166",
        "not by a native reader",
        "scripts/preeti_corpus.py",
    ):
        assert needle in doc, needle
    for doc_entry in TABLE["documents"]:
        assert doc_entry["url"] in doc
    sources = (ROOT / "docs" / "sources.md").read_text("utf-8")
    for doc_entry in TABLE["documents"]:
        assert doc_entry["url"] in sources
    assert "No Preeti font file" in sources


def test_changelog_has_the_0_9_0_entry() -> None:
    log = (ROOT / "CHANGELOG.md").read_text("utf-8")
    start = log.index("## 0.9.0")
    entry = log[start : log.index("\n## ", start + 1)]
    assert "Not released on PyPI." in entry
    assert "### Not verified" in entry
    for needle in ("native reader", "Word", "phone", "never seen"):
        assert needle in entry, needle


def test_no_text_claims_more_than_was_checked() -> None:
    banned = "per" + "fect"
    for path in (
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "preeti.md",
        ROOT / "site" / "index.html",
        ROOT / "site" / "app.js",
    ):
        text = path.read_text("utf-8").lower()
        assert banned not in text, path.name
    panel = (ROOT / "site" / "index.html").read_text("utf-8")
    assert "Tested on real documents." in panel
    assert "not been reviewed by a native reader" in panel
