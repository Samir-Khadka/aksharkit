"""Preeti to Unicode: the key table, the reordering rules and the reporting.

What these tests can and cannot show. There is no authoritative Preeti text
in this repository yet, so:

* the table tests show that ``font_preeti.json`` is exactly what the
  documented comparison of four MIT-licensed tables produces;
* the reordering tests show that the rules behave as written;
* the "self-consistency" samples were typed by the builder from the table
  itself. They prove the pieces fit together. They do **not** prove that a
  real Preeti document converts correctly;
* ``tests/golden/preeti_samples.tsv`` is where real samples go. It is empty.
"""

from __future__ import annotations

import importlib.util
import json
import random
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import aksharkit
from aksharkit import PreetiResult, UnmappedChar, convert_preeti, legacy, preeti_to_unicode
from aksharkit._data import load_table
from aksharkit.cli import main
from aksharkit.normalize import normalize

ROOT = Path(__file__).resolve().parent.parent
TABLE: dict[str, Any] = load_table("font_preeti")
AGREED: dict[str, Any] = TABLE["mapping"]
MAJORITY: dict[str, Any] = TABLE["majority"]
UNCONFIRMED: dict[str, Any] = TABLE["unconfirmed"]
DISPUTED: dict[str, Any] = TABLE["disputed"]
SEQUENCES: dict[str, Any] = TABLE["sequences"]
UNCONFIRMED_SEQUENCES: dict[str, Any] = TABLE["unconfirmed_sequences"]


