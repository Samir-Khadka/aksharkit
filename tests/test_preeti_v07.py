"""Preeti in 0.7: protected stretches, the detailed report, Unicode to Preeti, files.

As in ``test_preeti.py``, every Preeti sample here was typed from the table
by the builder. The tests show that the pieces behave as documented. They do
not show that a real Preeti document converts correctly.
"""

from __future__ import annotations

import io
import json
import random
import re
from pathlib import Path

import pytest

import aksharkit
from aksharkit import (
    PreetiEncodeResult,
    PreetiStats,
    convert_preeti,
    encode_preeti,
    legacy,
    preeti_to_unicode,
    unicode_to_preeti,
)
from aksharkit._data import load_table
from aksharkit.cli import main
from aksharkit.normalize import normalize

TABLE = load_table("font_preeti")
CONSONANTS = [chr(code) for code in range(0x0915, 0x093A) if chr(code) not in "ऩऱळऴ"]
VOWEL_SIGNS = ["", "ा", "ि", "ी", "ु", "ू", "ृ", "े", "ै", "ो", "ौ"]
FINALS = ["", "ँ", "ं", "ः"]
VOWELS = "अआइईउऊऋएऐओऔ"


def canonical(text: str) -> str:
    return normalize(text, whitespace=False, danda=False)


# --- protected stretches ------------------------------------------------------


def test_web_and_email_addresses_are_left_alone_by_default() -> None:
    text = "g]kfn www.example.com.np / https://a.org/x?y=1, info@example.org ."
    result = convert_preeti(text)
    assert result.text == "नेपाल www.example.com.np र https://a.org/x?y=1, info@example.org ।"
    assert [(span.text, span.reason) for span in result.protected] == [
        ("www.example.com.np", "link"),
        ("https://a.org/x?y=1", "link"),
        ("info@example.org", "link"),
    ]
    assert result.complete
    for span in result.protected:
        assert text[span.start : span.end] == span.text
        assert result.text[span.output_offset : span.output_offset + len(span.text)] == span.text


def test_punctuation_after_an_address_is_still_converted() -> None:
    assert preeti_to_unicode("www.example.com.") == "www.example.com।"
    assert preeti_to_unicode("-http://x.np_") == "(http://x.np)"


def test_keep_links_can_be_switched_off() -> None:
    result = convert_preeti("www.example.com", keep_links=False)
    assert result.protected == ()
    assert "www" not in result.text


def test_an_at_sign_between_preeti_words_is_still_the_digit_two() -> None:
    # "@" is the Preeti key for २. Only something shaped like name@host.tld is kept.
    assert preeti_to_unicode("@)*# ;fn") == "२०८३ साल"
    assert preeti_to_unicode("s @ v") == "क २ ख"
    assert convert_preeti("sf@v").protected == ()


def test_the_address_rule_has_a_known_false_positive() -> None:
    # Stated in docs/preeti.md: letters, "@", letters, a full stop and two or
    # more letters with no space anywhere is read as an e-mail address even if
    # it was meant as Preeti. keep_links=False converts it.
    assert convert_preeti("s@v.ug").protected[0].reason == "link"
    assert convert_preeti("s@v.ug", keep_links=False).text == "क२ख।गन"


def test_keep_patterns_leave_matches_alone() -> None:
    result = convert_preeti("g]kfn ABC-123 / XYZ-9 xf]", keep=r"[A-Z]+-\d+")
    assert result.text == "नेपाल ABC-123 र XYZ-9 हो"
    assert [span.reason for span in result.protected] == ["keep", "keep"]
    compiled = re.compile(r"\bNepal\b")
    assert preeti_to_unicode("Nepal g]kfn", keep=[compiled, r"\d+"]) == "Nepal नेपाल"


def test_keep_words_need_to_stand_alone() -> None:
    result = convert_preeti("UNESCO / g]kfn UNESCOs", keep_words=["UNESCO"])
    assert result.text.startswith("UNESCO र नेपाल ")
    assert len(result.protected) == 1
    assert not result.text.endswith("UNESCOs")


def test_markers_protect_and_are_removed() -> None:
    result = convert_preeti("g]kfn [[Mount Everest]] xf]", markers=("[[", "]]"))
    assert result.text == "नेपाल Mount Everest हो"
    span = result.protected[0]
    assert (span.start, span.end, span.text, span.reason) == (6, 23, "Mount Everest", "marker")
    assert result.stats.protected == 17


