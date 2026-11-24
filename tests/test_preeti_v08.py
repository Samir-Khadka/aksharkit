"""Preeti in 0.8: Unicode to Preeti made measurable, files in both directions.

What is checked here, and what is not:

* every word written as keys reads back, through ``convert_preeti``, as
  exactly the same word. That is the only property the word list and the
  sentences test: there are no hand-made Preeti "expected outputs", because
  nobody with the Preeti font has looked at any;
* the coverage numbers of ``scripts/preeti_coverage.py`` are pinned, so a
  change in either direction shows up;
* the 14 worked examples from two other converters' pages agree in both
  directions. They are a cross-check, not ground truth.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

import aksharkit
from aksharkit import (
    DocxEncodeReport,
    PreetiEncodeStats,
    convert_docx_bytes,
    convert_preeti,
    encode_docx,
    encode_docx_bytes,
    encode_preeti,
    normalize,
    unicode_to_preeti,
)
from aksharkit.cli import main

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


COVERAGE = _load("preeti_coverage", ROOT / "scripts" / "preeti_coverage.py")
_DOCX = _load("preeti_docx_helpers", ROOT / "tests" / "test_preeti_docx.py")
build, para, part, run, runs_of = _DOCX.build, _DOCX.para, _DOCX.part, _DOCX.run, _DOCX.runs_of
W = _DOCX.W_NS


def canonical(text: str) -> str:
    return normalize(text, whitespace=False, danda=False)


def devanagari(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- text that is not Nepali is left alone, and counted apart -------------------


def test_english_and_ascii_numbers_are_foreign_not_failures() -> None:
    result = encode_preeti("दर्ता नं. 245, Nepal मा")
    assert result.text == "btf{ g+= 245, Nepal df"
    assert [(span.text, span.start, span.line, span.column) for span in result.foreign] == [
        ("245,", 10, 1, 11),
        ("Nepal", 15, 1, 16),
    ]
    assert result.unmapped == () and result.complete
    stats = result.stats
    assert (stats.words, stats.words_encoded, stats.foreign) == (3, 3, 9)
    assert stats.share_words == 1.0 and stats.share_chars == 1.0


def test_a_mark_with_no_key_inside_nepali_text_is_still_reported() -> None:
    result = encode_preeti("काठमाडौं-३ [क]")
    assert result.text == "sf7df8f}+-# [s]"
    assert result.unmapped_chars == ("-", "[", "]")
    assert not result.complete
    assert result.stats.words == 2 and result.stats.words_encoded == 0


def test_segments_cover_the_input_and_say_what_each_stretch_became() -> None:
    text = "नेपाल abc क्ा काठ-मा ।"
    result = encode_preeti(text)
    assert [(s.text, s.kind) for s in result.segments] == [
        ("g]kfn", "keys"),
        (" ", "space"),
        ("abc", "foreign"),
        (" ", "space"),
        ("क्ा", "skipped"),
        (" ", "space"),
        ("sf7", "keys"),
        ("-", "unmapped"),
        ("df", "keys"),
        (" ", "space"),
        (".", "keys"),
    ]
    assert result.segments[0].start == 0 and result.segments[-1].end == len(canonical(text))
    for before, after in zip(result.segments, result.segments[1:], strict=False):
        assert before.end == after.start
    assert "".join(s.text for s in result.segments) == result.text


def test_whole_words_keeps_a_word_with_a_hole_in_unicode() -> None:
    loose = encode_preeti("अड्\u200cडा चढ")
    assert loose.text == "c8\\\u200c8f r9"
    whole = encode_preeti("अड्\u200cडा चढ", whole_words=True)
    assert whole.text == "अड्\u200cडा r9"
    assert next((s.text, s.kind) for s in whole.segments) == ("अड्\u200cडा", "unmapped")
    assert whole.unmapped_chars == ("\u200c",)


def test_stats_add_up_and_serialise() -> None:
    one = encode_preeti("नेपाल ok").stats
    two = encode_preeti("काठ-मा").stats
    total = one + two
    assert isinstance(total, PreetiEncodeStats)
    assert (total.words, total.words_encoded) == (2, 1)
    assert total.as_dict()["share_words"] == 0.5
    assert PreetiEncodeStats().share_words == 1.0
    payload = json.loads(json.dumps(encode_preeti("नेपाल ok").as_dict(), ensure_ascii=False))
    assert payload["stats"]["words"] == 1 and payload["foreign"][0]["text"] == "ok"
    assert payload["mark_kept"] is None


# --- ASCII digits ----------------------------------------------------------------


def test_ascii_digits_are_kept_by_default_and_never_typed_as_keys() -> None:
    # "2083" typed in the Preeti font would show as other glyphs, so it is
    # left alone and listed, not passed off as keys.
    result = encode_preeti("मिति 2083-01-15 मा")
    assert result.text == "ldlt 2083-01-15 df"
    assert [span.text for span in result.foreign] == ["2083-01-15"]
    assert [s.kind for s in result.segments if s.text == "2083-01-15"] == ["foreign"]


def test_digits_devanagari_rewrites_numbers_on_nepali_lines_only() -> None:
    result = encode_preeti("मिति 2083 साल\nInvoice 2083", digits="devanagari")
    assert result.text == "ldlt @)*# ;fn\nInvoice 2083"
    assert result.complete
    back = convert_preeti(result.text, keep_words=["Invoice"])
    assert back.text.splitlines()[0] == "मिति २०८३ साल"  # the text changed: said in the docs
    with pytest.raises(ValueError, match="digits"):
        encode_preeti("क", digits="roman")


# --- mark_kept: a plain-text round trip with English in it ------------------------


@pytest.mark.parametrize(
    "text",
    [
        "दर्ता नं. 245, Nepal काठ-मा",
        "Kathmandu Office मा अड्\u200cडा छ ।",
        "ईमेल ram@example.com मा पठाउनुहोस्\nदोस्रो line 2",
        "केवल नेपाली पाठ ।",
        "",
    ],
)
def test_mark_kept_makes_plain_text_reversible(text: str) -> None:
    result = encode_preeti(text, mark_kept=("{{", "}}"))
    back = convert_preeti(result.text, markers=("{{", "}}"), keep_links=False)
    assert back.text == canonical(text)
    assert result.mark_kept == ("{{", "}}")


def test_mark_kept_output_and_errors() -> None:
    result = encode_preeti("दर्ता नं. 245, Nepal काठ-मा", mark_kept=("{{", "}}"))
    assert result.text == "btf{ g+= {{245,}} {{Nepal}} sf7{{-}}df"
    with pytest.raises(ValueError):
        encode_preeti("क {{ ख", mark_kept=("{{", "}}"))
    with pytest.raises(ValueError):
        encode_preeti("क", mark_kept=("", "}}"))


# --- single-table keys in the reverse direction (off by default) ------------------


def test_unconfirmed_keys_are_an_option_and_need_the_same_option_to_read_back() -> None:
    assert encode_preeti("पढ़ काँड़ा").unmapped_chars == ("़",)
    result = encode_preeti("पढ़ काँड़ा कॅ", include_unconfirmed=True)
    assert result.text == "k9Þ sfF8Þf s‘"
    assert result.complete
    assert convert_preeti(result.text, include_unconfirmed=True).text == "पढ़ काँड़ा कॅ"
    assert convert_preeti(result.text).text != "पढ़ काँड़ा कॅ"
    assert unicode_to_preeti("पढ़", include_unconfirmed=True) == "k9Þ"
    # The other nukta letters have no key in any table.
    other = encode_preeti("क़ानून", include_unconfirmed=True)
    assert other.text == "क़ानून" and not other.complete
    assert [span.text for span in other.skipped] == ["क़ानून"]


# --- encoding rules new in 0.8 ----------------------------------------------------


@pytest.mark.parametrize(
    ("text", "keys"),
    [
        ("ट्रक", "6«s"),
        ("राष्ट्र", "/fi6«"),
        ("ड्राइभर", "8«fOe/"),
        ("श्लोक ॥", "Znf]s .."),
        ("विषय : निवेदन", "ljifo M lgj]bg"),
        ("समय १०:३० बजे", ";do !)M#) ah]"),
        ("दुःख", "b'Mv"),
    ],
)
def test_rules_new_in_0_8(text: str, keys: str) -> None:
    result = encode_preeti(text)
    assert result.text == keys and result.complete
    assert convert_preeti(keys, keep_links=False).text == text


def test_a_colon_straight_after_a_letter_cannot_be_written() -> None:
    # The only key for a colon is the visarga key, and after a letter that
    # key reads as a visarga. So the colon is reported, never guessed.
    result = encode_preeti("निवेदन: श्री")
    assert result.text == "lgj]bg: >L"
    assert result.unmapped_chars == (":",)


# --- Preeti to Unicode fixes found on the way --------------------------------------


@pytest.mark.parametrize(
    ("keys", "text"),
    [
        ("..", "॥"),
        ("Znf]s ..", "श्लोक ॥"),
        (". .", "। ।"),
        ("ljifo M lgj]bg", "विषय : निवेदन"),
        ("!)M#)", "१०:३०"),
        ("M", ":"),
        ("b'Mv", "दुःख"),
        ("k|foM", "प्रायः"),
        ("s\\{", "र्क्"),
    ],
)
def test_forward_fixes(keys: str, text: str) -> None:
    result = convert_preeti(keys)
    assert result.text == text
    assert result.unmapped == ()


# --- the coverage audit --------------------------------------------------------------


def test_coverage_audit_numbers_are_pinned() -> None:
    default = COVERAGE.audit()
    assert (default["forms"], default["pass"]) == (5300, 5246)
    assert COVERAGE.audit(unconfirmed=True)["pass"] == 5251
    assert COVERAGE.audit(strict=True)["pass"] == 5235
    by_id = {entry["id"]: entry for entry in default["classes"]}
    assert len(by_id) == 17
    full = [name for name, entry in by_id.items() if entry["pass"] == entry["forms"]]
    assert len(full) == 12
    # Every consonant, sign, two-consonant conjunct and listed ligature is writable.
    for name in ("consonants", "vowels", "digits", "matra", "signs", "matra-nasal"):
        assert name in full
    assert sum(entry["forms"] for entry in by_id.values()) == 5300


def test_every_coverage_failure_has_a_reason_and_none_is_a_wrong_read_back() -> None:
    report = COVERAGE.audit()
    failures = [item for entry in report["classes"] for item in entry["failures"]]
    assert len(failures) == 5300 - 5246
    for item in failures:
        assert item["reason"], item
        assert "reads back differently" not in item["reason"], item


def test_coverage_table_in_the_docs_is_current(capsys: pytest.CaptureFixture[str]) -> None:
    assert COVERAGE.main(["--check"]) == 0
    capsys.readouterr()
    assert COVERAGE.markdown() in (ROOT / "docs" / "preeti.md").read_text("utf-8")


# --- the hand-written word list and sentences -----------------------------------------


def _lines(name: str) -> list[str]:
    text = (GOLDEN / name).read_text("utf-8")
    return [line for line in text.splitlines() if line.strip() and not line.startswith("#")]


WORDS = list(dict.fromkeys(word for line in _lines("preeti_wordlist.txt") for word in line.split()))
SENTENCES = _lines("preeti_sentences.txt")


def test_word_list_is_large_and_holds_no_preeti_keys() -> None:
    assert len(WORDS) >= 1500
    assert len(WORDS) == 2639
    assert all(devanagari(word) for word in WORDS)
    assert all(not ("a" <= ch.lower() <= "z") for word in WORDS for ch in word)


def test_every_word_written_as_keys_reads_back_exactly() -> None:
    written = 0
    left: list[str] = []
    for word in WORDS:
        result = encode_preeti(word)
        if not result.complete:
            left.append(word)
            continue
        written += 1
        assert not devanagari(result.text), word
        back = convert_preeti(result.text, keep_links=False)
        assert back.text == canonical(word) and back.complete, (word, result.text, back.text)
    # 2,639 of 2,639 since 0.9, when real documents settled the key for the
    # eyelash ra (भर्‍याङ was the one word left before).
    assert left == []
    assert written == 2639


def test_words_also_survive_strict_and_unconfirmed_modes() -> None:
    for word in WORDS:
        for options in ({"strict": True}, {"include_unconfirmed": True}):
            result = encode_preeti(word, **options)  # type: ignore[arg-type]
            if result.complete:
                back = convert_preeti(result.text, keep_links=False, **options)  # type: ignore[arg-type]
                assert back.text == canonical(word), (word, options)


def test_sentences_round_trip() -> None:
    assert len(SENTENCES) >= 60
    assert len(SENTENCES) == 62
    left = []
    for sentence in SENTENCES:
        result = encode_preeti(sentence)
        back = convert_preeti(result.text, keep_links=False)
        if result.complete:
            assert back.text == canonical(sentence), sentence
        else:
            left.append(sentence)
    # All 62 since 0.9: the one with गर्‍यो was left before the eyelash ra had a key.
    assert left == []


def test_whole_word_list_as_one_text_gives_the_same_count() -> None:
    result = encode_preeti("\n".join(WORDS))
    assert (result.stats.words, result.stats.words_encoded) == (2639, 2639)
    assert round(100 * result.stats.share_words, 2) == 100.0


# --- worked examples from two other converters' pages ----------------------------------


def _crosscheck() -> list[tuple[str, str, str]]:
    rows = []
    for line in (GOLDEN / "preeti_crosscheck.tsv").read_text("utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        source, keys, text = line.split("\t")
        rows.append((source, keys, text))
    return rows


CROSSCHECK = _crosscheck()


def test_crosscheck_file_names_its_sources() -> None:
    assert len(CROSSCHECK) == 14
    assert {source for source, _, _ in CROSSCHECK} == {
        "https://www.engineeringnepal.com.np/p/preeti-to-unicode.html",
        "https://shobfree.com/nepali-preeti-to-unicode-converter",
    }
    head = (GOLDEN / "preeti_crosscheck.tsv").read_text("utf-8").split("\n\n")[0]
    assert "NOT ground truth" in head


@pytest.mark.parametrize(("source", "keys", "text"), CROSSCHECK)
def test_crosscheck_preeti_to_unicode(source: str, keys: str, text: str) -> None:
    result = convert_preeti(keys, keep_links=False)
    assert result.text == canonical(text), source
    assert result.complete


@pytest.mark.parametrize(("source", "keys", "text"), CROSSCHECK)
def test_crosscheck_unicode_to_preeti(source: str, keys: str, text: str) -> None:
    result = encode_preeti(text)
    assert result.complete, source
    # The round trip is the guarantee. Identical keys are a bonus: a
    # different but equivalent sequence would also be acceptable.
    assert convert_preeti(result.text, keep_links=False).text == canonical(text)
    # Since 0.9 one pair differs: ``झ`` is written ``em``, the way typists do
    # (312 times to 1 in the real documents), not with the rare key ``´``.
    assert result.text == keys.replace("´", "em"), source


def test_samples_file_holds_real_samples_since_0_9() -> None:
    lines = (GOLDEN / "preeti_samples.tsv").read_text("utf-8").splitlines()
    assert len([line for line in lines if line.strip() and not line.startswith("#")]) >= 26


# --- Unicode .docx to Preeti .docx -------------------------------------------------------

BOLD = '<w:b/><w:bCs/><w:szCs w:val="28"/>'
BODY = (
    para(
        run("निवेदन श्री प्रमुख ज्यू, "),
        run("Kathmandu Office", "Calibri"),
        run(" मा दर्ता नं. 245 (२०८३) अड्\u200cडा र काठमाडौं-३ ।", extra=BOLD),
    )
    + para(run("वि"), run("द्या"), run("लय नेपाल"))
    + para(run("Only English here."))
)


def encode(body: str, **kwargs: object) -> tuple[str, DocxEncodeReport, bytes]:
    data, report = encode_docx_bytes(build(body), **kwargs)  # type: ignore[arg-type]
    return part(data), report, data


def test_docx_devanagari_becomes_keys_in_the_preeti_font_and_the_rest_stays() -> None:
    xml, report, _ = encode(BODY)
    assert [item for item in runs_of(xml) if item[0]] == [
        ("lgj]bg >L k|d'v Ho\", ", "Preeti"),
        ("Kathmandu Office", "Calibri"),
        (" df btf{ g+= ", "Preeti"),
        ("245 ", None),
        ("-@)*#_ ", "Preeti"),
        ("अड्\u200cडा ", None),
        ("/ sf7df8f}+", "Preeti"),
        ("-", None),
        ("# .", "Preeti"),
        ("ljBfno", "Preeti"),
        (" g]kfn", "Preeti"),
        ("Only English here.", None),
    ]
    assert (report.runs_converted, report.runs_split, report.runs_untouched) == (3, 1, 3)
    assert report.paragraphs_changed == 2 and report.boundary_moves == 1
    assert report.font == "Preeti" and not report.complete
    assert [(item.text, item.reason, item.chars, item.paragraph) for item in report.left] == [
        ("अड्\u200cडा", "no key", ("\u200c",), 1),
        ("-", "no key", ("-",), 1),
    ]
    assert (report.stats.words, report.stats.words_encoded) == (14, 12)


def test_docx_bold_and_size_follow_the_complex_script_ones() -> None:
    xml, _, _ = encode(para(run("नेपाल", extra=BOLD)))
    assert (
        '<w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti" w:cs="Preeti"/><w:b/><w:bCs/>'
        '<w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr><w:t xml:space="preserve">g]kfn</w:t>'
    ) in xml
    # Bold only for complex script becomes bold for the keys too, and the
    # "treat as complex script" switch goes.
    xml, _, _ = encode(para(run("नेपाल", extra="<w:bCs/><w:cs/>")))
    assert "<w:b/><w:bCs/>" in xml and "<w:cs/>" not in xml


def test_docx_round_trip_gives_the_same_text() -> None:
    _, report, data = encode(BODY)
    back, forward = convert_docx_bytes(data)
    original = "".join(text for text, _ in runs_of(part(build(BODY))))
    assert "".join(text for text, _ in runs_of(part(back))) == original
    assert forward.complete
    # Read with a different XML reader: every part is well formed.
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
    assert report.parts == ("word/document.xml",)


def test_docx_word_list_round_trips_through_a_word_file() -> None:
    words = WORDS[:400]
    body = "".join(para(run(" ".join(words[at : at + 20]))) for at in range(0, len(words), 20))
    _, report, data = encode(body)
    back, _ = convert_docx_bytes(data)
    assert "".join(text for text, _ in runs_of(part(back))) == "".join(
        " ".join(words[at : at + 20]) for at in range(0, len(words), 20)
    )
    assert report.stats.words == 400


def test_docx_other_parts_english_files_and_untouched_bytes() -> None:
    parts = {"word/header1.xml": f'<w:hdr xmlns:w="{W}"><w:p>{run("सरकारी कार्यालय")}</w:p></w:hdr>'}
    data, report = encode_docx_bytes(build(para(run("Only English.")), parts=parts))
    assert report.parts_changed == ("word/header1.xml",)
    assert runs_of(part(data, "word/header1.xml")) == [(";/sf/L sfof{no", "Preeti")]
    english = build(para(run("Only English.", "Calibri")))
    same, report = encode_docx_bytes(english)
    assert part(same) == part(english)
    assert report.stats.words == 0 and report.complete and report.parts_changed == ()


def test_docx_options_reach_the_text() -> None:
    xml, report, _ = encode(para(run("मिति 2083 साल पढ़")), digits="devanagari")
    assert next(item for item in runs_of(xml) if item[0]) == ("ldlt @)*# ;fn ", "Preeti")
    assert [item.text for item in report.left] == ["पढ़"]
    xml, report, _ = encode(para(run("पढ़")), include_unconfirmed=True)
    assert runs_of(xml) == [("k9Þ", "Preeti")] and report.complete
    xml, _, _ = encode(para(run("नेपाल")), font="Preeti Bold")
    assert runs_of(xml) == [("g]kfn", "Preeti Bold")]
    xml, report, _ = encode(para(run("विद्या ६")), strict=True)
    assert next(item for item in runs_of(xml) if item[0]) == ("ljbØf ", "Preeti")
    assert [item.text for item in report.left] == ["६"]
    with pytest.raises(ValueError):
        encode_docx_bytes(build(para(run("क"))), font=" ")
    with pytest.raises(TypeError):
        encode_docx_bytes("text")  # type: ignore[arg-type]


def test_docx_tabs_and_breaks_inside_a_run_survive() -> None:
    body = (
        '<w:p><w:r><w:t xml:space="preserve">नाम</w:t><w:tab/>'
        '<w:t xml:space="preserve">Ram थापा</w:t><w:br/><w:t>ठेगाना</w:t></w:r></w:p>'
    )
    xml, report, data = encode(body)
    assert xml.count("<w:tab/>") == 1 and xml.count("<w:br/>") == 1
    assert [text for text, _ in runs_of(xml) if text] == ["gfd", "Ram ", "yfkf", "7]ufgf"]
    back, _ = convert_docx_bytes(data)
    assert "".join(text for text, _ in runs_of(part(back))) == "नामRam थापाठेगाना"
    assert report.runs_split == 1


def test_encode_docx_writes_a_new_file_and_never_the_input(tmp_path: Path) -> None:
    source = tmp_path / "in.docx"
    source.write_bytes(build(para(run("नेपाल सरकार"))))
    before = source.read_bytes()
    target = tmp_path / "out.docx"
    report = encode_docx(source, target)
    assert source.read_bytes() == before
    assert runs_of(part(target.read_bytes())) == [("g]kfn ;/sf/", "Preeti")]
    assert report.as_dict()["direction"] == "unicode-to-preeti"
    assert report.as_dict()["stats"]["share_words"] == 1.0
    with pytest.raises(ValueError, match="already exists"):
        encode_docx(source, target)
    with pytest.raises(ValueError, match="input file"):
        encode_docx(source, source, overwrite=True)
    encode_docx(source, target, overwrite=True)
    assert source.read_bytes() == before


# --- command line --------------------------------------------------------------------------


def test_cli_docx_to_preeti(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "in.docx"
    source.write_bytes(build(BODY))
    target = tmp_path / "out.docx"
    argv = ["convert", "preeti", "--to", "preeti", "--docx", str(source), "-o", str(target)]
    code, out, err = cli([*argv, "--quiet", "--report"], capsys)
    assert (code, out) == (0, "")
    assert err.splitlines() == [
        "aksharkit: warning: 2 stretch(es) of Nepali text were left in Unicode, in the font "
        "they had",
        "  word/document.xml, paragraph 1: अड्\u200cडा (no key: ? (U+200C))",
        "  word/document.xml, paragraph 1: - (no key: - (U+002D))",
        "aksharkit: docx: 3 run(s) written as keys and set to Preeti, 1 mixed run(s) cut into "
        "pieces, 3 run(s) left as they were, 2 paragraph(s) changed, 1 word(s) moved whole "
        "into their first run; parts read: word/document.xml",
        "aksharkit: summary: 12 of 14 Nepali word(s) written as keys (85.7%); 61 character(s) "
        "written as keys, 7 left with no key, 0 in words that did not read back, 18 not "
        "Devanagari and left alone",
    ]
    assert cli([*argv, "--quiet"], capsys)[0] == 2  # exists: needs --force
    code, out, _ = cli([*argv, "--quiet", "--force", "--json"], capsys)
    payload = json.loads(out)
    assert payload["direction"] == "unicode-to-preeti" and payload["font"] == "Preeti"
    assert payload["stats"]["words_encoded"] == 12 and len(payload["left"]) == 2
    assert cli([*argv, "--quiet", "--force", "--fail-on-unmapped"], capsys)[0] == 1
    back = tmp_path / "back.docx"
    assert (
        cli(["convert", "preeti", "--docx", str(target), "-o", str(back), "--quiet"], capsys)[0]
        == 0
    )
    assert "".join(t for t, _ in runs_of(part(back.read_bytes()))) == "".join(
        t for t, _ in runs_of(part(build(BODY)))
    )


def test_cli_text_files_to_preeti(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    one = tmp_path / "one.txt"
    two = tmp_path / "two.txt"
    one.write_bytes("नेपाल सरकार\r\nदर्ता नं. 245\n".encode())
    two.write_bytes("गृह मन्त्रालय ।\n".encode())
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    argv = ["convert", "preeti", "--to", "preeti", "--quiet", "--out-dir", str(out_dir)]
    code, _, err = cli([*argv, "-i", str(one), "-i", str(two)], capsys)
    assert code == 0
    assert (out_dir / "one.txt").read_bytes() == b"g]kfn ;/sf/\r\nbtf{ g+= 245\n"
    assert (out_dir / "two.txt").read_bytes() == b"u[x dGqfno .\n"
    assert "1 stretch(es) with no Devanagari" in err
    code, _, _ = cli(
        [*argv, "-i", str(one), "--force", "--digits", "devanagari", "--mark-kept", "{{", "}}"],
        capsys,
    )
    assert (out_dir / "one.txt").read_bytes() == b"g]kfn ;/sf/\r\nbtf{ g+= @$%\n"
    code, out, _ = cli(
        [
            "convert",
            "preeti",
            "दर्ता 245 Nepal",
            "--to",
            "preeti",
            "--quiet",
            "--mark-kept",
            "{{",
            "}}",
        ],
        capsys,
    )
    assert out == "btf{ {{245}} {{Nepal}}\n"
    code, out, _ = cli(
        ["convert", "preeti", out.strip(), "--quiet", "--markers", "{{", "}}"], capsys
    )
    assert out == "दर्ता 245 Nepal\n"


def test_cli_options_that_do_not_fit_are_refused(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = cli(["convert", "preeti", "g]kfn", "--digits", "devanagari"], capsys)
    assert code == 2 and "apply to --to preeti only" in err
    code, _, err = cli(["convert", "preeti", "g]kfn", "--mark-kept", "[", "]"], capsys)
    assert code == 2 and "apply to --to preeti only" in err


# --- package and wording ---------------------------------------------------------------------


def test_new_names_are_exported() -> None:
    for name in (
        "DocxEncodeReport",
        "DocxLeft",
        "ForeignSpan",
        "PreetiEncodeStats",
        "PreetiSegment",
        "encode_docx",
        "encode_docx_bytes",
    ):
        assert name in aksharkit.__all__ and hasattr(aksharkit, name)
    assert aksharkit.__version__ == "0.9.0"


def test_docs_never_claim_more_than_was_checked() -> None:
    for name in (
        "README.md",
        "CHANGELOG.md",
        "ROADMAP.md",
        "docs/preeti.md",
        "docs/known-issues.md",
    ):
        text = (ROOT / name).read_text("utf-8")
        section = text
        if name == "CHANGELOG.md":
            section = text[text.index("## 0.8.0") : text.index("## 0.7.0")]
            assert "Not released on PyPI." in section
            assert "### Not verified" in section
        assert "perfect" not in section.lower(), name
    for name in ("index.html", "app.js", "playground.py"):
        assert "perfect" not in (ROOT / "site" / name).read_text("utf-8").lower(), name
    page = (ROOT / "site" / "index.html").read_text("utf-8")
    panel = page[page.index('id="panel-preeti"') :]
    panel = panel[: panel.index("</section>")]
    assert "verified" not in panel.lower() and "Tested on real documents" in panel
    preeti = (ROOT / "docs" / "preeti.md").read_text("utf-8")
    assert "24 November 2026" in preeti and "phone" in preeti