def _load_script() -> ModuleType:
    path = ROOT / "scripts" / "compare_preeti_sources.py"
    spec = importlib.util.spec_from_file_location("compare_preeti_sources", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPARE = _load_script()
SOURCES: dict[str, Any] = COMPARE.load_sources()


# --- the table is what the comparison says, nothing more ---------------------


def test_table_matches_the_documented_comparison() -> None:
    expected = COMPARE.render(COMPARE.build_table(SOURCES))
    assert (ROOT / "src/aksharkit/data/font_preeti.json").read_text("utf-8") == expected
    assert COMPARE.main(["--check"]) == 0


def test_table_is_labelled_experimental() -> None:
    assert TABLE["status"] == "experimental"
    assert TABLE["label"] == legacy.PREETI_LABEL
    assert legacy.PREETI_LABEL.startswith("experimental — mapping agreed by at least 2 of 3 ")
    assert "not yet checked against real Preeti documents" in legacy.PREETI_LABEL
    assert "native reader" in legacy.PREETI_LABEL


def test_tier_sizes_are_the_ones_the_docs_state() -> None:
    sizes = (len(AGREED), len(MAJORITY), len(UNCONFIRMED), len(DISPUTED))
    assert sizes == (122, 4, 5, 5)
    assert (len(SEQUENCES), len(UNCONFIRMED_SEQUENCES)) == (5, 2)


def test_sources_are_four_mit_projects_in_three_families() -> None:
    sources = TABLE["sources"]
    assert [s["name"] for s in sources] == [
        "nepali-unicoder",
        "nepalikit",
        "preeti-unicode-converter",
        "nepali-keyboard",
    ]
    assert {s["licence"] for s in sources} == {"MIT"}
    assert [s["family"] for s in sources] == ["A", "A", "B", "C"]
    assert all(len(s["commit"]) == 40 and s["url"].startswith("https://") for s in sources)


@pytest.mark.parametrize("key", sorted(AGREED))
def test_agreed_entry_has_two_families_and_no_dissent(key: str) -> None:
    entry = AGREED[key]
    assert len(set(entry["families"])) >= 2
    assert "dissent" not in entry
    stated = {name: table[key] for name, table in SOURCES["tables"].items() if key in table}
    assert set(stated.values()) == {entry["to"]}


@pytest.mark.parametrize("key", sorted(MAJORITY))
def test_majority_entry_has_two_families_and_a_recorded_dissent(key: str) -> None:
    entry = MAJORITY[key]
    assert len(set(entry["families"])) >= 2
    assert entry["dissent"] and entry["to"] not in entry["dissent"].values()


def test_majority_keys_are_exactly_these() -> None:
    assert {key: entry["to"] for key, entry in MAJORITY.items()} == {
        "B": "द्य",
        "^": "६",
        "¡": "ज्ञ्",
        "¿": "रू",
    }


@pytest.mark.parametrize("key", sorted(UNCONFIRMED))
def test_unconfirmed_entry_has_one_family(key: str) -> None:
    assert len(UNCONFIRMED[key]["families"]) == 1


def test_tiers_do_not_overlap_and_strokes_are_not_letters() -> None:
    tiers = [set(AGREED), set(MAJORITY), set(UNCONFIRMED), set(DISPUTED)]
    assert sum(len(t) for t in tiers) == len(set().union(*tiers))
    for stroke in ("m", "{"):
        assert all(stroke not in tier for tier in tiers)


def test_every_printable_ascii_key_is_covered() -> None:
    covered = set(AGREED) | set(MAJORITY) | {"m", "{"}
    assert [chr(c) for c in range(33, 127) if chr(c) not in covered] == []


def test_sequences_have_two_families_and_unconfirmed_ones_do_not() -> None:
    assert {k: v["to"] for k, v in SEQUENCES.items()} == {
        "km": "फ",
        "qm": "क्र",
        "Qm": "क्त",
        "em": "झ",
        "pm": "ऊ",
    }
    assert all(len(v["families"]) >= 2 for v in SEQUENCES.values())
    assert {k: v["to"] for k, v in UNCONFIRMED_SEQUENCES.items()} == {"8Þ": "ड़", "9Þ": "ढ़"}
    assert all(len(v["families"]) == 1 for v in UNCONFIRMED_SEQUENCES.values())


def test_notice_carries_the_four_copyright_lines() -> None:
    notice = (ROOT / "NOTICE").read_text("utf-8")
    for source in SOURCES["sources"].values():
        assert source["copyright"] in notice
        assert source["url"] in notice
    assert "Permission is hereby granted, free of charge" in notice


# --- the comparison rules themselves ----------------------------------------


def _fake(tables: dict[str, dict[str, str]], families: dict[str, str]) -> dict[str, Any]:
    return {"sources": {n: {"family": f} for n, f in families.items()}, "tables": tables}


def _tier(tables: dict[str, dict[str, str]], families: dict[str, str]) -> dict[str, Any]:
    (record,) = COMPARE.classify(_fake(tables, families))
    return dict(record)


FAMILIES = {"a1": "A", "a2": "A", "b": "B", "c": "C"}


def test_two_projects_of_one_family_are_one_vote() -> None:
    record = _tier({"a1": {"x": "क"}, "a2": {"x": "क"}}, FAMILIES)
    assert (record["tier"], record["families"]) == ("single", ["A"])


def test_two_families_agreeing_is_agreed() -> None:
    record = _tier({"a1": {"x": "क"}, "b": {"x": "क"}}, FAMILIES)
    assert (record["tier"], record["value"], record["families"]) == ("agreed", "क", ["A", "B"])


def test_a_third_table_differing_makes_it_majority() -> None:
    record = _tier({"a1": {"x": "क"}, "b": {"x": "क"}, "c": {"x": "ख"}}, FAMILIES)
    assert (record["tier"], record["dissent"]) == ("majority", {"c": "ख"})


def test_a_split_family_has_no_vote() -> None:
    record = _tier({"a1": {"x": "क"}, "a2": {"x": "ख"}, "b": {"x": "क"}}, FAMILIES)
    assert record["tier"] == "disputed"
    record = _tier({"a1": {"x": "क"}, "a2": {"x": "ख"}, "b": {"x": "क"}, "c": {"x": "क"}}, FAMILIES)
    assert (record["tier"], record["families"], record["dissent"]) == (
        "majority",
        ["B", "C"],
        {"a2": "ख"},
    )


def test_two_families_disagreeing_is_disputed() -> None:
    assert _tier({"b": {"x": "क"}, "c": {"x": "ख"}}, FAMILIES)["tier"] == "disputed"
    assert _tier({"a1": {"x": "क"}, "a2": {"x": "ख"}}, FAMILIES)["tier"] == "disputed"


def test_stroke_keys_are_left_out_of_the_comparison() -> None:
    assert COMPARE.classify(_fake({"b": {"m": "फ", "{": "र्"}}, FAMILIES)) == []


def test_report_runs_and_names_every_tier(capsys: pytest.CaptureFixture[str]) -> None:
    assert COMPARE.main([]) == 0
    out = capsys.readouterr().out
    assert "agreed: 122" in out and "majority: 4" in out
    assert "single: 5" in out and "disputed: 5" in out


# --- every table entry converts to exactly its letter ------------------------


@pytest.mark.parametrize("key", sorted(AGREED) + sorted(MAJORITY))
def test_each_default_key_gives_its_letter(key: str) -> None:
    want = (AGREED.get(key) or MAJORITY[key])["to"]
    assert legacy.load_font_map()[key] == want
    result = convert_preeti(key, normalise=False)
    assert result == PreetiResult(want, ())


@pytest.mark.parametrize("key", sorted(MAJORITY))
def test_strict_leaves_majority_keys_alone(key: str) -> None:
    assert key not in legacy.load_font_map(strict=True)
    assert convert_preeti(key, strict=True) == PreetiResult(key, (UnmappedChar(key, 0),))


@pytest.mark.parametrize("key", sorted(UNCONFIRMED))
def test_unconfirmed_keys_need_to_be_asked_for(key: str) -> None:
    assert key not in legacy.load_font_map()
    assert convert_preeti(key) == PreetiResult(key, (UnmappedChar(key, 0),))
    want = UNCONFIRMED[key]["to"]
    assert legacy.load_font_map(include_unconfirmed=True)[key] == want
    assert convert_preeti(key, include_unconfirmed=True, normalise=False).text == want


@pytest.mark.parametrize("key", sorted(DISPUTED))
def test_disputed_keys_are_never_used(key: str) -> None:
    for unconfirmed, strict in ((False, False), (True, False), (False, True), (True, True)):
        table = legacy.load_font_map(include_unconfirmed=unconfirmed, strict=strict)
        assert key not in table
        result = convert_preeti(key, include_unconfirmed=unconfirmed, strict=strict)
        assert result == PreetiResult(key, (UnmappedChar(key, 0),))


@pytest.mark.parametrize(("keys", "want"), sorted((k, v["to"]) for k, v in SEQUENCES.items()))
def test_each_stroke_pair_gives_its_letter(keys: str, want: str) -> None:
    assert convert_preeti(keys) == PreetiResult(want, ())


def test_unconfirmed_sequences_need_to_be_asked_for() -> None:
    assert convert_preeti("8Þ").text == "डÞ"
    assert convert_preeti("8Þ").unmapped == (UnmappedChar("Þ", 1),)
    assert convert_preeti("8Þ", include_unconfirmed=True) == PreetiResult("ड़", ())
    assert convert_preeti("a9Þf", include_unconfirmed=True) == PreetiResult("बढ़ा", ())


def test_load_font_map_returns_a_copy_and_rejects_other_fonts() -> None:
    first = legacy.load_font_map()
    first["a"] = "changed"
    assert legacy.load_font_map()["a"] == "ब"
    assert legacy.load_font_table()["status"] == "experimental"
    for call in (
        lambda: legacy.load_font_map("kantipur"),
        lambda: legacy.to_unicode("x", "himali"),
    ):
        with pytest.raises(ValueError, match="unknown font"):
            call()
    assert legacy.to_unicode("g]kfn", " Preeti ") == "नेपाल"


# --- reordering rules --------------------------------------------------------


@pytest.mark.parametrize(
    ("preeti", "want"),
    [
        # short i: typed before the consonant, stored after the whole cluster
        ("ls", "कि"),
        ("lzIff", "शिक्षा"),
        ("l:ylt", "स्थिति"),
        ("lk|o", "प्रिय"),
        ("låtLo", "द्वितीय"),
        ("lhNnf", "जिल्ला"),
        ("lgod", "नियम"),
        ("lIflth", "क्षितिज"),
        # reph: typed after the syllable, stored before its cluster
        ("s{", "र्क"),
        ("sfo{", "कार्य"),
        ("kf6L{", "पार्टी"),
        ("jif{", "वर्ष"),
        ("ug'{", "गर्नु"),
        ("u5{'", "गर्छु"),
        ('k"0f{', "पूर्ण"),
        ("wd{+", "धर्मं"),
        ("cfTdf{", "आर्त्मा"),
        # reph and short i on the same syllable, either way round
        ("ls{", "र्कि"),
        ("cfly{s", "आर्थिक"),
        ("jflif{s", "वार्षिक"),
        # ई is इ with a reph
        ("O{", "ई"),
        ("c{", "र्अ"),
        ("O{Zj/", "ईश्वर"),
        ("tfO{", "ताई"),
        # half form + upright bar is the full letter
        ("0f", "ण"),
        ("If", "क्ष"),
        ("if", "ष"),
        ("u0f]z", "गणेश"),
        ("efiff", "भाषा"),
        ("l0f", "णि"),
        # half form + next letter is a conjunct
        (":jf:Yo", "स्वास्थ्य"),
        ("GofFo", "न्याँय"),
        ("ljBfno", "विद्यालय"),
        ('dxTTjk"0f{', "महत्त्वपूर्ण"),
        ("zAb", "शब्द"),
        ("k|wfgdGqL", "प्रधानमन्त्री"),
        # the m stroke
        ("km", "फ"),
        ("kmn", "फल"),
        ('k"mn', "फूल"),
        ('km"n', "फूल"),
        ("k|m]d", "फ्रेम"),
        ("emf]nf", "झोला"),
        ("pm", "ऊ"),
        ("qmd", "क्रम"),
        ("zlQm", "शक्ति"),
        ("eQm", "भक्त"),
        ("em]{", "र्झे"),
        # split vowels and sign order
        ("cf", "आ"),
        ("cf]", "ओ"),
        ("cf}", "औ"),
        ("P]", "ऐ"),
        ("sf]", "को"),
        ("s]f", "को"),
        ("sf}", "कौ"),
        ("s}f", "कौ"),
        ("xfF", "हाँ"),
        ("xFf", "हाँ"),
        ("s+f", "कां"),
        ("b'Mv", "दुःख"),
    ],
)
def test_reordering(preeti: str, want: str) -> None:
    assert convert_preeti(preeti) == PreetiResult(want, ())


def test_short_i_with_nothing_to_sit_on_stays_where_it_was_typed() -> None:
    assert convert_preeti("l").text == "ि"
    assert convert_preeti("l ").text == "ि "
    assert convert_preeti("lc").text == "िअ"


def test_short_i_stops_before_a_dangling_half_form() -> None:
    assert convert_preeti("lS", normalise=False).text == "कि्"


def test_reph_with_nothing_before_it_is_reported_not_guessed() -> None:
    assert convert_preeti("{") == PreetiResult("{", (UnmappedChar("{", 0),))
    assert convert_preeti(" {s") == PreetiResult(" {क", (UnmappedChar("{", 1),))
    assert convert_preeti("f{").unmapped == (UnmappedChar("{", 1),)


def test_stroke_with_nothing_to_change_is_reported_not_guessed() -> None:
    assert convert_preeti("m") == PreetiResult("m", (UnmappedChar("m", 0),))
    assert convert_preeti("sm") == PreetiResult("कm", (UnmappedChar("m", 1),))
    assert convert_preeti("k m") == PreetiResult("प m", (UnmappedChar("m", 2),))
    assert convert_preeti("kmm") == PreetiResult("फm", (UnmappedChar("m", 2),))
    assert convert_preeti("ksm") == PreetiResult("पकm", (UnmappedChar("m", 2),))


# --- passing through and reporting -------------------------------------------


def test_empty_and_white_space_only() -> None:
    assert convert_preeti("") == PreetiResult("", ())
    assert convert_preeti(" \t\n  ") == PreetiResult(" \t\n  ", ())


def test_white_space_and_line_breaks_are_kept_exactly() -> None:
    assert preeti_to_unicode("g]kfn  d]/f]\n\tb]z xf] .\n") == "नेपाल  मेरो\n\tदेश हो ।\n"


def test_text_that_is_already_devanagari_passes_through_unreported() -> None:
    assert convert_preeti("नेपाल कि किताब") == PreetiResult("नेपाल कि किताब", ())
    assert convert_preeti("किताब g]kfn") == PreetiResult("किताब नेपाल", ())
    assert convert_preeti("र्क क्ष ई") == PreetiResult("र्क क्ष ई", ())


def test_unmapped_characters_keep_their_place_and_their_offsets() -> None:
    text = "g]kfn ¥ Ý € d]/f]"
    result = convert_preeti(text)
    assert result.text == "नेपाल ¥ Ý € मेरो"
    assert result.unmapped == (UnmappedChar("¥", 6), UnmappedChar("Ý", 8), UnmappedChar("€", 10))
    assert all(text[item.offset] == item.char for item in result.unmapped)
    assert result.unmapped_chars == ("¥", "Ý", "€")
    assert not result.complete
    assert convert_preeti("g]kfn").complete


def test_repeated_unmapped_characters_are_each_reported_once_per_use() -> None:
    result = convert_preeti("¥s¥")
    assert [item.offset for item in result.unmapped] == [0, 2]
    assert result.unmapped_chars == ("¥",)


def test_unmapped_list_is_in_input_order_even_when_a_reph_fails() -> None:
    result = convert_preeti("{ ¥ m")
    assert [(item.char, item.offset) for item in result.unmapped] == [("{", 0), ("¥", 2), ("m", 4)]


def test_preeti_to_unicode_returns_just_the_text() -> None:
    assert preeti_to_unicode("g]kfn") == "नेपाल"
    assert preeti_to_unicode("ljBfno", strict=True) == "विBालय"
    assert preeti_to_unicode("‘", include_unconfirmed=True) == "ॅ"
    assert aksharkit.preeti_to_unicode is legacy.preeti_to_unicode


def test_result_is_frozen() -> None:
    result = convert_preeti("s")
    with pytest.raises(AttributeError):
        result.text = "x"  # type: ignore[misc]


def test_unicode_to_preeti_is_left_out() -> None:
    with pytest.raises(NotImplementedError, match="not implemented"):
        legacy.unicode_to_preeti("नेपाल")


# --- self-consistency samples: typed from the table, NOT real Preeti text -----

SELF_CONSISTENCY = [
    ("g]kfn", "नेपाल"),
    ("sf7df8f}+", "काठमाडौं"),
    ("d]/f] gfd ;ld/ xf] .", "मेरो नाम समिर हो ।"),
    ("ljBfno", "विद्यालय"),
    ("sfo{qmd", "कार्यक्रम"),
    ("k|wfgdGqL", "प्रधानमन्त्री"),
    (";/sf/", "सरकार"),
    ("?kfGt/0f", "रुपान्तरण"),
    ("cfpg'xf];\\", "आउनुहोस्"),
    (";+ljwfg", "संविधान"),
    ("kl/jt{g", "परिवर्तन"),
    ("@)*# ;fn", "२०८३ साल"),
    ("!@#$%^&*()", "१२३४५६७८९०"),
    ("pBf]u", "उद्योग"),
    ("em08f", "झण्डा"),
    ("pmgL", "ऊनी"),
    ("x'G5", "हुन्छ"),
    ("cf}iflw", "औषधि"),
    ("P]g", "ऐन"),
    ("1fg", "ज्ञान"),
    ("If]q", "क्षेत्र"),
    ("k|ltzt Ü", "प्रतिशत %"),
    ("s] 5 <", "के छ ?"),
    ("-s_ / -v_", "(क) र (ख)"),
    ("?= !))÷–", "रु. १००/–"),
    ("æg]kfnÆ", "“नेपाल”"),
    ("lzIff, :jf:Yo / /f]huf/L", "शिक्षा, स्वास्थ्य र रोजगारी"),
    ("C0f", "ऋण"),
    (">L % sf] ;/sf/", "श्री ५ को सरकार"),
    ("åf/f", "द्वारा"),
    ("a'4", "बुद्ध"),
    ("/fli6«o", "राष्ट्रिय"),
]


@pytest.mark.parametrize(("preeti", "want"), SELF_CONSISTENCY)
def test_self_consistency_sample(preeti: str, want: str) -> None:
    """Built from the table by the builder: shows consistency, not correctness."""
    result = convert_preeti(preeti)
    assert result.text == want
    assert [item.char for item in result.unmapped] == [ch for ch in preeti if ch == "–"]


# --- real samples: empty until a Preeti typist supplies them ------------------


def _real_samples() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    path = ROOT / "tests" / "golden" / "preeti_samples.tsv"
    for number, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        assert len(parts) == 3, f"line {number}: need preeti<TAB>unicode<TAB>origin"
        rows.append((parts[0], parts[1], parts[2]))
    return rows


def test_real_samples_file_explains_itself() -> None:
    text = (ROOT / "tests" / "golden" / "preeti_samples.tsv").read_text("utf-8")
    assert "preeti<TAB>unicode<TAB>where it came from" in text
    assert "not made by a converter" in text


def test_real_samples_convert_exactly() -> None:
    """Passes while the file is empty; every real line added becomes a check."""
    failures = [
        f"{origin}: {preeti!r} gave {convert_preeti(preeti).text!r}, want {want!r}"
        for preeti, want, origin in _real_samples()
        if convert_preeti(preeti).text != want
    ]
    assert failures == []


# --- properties ---------------------------------------------------------------


def _random_inputs(count: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    alphabet = sorted(AGREED) + sorted(MAJORITY) + ["m", "{", " ", " ", "\n"] + sorted(DISPUTED)
    return ["".join(rng.choices(alphabet, k=rng.randint(0, 40))) for _ in range(count)]


def test_any_key_sequence_converts_without_error_or_leaked_markers() -> None:
    for text in _random_inputs(3000, seed=83):
        for kwargs in ({}, {"include_unconfirmed": True}, {"strict": True}):
            result = convert_preeti(text, **kwargs)
            assert "<pre-i>" not in result.text and "<reph>" not in result.text
            assert all(text[item.offset] == item.char for item in result.unmapped)
            offsets = [item.offset for item in result.unmapped]
            assert offsets == sorted(offsets)


def test_output_is_already_in_normal_form() -> None:
    samples = [preeti for preeti, _ in SELF_CONSISTENCY] + _random_inputs(1500, seed=2083)
    for text in samples:
        out = convert_preeti(text).text
        assert normalize(out, whitespace=False, danda=False) == out


def test_white_space_survives_any_conversion() -> None:
    for text in _random_inputs(1000, seed=6):
        out = convert_preeti(text).text
        assert [ch for ch in out if ch in " \n"] == [ch for ch in text if ch in " \n"]


def test_normalise_false_skips_the_normaliser() -> None:
    assert convert_preeti("sf]", normalise=False).text == "का\u0947"
    assert convert_preeti("sf]").text == "को"
    assert convert_preeti("O{", normalise=False).text == "र्इ"


# --- command line -------------------------------------------------------------


def test_cli_converts_and_prints_the_experimental_note(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["convert", "preeti", "g]kfn"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "नेपाल\n"
    assert captured.err == f"aksharkit: note: Preeti conversion is {legacy.PREETI_LABEL}\n"


def test_cli_quiet_hides_only_the_note(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["convert", "preeti", "g]kfn", "--quiet"]) == 0
    assert capsys.readouterr() == ("नेपाल\n", "")
    assert main(["convert", "preeti", "s ¥", "--quiet"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "क ¥\n"
    assert captured.err == (
        "aksharkit: warning: 1 character(s) had no agreed Preeti entry "
        "and were left unchanged: ¥ (U+00A5)\n"
    )


def test_cli_report_lists_positions(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["convert", "preeti", "sfo{qmd ¥ Ý m", "--quiet", "--report"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "कार्यक्रम ¥ Ý m\n"
    assert captured.err.splitlines() == [
        "aksharkit: warning: 3 character(s) had no agreed Preeti entry "
        "and were left unchanged: ¥ (U+00A5) Ý (U+00DD) m (U+006D)",
        "  position 8: ¥ (U+00A5)",
        "  position 10: Ý (U+00DD)",
        "  position 12: m (U+006D)",
    ]
    assert main(["convert", "preeti", "g]kfn", "--quiet", "--report"]) == 0
    assert capsys.readouterr().err == "aksharkit: every character had an agreed Preeti entry\n"


def test_cli_tier_switches(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["convert", "preeti", "ljBfno ^", "--quiet", "--strict"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "विBालय ^\n"
    assert "B (U+0042) ^ (U+005E)" in captured.err
    assert main(["convert", "preeti", "a8Þf ‘", "--quiet", "--include-unconfirmed"]) == 0
    assert capsys.readouterr() == ("बड़ा ॅ\n", "")


def test_cli_reads_standard_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("d]/f] gfd\n;ld/ xf] .\n"))
    assert main(["convert", "preeti", "-", "--quiet"]) == 0
    assert capsys.readouterr().out == "मेरो नाम\nसमिर हो ।\n"
    monkeypatch.setattr("sys.stdin", io.StringIO("g]kfn\n"))
    assert main(["convert", "preeti"]) == 0
    assert capsys.readouterr().out == "नेपाल\n"


def test_cli_unprintable_unmapped_character_is_shown_safely(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["convert", "preeti", "s\x07", "--quiet"]) == 0
    assert "? (U+0007)" in capsys.readouterr().err


def test_cli_help_states_the_status(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["convert", "--help"])
    assert info.value.code == 0
    out = " ".join(capsys.readouterr().out.split())
    assert "experimental" in out and "not yet checked against real Preeti documents" in out


def test_sources_file_is_valid_and_attributed() -> None:
    data = json.loads((ROOT / "scripts" / "preeti_sources.json").read_text("utf-8"))
    assert set(data["tables"]) == set(data["sources"])
    for meta in data["sources"].values():
        assert meta["licence"] == "MIT" and meta["copyright"].startswith("Copyright (c)")
    assert all(len(key) == 1 for table in data["tables"].values() for key in table)


def test_version_is_0_6_0() -> None:
    assert aksharkit.__version__ == "0.6.0"
    pyproject = (ROOT / "pyproject.toml").read_text("utf-8")
    assert 'version = "0.6.0"' in pyproject
    assert 'license-files = ["LICENSE", "NOTICE"]' in pyproject
