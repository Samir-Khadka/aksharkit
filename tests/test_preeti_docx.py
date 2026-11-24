"""Preeti runs inside Word (.docx) files.

Every .docx here is built in the test from strings with ``zipfile``: there
is no real Word document in the repository, and none written by Microsoft
Word has been converted. The tests show that the converter finds the runs
it says it finds, changes only those, and leaves the rest byte-for-byte.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from aksharkit import DocxReport, convert_docx, convert_docx_bytes, convert_preeti, legacy
from aksharkit.cli import main
from aksharkit.legacy_docx import DEFAULT_DOCX_FONT, DocxUnmapped

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f'xmlns:w="{W_NS}"'
PREETI_RPR = '<w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/></w:rPr>'
HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

CONTENT_TYPES = (
    HEAD + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.styles+xml"/>'
    "</Types>"
)
RELS = (
    HEAD + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/></Relationships>'
)
DOC_RELS = (
    HEAD + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/styles" Target="styles.xml"/></Relationships>'
)
STYLES = (
    HEAD + f"<w:styles {W}><w:docDefaults><w:rPrDefault><w:rPr>"
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Mangal"/>'
    '<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
    "</w:style>"
    '<w:style w:type="paragraph" w:styleId="NepBase"><w:name w:val="Nep Base"/>'
    '<w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/><w:sz w:val="28"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="NepHead"><w:name w:val="Nep Head"/>'
    '<w:basedOn w:val="NepBase"/><w:rPr><w:b/></w:rPr></w:style>'
    '<w:style w:type="character" w:styleId="NepChar"><w:name w:val="Nep Char"/>'
    '<w:rPr><w:rFonts w:ascii="PREETI" w:hAnsi="preeti"/><w:i/></w:rPr></w:style>'
    '<w:style w:type="character" w:styleId="NepCharKid"><w:name w:val="Nep Char Kid"/>'
    '<w:basedOn w:val="NepChar"/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Loop"><w:basedOn w:val="Loop"/></w:style>'
    "</w:styles>"
)


def run(text: str, font: str | None = None, extra: str = "", style: str | None = None) -> str:
    """One run. ``text`` is XML: escape it yourself when it needs escaping."""
    props = ""
    if style:
        props += f'<w:rStyle w:val="{style}"/>'
    if font:
        props += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>'
    props += extra
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>'


def para(*runs: str, style: str | None = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


def document(body: str) -> str:
    return f"{HEAD}<w:document {W}><w:body>{body}<w:sectPr/></w:body></w:document>"


def build(
    body: str, *, parts: dict[str, str | bytes] | None = None, styles: str | None = STYLES
) -> bytes:
    files: dict[str, str | bytes] = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": RELS,
        "word/document.xml": document(body),
        "word/_rels/document.xml.rels": DOC_RELS,
    }
    if styles is not None:
        files["word/styles.xml"] = styles
    files.update(parts or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def part(data: bytes, name: str = "word/document.xml") -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read(name).decode("utf-8")


def runs_of(xml: str) -> list[tuple[str, str | None]]:
    """``(text, ascii font)`` of every run of a part, read with a real XML parser."""
    root = ElementTree.fromstring(xml)
    out: list[tuple[str, str | None]] = []
    for element in root.iter(f"{{{W_NS}}}r"):
        text = "".join(t.text or "" for t in element.findall(f"{{{W_NS}}}t"))
        fonts = element.find(f"{{{W_NS}}}rPr/{{{W_NS}}}rFonts")
        out.append((text, None if fonts is None else fonts.get(f"{{{W_NS}}}ascii")))
    return out


def convert(body: str, **kwargs: object) -> tuple[str, DocxReport]:
    data, report = convert_docx_bytes(build(body), **kwargs)  # type: ignore[arg-type]
    return part(data), report


MIXED_BODY = (
    para(
        run("Report 2026: ", "Calibri", "<w:b/>"),
        run("g]kfnsf] /fhwfgL sf7df8f}+ xf]", "Preeti", '<w:b/><w:sz w:val="32"/>'),
        run(".", "Preeti"),
        run(" (Kathmandu)", "Calibri"),
    )
    + para(run("k|yd lzif{s"), style="NepHead")
    + "<w:tbl><w:tr><w:tc>"
    + para(run("Name", "Calibri"))
    + "</w:tc><w:tc>"
    + para(run("gfd", "Preeti"))
    + "</w:tc></w:tr></w:tbl>"
)
MIXED_PARTS: dict[str, str | bytes] = {
    "word/header1.xml": f"{HEAD}<w:hdr {W}>{para(run(';/sf/L sfof{no', 'Preeti'))}</w:hdr>",
    "word/footer1.xml": (
        f"{HEAD}<w:ftr {W}>{para(run('Page ', 'Calibri'), run('k[i7', 'Preeti'))}</w:ftr>"
    ),
    "word/footnotes.xml": (
        f'{HEAD}<w:footnotes {W}><w:footnote w:id="2">'
        f"{para(run(';|f]t M ', 'Preeti'), run('Census 2021', 'Calibri'))}"
        "</w:footnote></w:footnotes>"
    ),
    "word/endnotes.xml": (
        f'{HEAD}<w:endnotes {W}><w:endnote w:id="2">{para(run("cGTo", "Preeti"))}'
        "</w:endnote></w:endnotes>"
    ),
    "word/comments.xml": (
        f'{HEAD}<w:comments {W}><w:comment w:id="0">{para(run("l6Kk0fL", "Preeti"))}'
        "</w:comment></w:comments>"
    ),
    "word/media/image1.png": "not really a picture",
}


# --- what is converted and what is not ---------------------------------------


def test_mixed_document_converts_only_preeti_runs() -> None:
    data, report = convert_docx_bytes(build(MIXED_BODY, parts=MIXED_PARTS))
    assert runs_of(part(data)) == [
        ("Report 2026: ", "Calibri"),
        ("नेपालको राजधानी काठमाडौं हो", "Kalimati"),
        ("।", "Kalimati"),
        (" (Kathmandu)", "Calibri"),
        ("प्रथम शिर्षक", "Kalimati"),
        ("Name", "Calibri"),
        ("नाम", "Kalimati"),
    ]
    assert runs_of(part(data, "word/header1.xml")) == [("सरकारी कार्यालय", "Kalimati")]
    assert runs_of(part(data, "word/footer1.xml")) == [("Page ", "Calibri"), ("पृष्ठ", "Kalimati")]
    assert runs_of(part(data, "word/footnotes.xml")) == [
        ("स्रोत : ", "Kalimati"),  # since 0.8: a visarga after a space is a colon
        ("Census 2021", "Calibri"),
    ]
    assert runs_of(part(data, "word/endnotes.xml")) == [("अन्त्य", "Kalimati")]
    assert runs_of(part(data, "word/comments.xml")) == [("टिप्पणी", "Kalimati")]
    assert report.parts == (
        "word/document.xml",
        "word/header1.xml",
        "word/footer1.xml",
        "word/footnotes.xml",
        "word/endnotes.xml",
        "word/comments.xml",
    )
    assert report.parts_changed == report.parts
    assert (report.runs_converted, report.runs_untouched) == (9, 5)
    assert report.paragraphs_changed == 8
    assert report.fonts_seen == {"Calibri": 5, "Preeti": 9}
    assert report.complete and report.unmapped == ()
    assert report.font == "Kalimati" == DEFAULT_DOCX_FONT
    assert report.stats.unmapped == 0 and report.stats.agreed > 60


def test_english_runs_and_other_parts_are_byte_for_byte_the_same() -> None:
    source = build(MIXED_BODY, parts=MIXED_PARTS)
    data, _ = convert_docx_bytes(source)
    out = part(data)
    for original in (
        run("Report 2026: ", "Calibri", "<w:b/>"),
        run(" (Kathmandu)", "Calibri"),
        para(run("Name", "Calibri")),
        '<w:pPr><w:pStyle w:val="NepHead"/></w:pPr>',
        "<w:sectPr/></w:body></w:document>",
    ):
        assert original in out
    assert out.startswith(HEAD)
    with zipfile.ZipFile(io.BytesIO(source)) as before, zipfile.ZipFile(io.BytesIO(data)) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name not in MIXED_PARTS and name != "word/document.xml":
                assert before.read(name) == after.read(name), name
        assert after.read("word/media/image1.png") == b"not really a picture"
        assert after.read("word/styles.xml") == STYLES.encode("utf-8")
        assert after.testzip() is None
        assert all(info.compress_type == zipfile.ZIP_DEFLATED for info in after.infolist())


def test_a_document_without_preeti_comes_back_unchanged() -> None:
    body = para(run("Hello", "Calibri"), run(" world")) + para(run("नेपाल", "Mangal"))
    source = build(body)
    data, report = convert_docx_bytes(source)
    assert part(data) == part(source)
    assert report.runs_converted == 0 and report.runs_untouched == 3
    assert report.parts_changed == () and report.paragraphs_changed == 0
    assert report.fonts_seen == {"Calibri": 2, "Mangal": 1}


def test_every_output_part_is_well_formed_xml() -> None:
    data, _ = convert_docx_bytes(build(MIXED_BODY, parts=MIXED_PARTS))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            if name.endswith((".xml", ".rels")):
                ElementTree.fromstring(archive.read(name))


# --- where the font comes from -------------------------------------------------


def test_font_from_paragraph_style_and_its_parent() -> None:
    out, report = convert(para(run("gfd"), style="NepBase") + para(run("gfd"), style="NepHead"))
    assert runs_of(out) == [("नाम", "Kalimati"), ("नाम", "Kalimati")]
    assert report.runs_converted == 2


def test_font_from_character_style_and_its_parent() -> None:
    out, _ = convert(para(run("gfd", style="NepChar"), run("gfd", style="NepCharKid"), run("x")))
    assert runs_of(out) == [("नाम", "Kalimati"), ("नाम", "Kalimati"), ("x", None)]
    assert '<w:rStyle w:val="NepChar"/><w:rFonts w:ascii="Kalimati"' in out


def test_direct_font_beats_the_style() -> None:
    body = para(run("Name", "Calibri"), run("gfd"), style="NepBase")
    out, report = convert(body)
    assert runs_of(out) == [("Name", "Calibri"), ("नाम", "Kalimati")]
    assert (report.runs_converted, report.runs_untouched) == (1, 1)


def test_character_style_beats_paragraph_style() -> None:
    styles = STYLES.replace(
        "</w:styles>",
        '<w:style w:type="character" w:styleId="Latin"><w:rPr>'
        '<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/></w:rPr></w:style></w:styles>',
    )
    body = para(run("Name", style="Latin"), run("gfd"), style="NepBase")
    data, _ = convert_docx_bytes(build(body, styles=styles))
    assert runs_of(part(data)) == [("Name", None), ("नाम", "Kalimati")]


def test_font_from_document_defaults_and_default_paragraph_style() -> None:
    defaults = STYLES.replace(
        'w:ascii="Calibri" w:hAnsi="Calibri"', 'w:ascii="Preeti" w:hAnsi="Preeti"'
    )
    data, _ = convert_docx_bytes(build(para(run("gfd")), styles=defaults))
    assert runs_of(part(data)) == [("नाम", "Kalimati")]
    normal = STYLES.replace(
        '<w:name w:val="Normal"/>',
        '<w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/></w:rPr>',
    )
    data, _ = convert_docx_bytes(
        build(para(run("gfd")) + para(run("x"), style="Loop"), styles=normal)
    )
    assert runs_of(part(data)) == [("नाम", "Kalimati"), ("x", None)]


def test_font_from_the_theme() -> None:
    theme = (
        f'{HEAD}<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:themeElements><a:fontScheme name="x"><a:majorFont><a:latin typeface="Arial"/>'
        '</a:majorFont><a:minorFont><a:latin typeface="Preeti"/><a:cs typeface="Mangal"/>'
        "</a:minorFont></a:fontScheme></a:themeElements></a:theme>"
    )
    minor = '<w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi" w:ascii="Arial"/>'
    major = '<w:rFonts w:asciiTheme="majorHAnsi" w:hAnsiTheme="majorHAnsi" w:ascii="Preeti"/>'
    body = para(run("gfd", extra=minor), run("gfd", extra=major))
    data, report = convert_docx_bytes(build(body, parts={"word/theme/theme1.xml": theme}))
    assert runs_of(part(data)) == [("नाम", "Kalimati"), ("gfd", "Preeti")]
    assert "Theme" not in part(data).split("</w:r>")[0]
    assert report.fonts_seen == {"Arial": 1, "Preeti": 1}


def test_no_styles_part_at_all() -> None:
    data, report = convert_docx_bytes(build(para(run("gfd", "Preeti"), run("x")), styles=None))
    assert runs_of(part(data)) == [("नाम", "Kalimati"), ("x", None)]
    assert report.fonts_seen == {"(not stated)": 1, "Preeti": 1}


def test_a_run_with_preeti_in_only_one_slot_is_left_alone_and_counted() -> None:
    half = '<w:rFonts w:ascii="Preeti" w:hAnsi="Calibri"/>'
    out, report = convert(para(run("gfd", extra=half), run("gfd", "Preeti")))
    assert runs_of(out) == [("gfd", "Preeti"), ("नाम", "Kalimati")]
    assert (report.runs_partial_font, report.runs_converted) == (1, 1)


def test_font_names_are_compared_without_case_and_can_be_added() -> None:
    out, _ = convert(para(run("gfd", "PREETI"), run("gfd", " preeti ")))
    assert [text for text, _ in runs_of(out)] == ["नाम", "नाम"]
    body = para(run("gfd", "Preeti"), run("gfd", "Kantipur"))
    out, report = convert(body, source_fonts=["Kantipur"], font="Noto Sans Devanagari")
    assert runs_of(out) == [("gfd", "Preeti"), ("नाम", "Noto Sans Devanagari")]
    assert report.source_fonts == ("Kantipur",) and report.font == "Noto Sans Devanagari"
    out, _ = convert(body, source_fonts="Kantipur")
    assert runs_of(out)[1] == ("नाम", "Kalimati")


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"font": ""}, "non-empty font name"),
        ({"font": "preeti"}, "must differ"),
        ({"font": "A\nB"}, "control characters"),
        ({"source_fonts": []}, "at least one font"),
        ({"source_fonts": [""]}, "non-empty font name"),
    ],
)
def test_bad_font_arguments(kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        convert_docx_bytes(build(para(run("s", "Preeti"))), **kwargs)  # type: ignore[arg-type]


# --- words split across runs ---------------------------------------------------


@pytest.mark.parametrize(
    ("pieces", "expected", "moves"),
    [
        # Each piece converts on its own: nothing has to move.
        (["lj", "Bf", "yL{"], ["वि", "द्या", "र्थी"], 0),
        # The short i is typed before its consonant, which is in the next run.
        (["l", "jBfyL{"], ["वि", "द्यार्थी"], 1),
        # The reph is typed after its syllable, which is in the run before.
        (["sd", "{ xf]"], ["कर्म", " हो"], 1),
        # The "m" stroke changes the letter before it.
        (["k", "mn"], ["फ", "ल"], 1),
        # A half form and the bar that completes it.
        (["0", "f g"], ["ण", " न"], 1),
        # ा and े in different runs compose to ो.
        (["sf", "] 5"], ["को", " छ"], 1),
        # Two boundaries, both needing a move.
        (["l", "s", "{"], ["र्कि", "", ""], 2),
        (["g]kfn", "", " xf]"], ["नेपाल", "", " हो"], 0),
    ],
)
def test_words_split_across_runs(pieces: list[str], expected: list[str], moves: int) -> None:
    formats = ["<w:b/>", "<w:i/>", '<w:color w:val="FF0000"/>']
    body = para(*(run(text, "Preeti", formats[i % 3]) for i, text in enumerate(pieces)))
    out, report = convert(body)
    assert [text for text, _ in runs_of(out)] == expected
    assert "".join(expected) == convert_preeti("".join(pieces)).text
    assert report.boundary_moves == moves and report.groups_merged == 0
    # Each run keeps its own formatting.
    for i in range(len(pieces)):
        assert formats[i % 3] in out.split("</w:r>")[i]


def test_split_runs_always_give_the_text_of_the_whole() -> None:
    import random

    rng = random.Random(41)
    words = [
        "ljBfyL{",
        "sfo{qmd",
        "k|wfgdGqL",
        "kl/jt{g",
        "lzIff",
        "cf}iflw",
        "/fli6«o",
        "em08f",
        "pmgL",
        "sd{",
        "lj{",
        "m",
        "¥",
    ]
    for _ in range(300):
        text = " ".join(rng.choices(words, k=rng.randint(1, 4)))
        cuts = sorted(rng.sample(range(len(text) + 1), k=min(len(text), rng.randint(1, 6))))
        pieces = [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)], strict=True)]
        out, report = convert(para(*(run(piece, "Preeti") for piece in pieces)))
        whole = convert_preeti(text, keep_links=False)
        assert "".join(t for t, _ in runs_of(out)) == whole.text, pieces
        assert len(runs_of(out)) == len(pieces)
        assert len(report.unmapped) == len(whole.unmapped)
        assert report.stats.total == len(text)


def test_a_tab_a_break_or_another_font_ends_the_word() -> None:
    tab = f"<w:r>{PREETI_RPR}<w:t>l</w:t><w:tab/><w:t>s</w:t></w:r>"
    out, report = convert(para(tab))
    assert runs_of(out) == [("िक", "Kalimati")]
    assert "<w:tab/>" in out and report.boundary_moves == 0
    out, report = convert(para(run("l", "Preeti"), run("-", "Calibri"), run("s", "Preeti")))
    assert runs_of(out) == [("ि", "Kalimati"), ("-", "Calibri"), ("क", "Kalimati")]
    out, _ = convert(para(run("l", "Preeti")) + para(run("s", "Preeti")))
    assert [text for text, _ in runs_of(out)] == ["ि", "क"]


def test_a_stretch_that_cannot_be_cut_goes_to_its_first_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aksharkit import legacy_docx

    monkeypatch.setattr(legacy_docx, "_MOVE_LIMIT", 0)
    out, report = convert(para(run("l", "Preeti", "<w:b/>"), run("jBfno", "Preeti")))
    assert [text for text, _ in runs_of(out)] == ["विद्यालय", ""]
    assert (report.groups_merged, report.boundary_moves) == (1, 0)


# --- the run properties --------------------------------------------------------


def test_complex_script_bold_italic_and_size_follow_the_latin_ones() -> None:
    out, _ = convert(para(run("s", "Preeti", '<w:b/><w:i/><w:sz w:val="32"/>')))
    assert (
        '<w:rPr><w:rFonts w:ascii="Kalimati" w:hAnsi="Kalimati" w:cs="Kalimati"/>'
        '<w:b/><w:bCs/><w:i/><w:iCs/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr>'
    ) in out
    # Already the same: nothing is added.
    same = '<w:b/><w:bCs/><w:sz w:val="22"/><w:szCs w:val="22"/>'
    out, _ = convert(para(run("s", "Preeti", same)))
    assert f'w:cs="Kalimati"/>{same}</w:rPr>' in out
    # A different complex-script size is replaced; "off" values are understood.
    out, _ = convert(
        para(run("s", "Preeti", '<w:b w:val="0"/><w:bCs/><w:sz w:val="40"/><w:szCs w:val="20"/>'))
    )
    assert '<w:b w:val="0"/><w:bCs w:val="0"/><w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr>' in out


def test_inherited_bold_and_size_are_mirrored_too() -> None:
    out, _ = convert(para(run("s"), style="NepHead"))
    assert (
        '<w:rPr><w:rFonts w:ascii="Kalimati" w:hAnsi="Kalimati" w:cs="Kalimati"/>'
        '<w:bCs/><w:szCs w:val="28"/></w:rPr>'
    ) in out
    out, _ = convert(para(run("s", style="NepChar")))
    assert "<w:iCs/></w:rPr>" in out


def test_other_properties_keep_their_place_and_east_asian_font_survives() -> None:
    fonts = (
        '<w:rFonts w:ascii="Preeti" w:hAnsi="Preeti" w:eastAsia="SimSun" '
        'w:cs="Preeti" w:hint="default"/>'
    )
    extra = (
        f'{fonts}<w:strike/><w:color w:val="FF0000"/><w:sz w:val="24"/><w:szCs w:val="24"/>'
        '<w:u w:val="single"/><w:lang w:val="en-US"/>'
    )
    out, _ = convert(para(run("s", extra=extra, style="NepChar")))
    assert (
        '<w:rPr><w:rStyle w:val="NepChar"/>'
        '<w:rFonts w:ascii="Kalimati" w:hAnsi="Kalimati" w:cs="Kalimati" w:eastAsia="SimSun"/>'
        '<w:iCs/><w:strike/><w:color w:val="FF0000"/><w:sz w:val="24"/><w:szCs w:val="24"/>'
        '<w:u w:val="single"/><w:lang w:val="en-US"/></w:rPr>'
    ) in out


def test_a_run_without_properties_gets_them_and_an_empty_rpr_is_filled() -> None:
    defaults = STYLES.replace(
        'w:ascii="Calibri" w:hAnsi="Calibri"', 'w:ascii="Preeti" w:hAnsi="Preeti"'
    )
    body = para("<w:r><w:t>s</w:t></w:r>", "<w:r><w:rPr/><w:t>v</w:t></w:r>")
    data, _ = convert_docx_bytes(build(body, styles=defaults))
    rpr = '<w:rPr><w:rFonts w:ascii="Kalimati" w:hAnsi="Kalimati" w:cs="Kalimati"/></w:rPr>'
    assert part(data).count(f"<w:r>{rpr}<w:t") == 2
    assert [text for text, _ in runs_of(part(data))] == ["क", "ख"]


def test_tracked_formatting_change_inside_rpr_is_kept_whole() -> None:
    change = (
        '<w:rPrChange w:id="1" w:author="a"><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
        "<w:b/></w:rPr></w:rPrChange>"
    )
    out, _ = convert(para(run("s", "Preeti", change)))
    assert f'w:cs="Kalimati"/>{change}</w:rPr>' in out


# --- awkward XML ---------------------------------------------------------------


def test_escaped_characters_and_awkward_attributes() -> None:
    body = para(
        run("s &amp; v &lt; u &#x21;", "Preeti"),
        '<w:r w:rsidR="a&gt;b" w:rsidRPr=\'x">y\'><w:rPr>'
        '<w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/>'
        "</w:rPr><w:t>u</w:t></w:r>",
        run("A &amp; B &lt;tag&gt;", "Calibri"),
    )
    out, report = convert(body)
    assert runs_of(out) == [
        ("क ७ ख ? ग १", "Kalimati"),
        ("ग", "Kalimati"),
        ("A & B <tag>", "Calibri"),
    ]
    assert '<w:r w:rsidR="a&gt;b" w:rsidRPr=\'x">y\'><w:rPr><w:rFonts w:ascii="Kalimati"' in out
    assert run("A &amp; B &lt;tag&gt;", "Calibri") in out
    assert report.complete


def test_output_text_is_escaped() -> None:
    # Preeti "<" is the question mark, but an unmapped "&" or ">" must stay XML-safe.
    out, report = convert(para(run("s &amp;&gt; ¥", "Preeti")), strict=True, keep=r"[&>]")
    assert "क &amp;&gt; ¥</w:t>" in out
    assert report.unmapped_chars == ("¥",)


def test_other_prefixes_namespaces_bom_and_comments() -> None:
    strict_ns = "http://purl.oclc.org/ooxml/wordprocessingml/main"
    body = (
        f'\ufeff{HEAD}<!-- a > comment --><x:document xmlns:x="{strict_ns}"><x:body><x:p><x:r>'
        '<x:rPr><x:rFonts x:ascii="Preeti" x:hAnsi="Preeti"/></x:rPr><x:t>gfd</x:t></x:r>'
        "<x:r><x:t><![CDATA[a<b]]></x:t></x:r></x:p></x:body></x:document>"
    )
    source = build("", parts={"word/document.xml": body})
    data, report = convert_docx_bytes(source)
    out = part(data)
    assert (
        '<x:r><x:rPr><x:rFonts x:ascii="Kalimati" x:hAnsi="Kalimati" x:cs="Kalimati"/></x:rPr>'
        '<x:t xml:space="preserve">नाम</x:t></x:r>'
    ) in out
    assert "<x:r><x:t><![CDATA[a<b]]></x:t></x:r>" in out and out.startswith("\ufeff")
    assert report.runs_converted == 1


def test_text_boxes_fields_and_deleted_text() -> None:
    box = (
        '<w:r><w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/></w:rPr><w:t>l</w:t>'
        '<w:pict><v:shape xmlns:v="urn:schemas-microsoft-com:vml"><v:textbox><w:txbxContent>'
        + para(run("s", "Preeti"), run("box", "Calibri"))
        + "</w:txbxContent></v:textbox></v:shape></w:pict><w:t>v</w:t></w:r>"
    )
    field = (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/></w:rPr>'
        '<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        + run("!", "Preeti")
        + '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )
    deleted = (
        '<w:del w:id="1" w:author="a"><w:r><w:rPr><w:rFonts w:ascii="Preeti" w:hAnsi="Preeti"/>'
        "</w:rPr><w:delText>gfd</w:delText></w:r></w:del>"
    )
    out, report = convert(para(box) + para(field) + para(deleted))
    texts = [text for text, _ in runs_of(out)]
    assert texts[:3] == ["िख", "क", "box"]
    assert '<w:instrText xml:space="preserve"> PAGE </w:instrText>' in out
    assert "१" in texts
    assert deleted in out
    assert report.paragraphs_changed == 3


def test_unmapped_characters_are_reported_with_part_and_paragraph() -> None:
    body = para(run("s", "Preeti")) + para(run("x", "Calibri")) + para(run("¥ s Ý ¥", "Preeti"))
    footer = f"{HEAD}<w:ftr {W}>{para(run('m', 'Preeti'))}</w:ftr>"
    data, report = convert_docx_bytes(build(body, parts={"word/footer1.xml": footer}))
    assert report.unmapped == (
        DocxUnmapped("word/document.xml", 3, "¥"),
        DocxUnmapped("word/document.xml", 3, "Ý"),
        DocxUnmapped("word/document.xml", 3, "¥"),
        DocxUnmapped("word/footer1.xml", 1, "m"),
    )
    assert report.unmapped_chars == ("¥", "Ý", "m") and not report.complete
    assert runs_of(part(data))[2] == ("¥ क Ý ¥", "Kalimati")
    payload = json.loads(json.dumps(report.as_dict(), ensure_ascii=False))
    assert payload["unmapped"][0] == {
        "part": "word/document.xml",
        "paragraph": 3,
        "char": "¥",
        "codepoint": "U+00A5",
    }
    assert payload["unmapped_counts"][0] == {"char": "¥", "codepoint": "U+00A5", "count": 2}
    assert payload["stats"]["unmapped"] == 4 and payload["status"] == legacy.PREETI_LABEL


def test_tier_switches_and_keep_options_reach_the_runs() -> None:
    body = para(run("ljBfno UNESCO www.a.np", "Preeti"))
    out, report = convert(body, strict=True, keep_words=["UNESCO"], keep_links=True)
    assert runs_of(out)[0][0] == "विBालय UNESCO www.a.np"
    assert report.unmapped_chars == ("B",)
    out, _ = convert(body)
    assert "www" not in runs_of(out)[0][0]  # in a Word file the font decides
    out, _ = convert(para(run("a8Þf", "Preeti")), include_unconfirmed=True)
    assert runs_of(out)[0][0] == "बड़ा"


# --- files -----------------------------------------------------------------------


def test_convert_docx_writes_a_new_file_and_never_the_input(tmp_path: Path) -> None:
    source = tmp_path / "in.docx"
    original = build(MIXED_BODY, parts=MIXED_PARTS)
    source.write_bytes(original)
    target = tmp_path / "out.docx"
    report = convert_docx(source, target)
    assert report.runs_converted == 9 and source.read_bytes() == original
    assert runs_of(part(target.read_bytes()))[1][0] == "नेपालको राजधानी काठमाडौं हो"
    with pytest.raises(ValueError, match="already exists"):
        convert_docx(source, target)
    convert_docx(str(source), str(target), overwrite=True, font="Mangal")
    assert runs_of(part(target.read_bytes()))[1][1] == "Mangal"
    for same in (source, tmp_path / "sub" / ".." / "in.docx"):
        with pytest.raises(ValueError, match="the output file is the input file"):
            convert_docx(source, same, overwrite=True)
    link = tmp_path / "link.docx"
    try:
        link.symlink_to(source)
    except OSError:
        return
    with pytest.raises(ValueError, match="the output file is the input file"):
        convert_docx(source, link, overwrite=True)
    assert source.read_bytes() == original


def test_convert_docx_refuses_what_is_not_a_docx(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no such file"):
        convert_docx(tmp_path / "missing.docx", tmp_path / "o.docx")
    with pytest.raises(ValueError, match=r"old \.doc file or a password-protected"):
        convert_docx_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64)
    with pytest.raises(ValueError, match="not a zip archive"):
        convert_docx_bytes(b"plain text")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("hello.txt", "hi")
    with pytest.raises(ValueError, match=r"word/document.xml is missing"):
        convert_docx_bytes(buffer.getvalue())
    with pytest.raises(TypeError):
        convert_docx_bytes("text")  # type: ignore[arg-type]
    broken = build("", parts={"word/document.xml": f"{HEAD}<w:document {W}><w:body>"})
    with pytest.raises(ValueError, match=r"word/document.xml is not well-formed XML"):
        convert_docx_bytes(broken)
    broken = build(para(run("s", "Preeti")), styles="<w:styles")
    with pytest.raises(ValueError, match=r"word/styles.xml is not well-formed XML"):
        convert_docx_bytes(broken)
    utf16 = build("", parts={"word/document.xml": "<a/>".encode("utf-16")})
    with pytest.raises(ValueError, match="not UTF-8"):
        convert_docx_bytes(utf16)
    target = tmp_path / "dir"
    target.mkdir()
    source = tmp_path / "in.docx"
    source.write_bytes(build(para(run("s", "Preeti"))))
    with pytest.raises(ValueError, match="is a directory"):
        convert_docx(source, target)


def test_a_part_with_another_root_is_copied_untouched() -> None:
    odd = f"{HEAD}<w:settings {W}><w:p><w:r>{PREETI_RPR}<w:t>s</w:t></w:r></w:p></w:settings>"
    source = build(para(run("s", "Preeti")), parts={"word/header9.xml": odd})
    data, report = convert_docx_bytes(source)
    assert part(data, "word/header9.xml") == odd
    assert report.parts == ("word/document.xml",)


# --- optional: does another program open the result? ------------------------------


def test_libreoffice_opens_the_result_and_reads_the_same_text(tmp_path: Path) -> None:
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if office is None:
        pytest.skip("LibreOffice is not installed")
    target = tmp_path / "out.docx"
    target.write_bytes(convert_docx_bytes(build(MIXED_BODY, parts=MIXED_PARTS))[0])
    done = subprocess.run(
        [
            office,
            f"-env:UserInstallation=file://{tmp_path / 'profile'}",
            "--headless",
            "--convert-to",
            "txt:Text (encoded):UTF8",
            "--outdir",
            str(tmp_path),
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    text_file = tmp_path / "out.txt"
    if done.returncode != 0 or not text_file.exists():
        pytest.skip(f"LibreOffice could not run here: {done.stderr.strip()[:200]}")
    text = text_file.read_text("utf-8-sig")
    assert "Report 2026: नेपालको राजधानी काठमाडौं हो। (Kathmandu)" in text
    assert "प्रथम शिर्षक" in text and "नाम" in text and "Name" in text


def test_python_docx_opens_the_result(tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    target = tmp_path / "out.docx"
    target.write_bytes(convert_docx_bytes(build(MIXED_BODY, parts=MIXED_PARTS))[0])
    loaded = docx.Document(str(target))
    first = loaded.paragraphs[0].runs
    assert [(r.text, r.font.name, r.bold) for r in first][:2] == [
        ("Report 2026: ", "Calibri", True),
        ("नेपालको राजधानी काठमाडौं हो", "Kalimati", True),
    ]


# --- command line ---------------------------------------------------------------


def cli(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_docx_round_trip_with_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "in.docx"
    body = MIXED_BODY + para(run("¥ s", "Preeti"))
    source.write_bytes(build(body, parts=MIXED_PARTS))
    before = source.read_bytes()
    target = tmp_path / "out.docx"
    argv = ["convert", "preeti", "--docx", str(source), "-o", str(target)]
    code, out, err = cli([*argv, "--report"], capsys)
    assert code == 0 and out == "" and source.read_bytes() == before
    lines = err.splitlines()
    assert lines[0] == f"aksharkit: note: Preeti conversion is {legacy.PREETI_LABEL}"
    assert lines[1] == (
        "aksharkit: warning: 1 character(s) had no agreed Preeti entry and were left "
        "unchanged: ¥ (U+00A5)"
    )
    assert lines[2] == "  word/document.xml, paragraph 5: ¥ (U+00A5)"
    assert lines[3].startswith(
        "aksharkit: docx: 10 run(s) converted and set to Kalimati, 5 run(s) in other fonts "
        "left as they were, 9 paragraph(s) changed, 0 run boundary move(s); parts read: "
        "word/document.xml, word/header1.xml"
    )
    assert lines[4] == "aksharkit: docx: fonts found on text runs: Calibri (5), Preeti (10)"
    assert lines[5].startswith("aksharkit: summary: ") and "1 left unchanged" in lines[5]
    assert runs_of(part(target.read_bytes()))[1] == ("नेपालको राजधानी काठमाडौं हो", "Kalimati")
    code, _, err = cli([*argv, "--quiet"], capsys)
    assert code == 2 and "already exists; use --force" in err
    code, out, _ = cli([*argv, "--quiet", "--force", "--json", "--font", "Mangal"], capsys)
    payload = json.loads(out)
    assert code == 0 and payload["font"] == "Mangal" and payload["runs_converted"] == 10
    assert payload["input"] == str(source) and payload["output"] == str(target)
    assert cli([*argv, "--quiet", "--force", "--fail-on-unmapped"], capsys)[0] == 1


def test_cli_docx_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "in.docx"
    source.write_bytes(build(para(run("x", "Calibri"))))
    base = ["convert", "preeti", "--docx", str(source), "--quiet"]
    code, _, err = cli(base, capsys)
    assert code == 2 and "--docx needs -o FILE" in err
    code, _, err = cli([*base, "-o", str(source)], capsys)
    assert code == 2 and "the output file is the input file" in err
    code, _, err = cli([*base, "-o", str(source), "--force"], capsys)
    assert code == 2 and "the output file is the input file" in err
    code, _, err = cli(
        [*base, "-o", str(tmp_path / "o.docx"), "--to", "preeti", "--source-font", "X"], capsys
    )
    assert code == 2 and "--source-font has no meaning" in err
    code, _, err = cli([*base, "-o", str(tmp_path / "o.docx"), "--markers", "[", "]"], capsys)
    assert code == 2 and "apply to plain text" in err
    old = tmp_path / "old.doc"
    old.write_bytes(b"\xd0\xcf\x11\xe0")
    code, _, err = cli(
        ["convert", "preeti", "--docx", str(old), "-o", str(tmp_path / "o.docx")], capsys
    )
    assert code == 2 and "does not end in .docx" in err
    fake = tmp_path / "fake.docx"
    fake.write_bytes(b"\xd0\xcf\x11\xe0")
    code, _, err = cli(
        ["convert", "preeti", "--docx", str(fake), "-o", str(tmp_path / "o.docx")], capsys
    )
    assert code == 2 and "old .doc file or a password-protected" in err
    assert not (tmp_path / "o.docx").exists()
    code, _, err = cli(
        ["convert", "preeti", "--docx", str(tmp_path / "no.docx"), "-o", "x.docx"], capsys
    )
    assert code == 2 and "no such file" in err
    code, out, err = cli([*base, "-o", str(tmp_path / "o.docx")], capsys)
    assert code == 0 and out == ""
    assert "no run of" in err and "uses the font Preeti" in err and "Calibri (1)" in err


def test_cli_docx_batch_and_source_font(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    first = tmp_path / "a.docx"
    second = tmp_path / "b.docx"
    notes = tmp_path / "n.txt"
    first.write_bytes(build(para(run("gfd", "Preeti"))))
    second.write_bytes(build(para(run("gfd", "Kantipur"))))
    notes.write_bytes(b"g]kfn\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    argv = [
        "convert", "preeti", "-i", str(notes), "--docx", str(first), "--docx", str(second),
        "--out-dir", str(out_dir), "--quiet", "--json", "--source-font", "Kantipur",
        "--source-font", "Preeti",
    ]  # fmt: skip
    code, out, _ = cli(argv, capsys)
    payload = json.loads(out)
    assert code == 0 and [entry["input"] for entry in payload["files"]] == [
        str(notes),
        str(first),
        str(second),
    ]
    assert (out_dir / "n.txt").read_text("utf-8") == "नेपाल\n"
    for name in ("a.docx", "b.docx"):
        assert runs_of(part((out_dir / name).read_bytes())) == [("नाम", "Kalimati")]