def test_an_unclosed_marker_is_an_error_with_its_place() -> None:
    with pytest.raises(ValueError, match=r"line 2, column 3 is never closed"):
        convert_preeti("g]kfn\ns [[Everest", markers=("[[", "]]"))


def test_first_claim_wins_and_spans_never_overlap() -> None:
    result = convert_preeti(
        "[[www.example.com]] www.example.org", markers=("[[", "]]"), keep=r"example"
    )
    assert [(span.text, span.reason) for span in result.protected] == [
        ("www.example.com", "marker"),
        ("example", "keep"),
    ]
    ends = [span.end for span in result.protected]
    starts = [span.start for span in result.protected]
    assert all(end <= start for end, start in zip(ends, starts[1:], strict=False))


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    [
        ({"keep": "("}, ValueError, "not a valid regular expression"),
        ({"keep": [3]}, TypeError, "keep must be"),
        ({"keep_words": "word"}, TypeError, "list of words"),
        ({"keep_words": [""]}, ValueError, "non-empty"),
        ({"markers": ("[[", "")}, ValueError, "two non-empty strings"),
        ({"markers": ("[[",)}, ValueError, "two non-empty strings"),
    ],
)
def test_bad_protection_arguments(kwargs: dict[str, object], error: type, match: str) -> None:
    with pytest.raises(error, match=match):
        convert_preeti("g]kfn", **kwargs)  # type: ignore[arg-type]


def test_no_english_guessing() -> None:
    # Plain ASCII words are Preeti words. Nothing "looks English" to the converter.
    assert preeti_to_unicode("dfof sdn gfd") == "माया कमल नाम"
    assert preeti_to_unicode("the cat") == "तजभ अबत"


def test_text_must_be_a_string() -> None:
    with pytest.raises(TypeError):
        convert_preeti(b"g]kfn")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        encode_preeti(None)  # type: ignore[arg-type]


# --- report detail ------------------------------------------------------------


def test_unmapped_characters_carry_line_column_and_output_offset() -> None:
    text = "g]kfn ¥\n\ts Ý m\r\nlj{"
    result = convert_preeti(text)
    assert [(u.char, u.offset, u.line, u.column) for u in result.unmapped] == [
        ("¥", 6, 1, 7),
        ("Ý", 11, 2, 4),
        ("m", 13, 2, 6),
    ]
    for item in result.unmapped:
        assert result.text[item.output_offset] == item.char
        assert text[item.offset] == item.char


def test_output_offsets_hold_on_random_input() -> None:
    rng = random.Random(707)
    alphabet = [*TABLE["mapping"], *TABLE["majority"], *TABLE["disputed"], "m", "{", " ", "\n"]
    for _ in range(2000):
        text = "".join(rng.choices(alphabet, k=rng.randint(0, 40)))
        result = convert_preeti(text)
        offsets = [item.output_offset for item in result.unmapped]
        assert offsets == sorted(offsets)
        assert len(set(offsets)) == len(offsets)
        for item in result.unmapped:
            assert result.text[item.output_offset] == item.char
        stats = result.stats
        assert stats.total == len(text)
        assert stats.unmapped == len(result.unmapped)


def test_equality_ignores_the_extra_fields() -> None:
    assert legacy.UnmappedChar("¥", 3) == legacy.UnmappedChar("¥", 3, 2, 1, 9)
    first = convert_preeti("g]kfn")
    assert first == legacy.PreetiResult("नेपाल", ())


def test_stats_count_every_input_character_once() -> None:
    result = convert_preeti("ljBfno ^ ¥ नेपाल www.a.np")
    stats = result.stats
    assert stats == PreetiStats(
        agreed=5, majority=2, unconfirmed=0, unmapped=1, untouched=9, protected=8
    )
    assert stats.converted == 7 and stats.convertible == 8
    assert stats.total == len("ljBfno ^ ¥ नेपाल www.a.np")
    assert stats.share("agreed") == pytest.approx(5 / 8)
    assert stats.share("majority") == pytest.approx(2 / 8)
    assert stats.share("unmapped") == pytest.approx(1 / 8)
    with pytest.raises(ValueError, match="unknown kind"):
        stats.share("protected")


def test_stats_tiers_follow_the_switches() -> None:
    assert convert_preeti("B", strict=True).stats.unmapped == 1
    unconfirmed = convert_preeti("a8Þf ‘", include_unconfirmed=True).stats
    assert unconfirmed.unconfirmed == 3 and unconfirmed.agreed == 2
    stroke = convert_preeti("km m").stats
    assert (stroke.agreed, stroke.unmapped) == (2, 1)
    assert convert_preeti("{").stats.unmapped == 1
    assert convert_preeti("").stats.share("agreed") == 0.0


def test_stats_add_up() -> None:
    total = convert_preeti("s ¥").stats + convert_preeti("B").stats
    assert (total.agreed, total.majority, total.unmapped, total.untouched) == (1, 1, 1, 1)


def test_as_dict_is_json_ready() -> None:
    result = convert_preeti("s ¥ ¥ www.a.np")
    payload = json.loads(json.dumps(result.as_dict(), ensure_ascii=False))
    assert payload["direction"] == "preeti-to-unicode"
    assert payload["status"] == legacy.PREETI_LABEL
    assert payload["complete"] is False
    assert payload["text"] == "क ¥ ¥ www.a.np"
    assert payload["unmapped"][0] == {
        "char": "¥",
        "codepoint": "U+00A5",
        "offset": 2,
        "line": 1,
        "column": 3,
        "output_offset": 2,
    }
    assert payload["unmapped_counts"] == [{"char": "¥", "codepoint": "U+00A5", "count": 2}]
    assert payload["protected"][0]["reason"] == "link"
    assert payload["stats"]["share_unmapped"] == pytest.approx(2 / 3, abs=1e-4)


# --- Unicode to Preeti ----------------------------------------------------------


def assert_round_trip(text: str, *, strict: bool = False) -> None:
    result = encode_preeti(text, strict=strict)
    assert result.complete, (text, result)
    back = convert_preeti(result.text, strict=strict, keep_links=False)
    assert back.complete, (text, result.text)
    assert back.text == canonical(text), (text, result.text, back.text)


def test_known_words_are_written_with_the_expected_keys() -> None:
    samples = {
        "नेपाल": "g]kfn",
        "काठमाडौं": "sf7df8f}+",
        "विद्यार्थी": "ljBfyL{",
        "कार्यक्रम": "sfo{qmd",
        "प्रधानमन्त्री": "k|wfgdGqL",
        "रुपान्तरण": "?kfGt/0f",
        "आउनुहोस्": "cfpg'xf];\\",
        "संविधान": ";+ljwfg",
        "२०८३ साल": "@)*# ;fn",
        "ऊनी": "pmgL",
        "औषधि": "cf}iflw",
        "ज्ञान": "1fg",
        "क्षेत्र": "If]q",
        "शिक्षा, स्वास्थ्य र रोजगारी": "lzIff, :jf:Yo / /f]huf/L",
        "ईश्वर": "O{Zj/",
        "हृदय": "Åbo",
        "(क) र (ख)": "-s_ / -v_",
        "के छ ?": "s] 5 <",
        "“नेपाल”": "æg]kfnÆ",
    }
    for text, keys in samples.items():
        assert unicode_to_preeti(text) == keys
        assert preeti_to_unicode(keys) == text


def test_every_self_consistency_sample_survives_both_directions() -> None:
    from tests.test_preeti import SELF_CONSISTENCY

    for _, text in SELF_CONSISTENCY:
        result = encode_preeti(text)
        assert not result.skipped
        if result.complete:
            assert preeti_to_unicode(result.text, keep_links=False) == canonical(text)
        else:
            # Only characters outside the table are reported, e.g. the en dash.
            assert all(not ("\u0900" <= ch <= "\u097f") for ch in result.unmapped_chars)


def test_every_consonant_with_every_vowel_sign_and_final() -> None:
    count = 0
    for consonant in CONSONANTS:
        for sign in VOWEL_SIGNS:
            for final in FINALS:
                assert_round_trip(consonant + sign + final)
                count += 1
    assert count == 33 * 11 * 4


def test_reph_on_every_consonant_with_every_vowel_sign() -> None:
    for consonant in CONSONANTS:
        for sign in VOWEL_SIGNS:
            assert_round_trip("र्" + consonant + sign)
            assert_round_trip("र्" + consonant + sign + "ं")


def test_every_pair_of_consonants_as_a_conjunct() -> None:
    for first in CONSONANTS:
        for second in CONSONANTS:
            for sign in ("", "ि", "ा", "ो", "ु"):
                assert_round_trip(first + "्" + second + sign)


def test_every_value_in_the_table_and_its_combinations() -> None:
    values = [
        entry["to"]
        for section in ("mapping", "majority", "sequences")
        for entry in TABLE[section].values()
    ]
    assert len(values) == 131
    for value in values:
        assert_round_trip(value)
        if len(value) > 1 and value[-1] in CONSONANTS:
            for sign in VOWEL_SIGNS:
                assert_round_trip(value + sign)
                assert_round_trip("र्" + value + sign)


def test_vowels_digits_punctuation_and_final_halant() -> None:
    for vowel in VOWELS:
        for final in FINALS:
            assert_round_trip(vowel + final)
    assert_round_trip("०१२३४५६७८९")
    assert_round_trip("क, ख। ग? घ. (ङ) च+छ=ज; झ! ५% १/२ “ञ” ‘ट ॐ ऽ")
    for consonant in CONSONANTS:
        assert_round_trip(consonant + "्")
        assert_round_trip("क" + consonant + "्")


def _syllable(rng: random.Random) -> str:
    cluster = "्".join(rng.choice(CONSONANTS) for _ in range(rng.choice((1, 1, 1, 2, 2, 3))))
    if rng.random() < 0.1:
        cluster = "र्" + cluster
    return cluster + rng.choice(VOWEL_SIGNS) + rng.choice([*FINALS, "", "", ""])


def test_random_well_formed_text_round_trips_exactly() -> None:
    rng = random.Random(2083)
    for _ in range(6000):
        words = []
        for _ in range(rng.randint(1, 4)):
            parts = [
                _syllable(rng) if rng.random() < 0.9 else rng.choice(VOWELS)
                for _ in range(rng.randint(1, 5))
            ]
            words.append("".join(parts))
        text = rng.choice((" ", "\n", "\t", " । ")).join(words)
        assert_round_trip(text)
        assert_round_trip(text, strict=True) if "६" not in text else None


def test_random_devanagari_soup_never_reads_back_differently() -> None:
    # Any order of Devanagari characters, well formed or not. Whatever is
    # written as keys must read back the same; the rest is reported.
    rng = random.Random(77)
    alphabet = [chr(code) for code in range(0x0901, 0x0970)] + [" ", " ", "\n", "\u200d", "\u200c"]
    skipped = 0
    for _ in range(4000):
        text = "".join(rng.choices(alphabet, k=rng.randint(0, 25)))
        for strict in (False, True):
            result = encode_preeti(text, strict=strict)
            assert all(item.char == canonical(text)[item.offset] for item in result.unmapped)
            skipped += len(result.skipped)
            if result.skipped:
                # Left in Unicode, and reported. Such a word is not well formed.
                assert all(span.text in result.text for span in result.skipped)
                continue
            back = convert_preeti(result.text, strict=strict, keep_links=False)
            assert back.text == canonical(text), (text, result.text)
    assert skipped > 0  # the soup does exercise the "leave it in Unicode" path


def test_characters_without_a_key_are_reported_not_guessed() -> None:
    result = encode_preeti("नेपाल 2026 ok ड़ ॥ ॉ")
    assert result.text == "g]kfn 2026 ok 8़ ॥ ॉ"
    assert result.unmapped_chars == ("2", "0", "6", "o", "k", "़", "॥", "ॉ")
    assert not result.complete
    first = result.unmapped[0]
    assert (first.char, first.offset, first.line, first.column) == ("2", 6, 1, 7)
    assert result.text[first.output_offset] == "2"
    assert result.encoded == 6


def test_a_word_that_does_not_read_back_is_left_in_unicode() -> None:
    result = encode_preeti("नेपाल क्ा हो")
    assert result.text == "g]kfn क्ा xf]"
    assert [(span.text, span.start, span.line, span.column) for span in result.skipped] == [
        ("क्ा", 6, 1, 7)
    ]
    assert result.text[result.skipped[0].output_offset :].startswith("क्ा")
    assert not result.complete and result.unmapped == ()


def test_strict_uses_only_keys_every_family_agrees_on() -> None:
    assert unicode_to_preeti("रू") == "¿"
    assert unicode_to_preeti("रू", strict=True) == '/"'
    assert unicode_to_preeti("विद्या") == "ljBf"
    assert unicode_to_preeti("विद्या", strict=True) == "ljbØf"
    assert encode_preeti("६", strict=True).unmapped_chars == ("६",)
    for key in unicode_to_preeti("रू द्य ६ ज्ञ्", strict=True):
        assert key not in TABLE["majority"]


def test_unconfirmed_and_disputed_keys_are_never_written() -> None:
    forbidden = set(TABLE["unconfirmed"]) | set(TABLE["disputed"]) | {"Þ"}
    rng = random.Random(5)
    for _ in range(1500):
        text = " ".join("".join(_syllable(rng) for _ in range(3)) for _ in range(3))
        assert not forbidden & set(unicode_to_preeti(text))


def test_input_is_normalised_first_and_positions_refer_to_that() -> None:
    assert unicode_to_preeti("काे") == "sf]"  # ा + े is ो
    assert unicode_to_preeti("र्इ") == "O{"  # र्इ is ई
    result = encode_preeti("कााx")
    assert result.text == "sfx" and result.unmapped[0].offset == 2


def test_protection_works_in_the_reverse_direction_too() -> None:
    result = encode_preeti(
        "नेपाल www.example.com [[Nepal]] UN", markers=("[[", "]]"), keep_words=["UN"]
    )
    assert result.text == "g]kfn www.example.com Nepal UN"
    assert [span.reason for span in result.protected] == ["link", "marker", "word"]
    assert result.unmapped == () and result.complete


def test_encode_result_as_dict() -> None:
    payload = json.loads(json.dumps(encode_preeti("नेपाल x क्ा").as_dict(), ensure_ascii=False))
    assert payload["direction"] == "unicode-to-preeti"
    assert payload["complete"] is False
    assert payload["text"] == "g]kfn x क्ा"
    assert payload["encoded"] == 5
    assert payload["unmapped"][0]["codepoint"] == "U+0078"
    assert payload["skipped"][0]["text"] == "क्ा"
    assert isinstance(encode_preeti(""), PreetiEncodeResult)
    assert encode_preeti("").complete


def test_new_names_are_exported() -> None:
    for name in (
        "encode_preeti",
        "unicode_to_preeti",
        "PreetiEncodeResult",
        "PreetiStats",
        "convert_docx",
        "convert_docx_bytes",
        "DocxReport",
    ):
        assert name in aksharkit.__all__ and hasattr(aksharkit, name)


# --- command line: files, protection, JSON -----------------------------------


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_file_to_file_keeps_line_endings_tabs_and_blank_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "in.txt"
    target = tmp_path / "out.txt"
    source.write_bytes(b"g]kfn\r\n\r\n\td]/f]  gfd\n\n\nxf]")
    code, out, err = run(["convert", "preeti", "-i", str(source), "-o", str(target)], capsys)
    assert code == 0 and out == ""
    assert err == f"aksharkit: note: Preeti conversion is {legacy.PREETI_LABEL}\n"
    assert target.read_bytes() == "नेपाल\r\n\r\n\tमेरो  नाम\n\n\nहो".encode()
    assert source.read_bytes() == b"g]kfn\r\n\r\n\td]/f]  gfd\n\n\nxf]"


def test_cli_file_to_stdout_adds_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "in.txt"
    source.write_bytes(b"g]kfn\n\nxf]\n")
    code, out, _ = run(["convert", "preeti", "-i", str(source), "--quiet"], capsys)
    assert (code, out) == (0, "नेपाल\n\nहो\n")
    source.write_bytes(b"g]kfn")
    assert run(["convert", "preeti", "-i", str(source), "--quiet"], capsys)[1] == "नेपाल"


def test_cli_accepts_a_byte_order_mark_and_other_encodings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "bom.txt"
    source.write_bytes(b"\xef\xbb\xbfg]kfn\n")
    assert run(["convert", "preeti", "-i", str(source), "--quiet"], capsys)[1] == "नेपाल\n"
    legacy_file = tmp_path / "cp1252.txt"
    legacy_file.write_bytes("æg]kfnÆ ‰".encode("cp1252"))
    code, _, err = run(["convert", "preeti", "-i", str(legacy_file), "--quiet"], capsys)
    assert code == 2
    assert "is not valid utf-8 (byte 0)" in err and "--encoding cp1252" in err
    code, out, _ = run(
        ["convert", "preeti", "-i", str(legacy_file), "--quiet", "--encoding", "cp1252"], capsys
    )
    assert (code, out) == (0, "“नेपाल” झ्")
    code, _, err = run(["convert", "preeti", "-i", str(source), "--encoding", "nope"], capsys)
    assert code == 2 and "unknown encoding" in err


def test_cli_never_overwrites_the_input_or_an_existing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "in.txt"
    source.write_bytes(b"g]kfn\n")
    code, _, err = run(["convert", "preeti", "-i", str(source), "-o", str(source)], capsys)
    assert code == 2 and "the output file is the input file" in err
    code, _, err = run(
        ["convert", "preeti", "-i", str(source), "-o", str(source), "--force"], capsys
    )
    assert code == 2 and "the output file is the input file" in err
    assert source.read_bytes() == b"g]kfn\n"
    target = tmp_path / "out.txt"
    target.write_text("keep me", "utf-8")
    code, _, err = run(["convert", "preeti", "-i", str(source), "-o", str(target)], capsys)
    assert code == 2 and "already exists; use --force" in err
    assert target.read_text("utf-8") == "keep me"
    assert (
        run(["convert", "preeti", "-i", str(source), "-o", str(target), "--force"], capsys)[0] == 0
    )
    assert target.read_text("utf-8") == "नेपाल\n"


def test_cli_clear_errors_for_bad_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing.txt"
    code, _, err = run(["convert", "preeti", "-i", str(missing), "--quiet"], capsys)
    assert code == 2 and "cannot read" in err and "missing.txt" in err
    code, _, err = run(["convert", "preeti", "-i", str(tmp_path), "--quiet"], capsys)
    assert code == 2 and "is a directory" in err
    source = tmp_path / "in.txt"
    source.write_bytes(b"s")
    code, _, err = run(
        ["convert", "preeti", "-i", str(source), "-o", str(tmp_path / "no" / "out.txt")], capsys
    )
    assert code == 2 and "does not exist" in err
    code, _, err = run(["convert", "preeti", "s", "-i", str(source)], capsys)
    assert code == 2 and "not several of them" in err
    code, _, err = run(["convert", "preeti", "-i", str(source), "-i", str(source)], capsys)
    assert code == 2 and "need --out-dir" in err
    binary = tmp_path / "old.txt"
    binary.write_bytes(b"\xd0\xcf\x11\xe0rest")
    code, _, err = run(["convert", "preeti", "-i", str(binary)], capsys)
    assert code == 2 and "is not plain text" in err


def test_cli_standard_input_as_a_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("g]kfn\n\n\txf]\n"))
    code, out, _ = run(["convert", "preeti", "-i", "-", "--quiet"], capsys)
    assert (code, out) == (0, "नेपाल\n\n\tहो\n")


def test_cli_batch_into_a_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_bytes(b"g]kfn\n")
    second.write_bytes("s ¥\n".encode())
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    argv = ["convert", "preeti", "-i", str(first), "-i", str(second), "--out-dir", str(out_dir)]
    code, out, err = run([*argv, "--quiet", "--report"], capsys)
    assert code == 0 and out == ""
    assert (out_dir / "a.txt").read_text("utf-8") == "नेपाल\n"
    assert (out_dir / "b.txt").read_text("utf-8") == "क ¥\n"
    assert f"aksharkit: file {first}" in err and f"aksharkit: file {second}" in err
    assert "  line 1, column 3: ¥ (U+00A5)" in err
    code, _, err = run([*argv, "--quiet"], capsys)
    assert code == 2 and "already exists" in err
    code, _, err = run(
        ["convert", "preeti", "-i", str(first), "--out-dir", str(tmp_path), "--quiet"], capsys
    )
    assert code == 2 and "the output file is the input file" in err
    code, _, err = run(["convert", "preeti", "s", "--out-dir", str(out_dir)], capsys)
    assert code == 2 and "--out-dir needs input files" in err


def test_cli_protection_options(capsys: pytest.CaptureFixture[str]) -> None:
    text = "g]kfn [[Everest]] ABC-12 UN www.a.np"
    argv = ["convert", "preeti", text, "--quiet", "--markers", "[[", "]]"]
    code, out, _ = run([*argv, "--keep", r"[A-Z]+-\d+", "--keep-word", "UN"], capsys)
    assert (code, out) == (0, "नेपाल Everest ABC-12 UN www.a.np\n")
    out = run(["convert", "preeti", "www.a.np", "--quiet", "--no-keep-links"], capsys)[1]
    assert "www" not in out
    code, _, err = run(["convert", "preeti", "s [[x", "--quiet", "--markers", "[[", "]]"], capsys)
    assert code == 2 and "never closed" in err
    code, _, err = run(["convert", "preeti", "s", "--quiet", "--keep", "("], capsys)
    assert code == 2 and "not a valid regular expression" in err


def test_cli_json_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["convert", "preeti", "ljBfno ¥", "--json", "--quiet"], capsys)
    payload = json.loads(out)
    assert code == 0
    assert payload["text"] == "विद्यालय ¥"
    assert payload["stats"]["majority"] == 1
    assert payload["unmapped"][0]["column"] == 8
    assert "warning: 1 character(s)" in err
    source = tmp_path / "in.txt"
    source.write_bytes(b"g]kfn\n")
    target = tmp_path / "out.txt"
    code, out, _ = run(
        ["convert", "preeti", "-i", str(source), "-o", str(target), "--json", "--quiet"], capsys
    )
    payload = json.loads(out)
    assert "text" not in payload
    assert payload["input"] == str(source) and payload["output"] == str(target)
    assert payload["complete"] is True
    assert target.read_text("utf-8") == "नेपाल\n"


def test_cli_fail_on_unmapped(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["convert", "preeti", "s ¥", "--quiet"], capsys)[0] == 0
    code, out, _ = run(["convert", "preeti", "s ¥", "--quiet", "--fail-on-unmapped"], capsys)
    assert (code, out) == (1, "क ¥\n")
    assert run(["convert", "preeti", "s", "--quiet", "--fail-on-unmapped"], capsys)[0] == 0


def test_cli_to_preeti(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["convert", "preeti", "नेपाल कर्म", "--to", "preeti"], capsys)
    assert (code, out) == (0, "g]kfn sd{\n")
    assert err == f"aksharkit: note: Preeti conversion is {legacy.PREETI_LABEL}\n"
    code, out, err = run(
        ["convert", "preeti", "नेपाल ok क्ा", "--to", "preeti", "--quiet", "--report"], capsys
    )
    assert out == "g]kfn ok क्ा\n"
    assert err.splitlines() == [
        "aksharkit: warning: 2 character(s) had no Preeti key and were left unchanged: "
        "o (U+006F) k (U+006B)",
        "  line 1, column 7: o (U+006F)",
        "  line 1, column 8: k (U+006B)",
        "aksharkit: warning: 1 word(s) were left in Unicode because their Preeti keys "
        "did not convert back to the same text",
        "  line 1, column 10: क्ा",
        "aksharkit: summary: 5 character(s) written as keys, 2 with no key, "
        "1 word(s) skipped, 0 stretch(es) protected",
    ]
    code, _, err = run(
        ["convert", "preeti", "क", "--to", "preeti", "--include-unconfirmed", "--quiet"], capsys
    )
    assert code == 2 and "no meaning with --to preeti" in err
    source = tmp_path / "u.txt"
    source.write_bytes("नेपाल\r\nहो\n".encode())
    target = tmp_path / "p.txt"
    argv = ["convert", "preeti", "-i", str(source), "-o", str(target), "--to", "preeti", "--quiet"]
    assert run(argv, capsys)[0] == 0
    assert target.read_bytes() == b"g]kfn\r\nxf]\n"


def test_cli_text_argument_to_output_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "o.txt"
    code, out, _ = run(["convert", "preeti", "g]kfn", "-o", str(target), "--quiet"], capsys)
    assert (code, out) == (0, "")
    assert target.read_text("utf-8") == "नेपाल\n"


def test_cli_text_may_come_after_the_options(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["convert", "preeti", "--quiet", "--to", "preeti", "नेपाल"], capsys)
    assert (code, out) == (0, "g]kfn\n")
    code, out, _ = run(["convert", "preeti", "--quiet", "--strict", "g]kfn"], capsys)
    assert (code, out) == (0, "नेपाल\n")
    for argv in (
        ["convert", "preeti", "--quiet", "g]kfn", "extra"],
        ["convert", "preeti", "--quiet", "--bogus"],
        ["convert", "preeti", "g]kfn", "--quiet", "extra"],
        ["digits", "5", "6"],
    ):
        with pytest.raises(SystemExit) as stopped:
            main(argv)
        assert stopped.value.code == 2, argv
        assert "unrecognized arguments" in capsys.readouterr().err
