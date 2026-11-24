"""Preeti to Unicode inside Word (.docx) files.

A .docx file is a zip archive of XML parts. This module converts the text
of the runs whose font is Preeti and leaves everything else as it is. It
uses only the standard library (``zipfile`` and the ``expat`` XML parser).

How it stays out of the way of the rest of the document:

* a part is never parsed into a tree and written out again. The parser is
  used only to find where things are; the changes are then made to the
  original bytes. Everything that is not a converted run stays
  byte-for-byte the same;
* only two things are rewritten: the text elements (``w:t``) of a Preeti
  run, and that run's properties (``w:rPr``), where the font is replaced;
* other parts of the archive (images, styles, settings, ...) are copied.

Which runs count as Preeti, what is and is not handled, and what has not
been tested are described in ``docs/preeti.md``. In short: the key table
was tested on real Preeti PDFs, but no real Word file has been converted
with this.
"""

from __future__ import annotations

import io
import os
import re
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from xml.parsers import expat

from .legacy import (
    PREETI_LABEL,
    Keep,
    PreetiEncodeResult,
    PreetiEncodeStats,
    PreetiResult,
    PreetiStats,
    convert_preeti,
    encode_preeti,
)
from .normalize import normalize

__all__ = [
    "DEFAULT_DOCX_FONT",
    "DEFAULT_PREETI_FONT",
    "DocxEncodeReport",
    "DocxLeft",
    "DocxReport",
    "DocxUnmapped",
    "convert_docx",
    "convert_docx_bytes",
    "encode_docx",
    "encode_docx_bytes",
]

#: The font name written on converted runs. The font itself is not part of
#: this package or of the output file; see ``docs/preeti.md``.
DEFAULT_DOCX_FONT = "Kalimati"

_W_NAMESPACES = frozenset(
    {
        "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "http://purl.oclc.org/ooxml/wordprocessingml/main",
    }
)
_A_NAMESPACES = frozenset(
    {
        "http://schemas.openxmlformats.org/drawingml/2006/main",
        "http://purl.oclc.org/ooxml/drawingml/main",
    }
)
_XMLNS = "http://www.w3.org/2000/xmlns/"

# The parts that hold running text, and the root element each must have.
_PART_NAME = re.compile(r"word/(?:document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml")
_PART_ROOTS = frozenset({"document", "hdr", "ftr", "footnotes", "endnotes", "comments"})

# The order the schema wants the children of w:rPr in.
_RPR_ORDER = (
    "rStyle",
    "rFonts",
    "b",
    "bCs",
    "i",
    "iCs",
    "caps",
    "smallCaps",
    "strike",
    "dstrike",
    "outline",
    "shadow",
    "emboss",
    "imprint",
    "noProof",
    "snapToGrid",
    "vanish",
    "webHidden",
    "color",
    "spacing",
    "w",
    "kern",
    "position",
    "sz",
    "szCs",
    "highlight",
    "u",
    "effect",
    "bdr",
    "shd",
    "fitText",
    "vertAlign",
    "rtl",
    "cs",
    "em",
    "lang",
    "eastAsianLayout",
    "specVanish",
    "oMath",
    "rPrChange",
)
_RPR_RANK = {name: rank for rank, name in enumerate(_RPR_ORDER)}

_OLE_MAGIC = b"\xd0\xcf\x11\xe0"
# How many characters may move to the run before, to keep a word whole.
_MOVE_LIMIT = 16


@dataclass(frozen=True)
class DocxUnmapped:
    """A character in a Preeti run that had no agreed table entry."""

    #: The part of the archive, for example ``word/document.xml``.
    part: str
    #: The paragraph in that part, counting from 1 in document order.
    paragraph: int
    char: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "part": self.part,
            "paragraph": self.paragraph,
            "char": self.char,
            "codepoint": f"U+{ord(self.char):04X}",
        }


@dataclass(frozen=True)
class DocxReport:
    """What :func:`convert_docx` did."""

    #: The parts that were read, in archive order.
    parts: tuple[str, ...]
    #: The parts that were changed.
    parts_changed: tuple[str, ...]
    #: Paragraphs holding at least one converted run.
    paragraphs_changed: int
    #: Runs with text whose font was Preeti: converted and given ``font``.
    runs_converted: int
    #: Runs with text in another font: left exactly as they were.
    runs_untouched: int
    #: Runs where only one of the two Latin font slots was Preeti: left alone.
    runs_partial_font: int
    #: Times characters were moved to the run before, to keep a word whole.
    boundary_moves: int
    #: Times a whole stretch had to be put into its first run instead.
    groups_merged: int
    #: Character counts for the converted runs.
    stats: PreetiStats
    #: Every unmapped character, in document order.
    unmapped: tuple[DocxUnmapped, ...]
    #: Font name to number of text runs using it, as resolved.
    fonts_seen: dict[str, int] = field(default_factory=dict)
    #: The font name written on converted runs.
    font: str = DEFAULT_DOCX_FONT
    #: The font names treated as Preeti.
    source_fonts: tuple[str, ...] = ("Preeti",)

    @property
    def complete(self) -> bool:
        """True when every character of every Preeti run had an agreed entry."""
        return not self.unmapped

    @property
    def unmapped_chars(self) -> tuple[str, ...]:
        """The distinct unmapped characters, in order of first appearance."""
        return tuple(dict.fromkeys(item.char for item in self.unmapped))

    def as_dict(self) -> dict[str, Any]:
        """Everything in the report as plain JSON-ready data."""
        counts: dict[str, int] = {}
        for item in self.unmapped:
            counts[item.char] = counts.get(item.char, 0) + 1
        return {
            "direction": "preeti-to-unicode",
            "status": PREETI_LABEL,
            "complete": self.complete,
            "font": self.font,
            "source_fonts": list(self.source_fonts),
            "parts": list(self.parts),
            "parts_changed": list(self.parts_changed),
            "paragraphs_changed": self.paragraphs_changed,
            "runs_converted": self.runs_converted,
            "runs_untouched": self.runs_untouched,
            "runs_partial_font": self.runs_partial_font,
            "boundary_moves": self.boundary_moves,
            "groups_merged": self.groups_merged,
            "fonts_seen": dict(self.fonts_seen),
            "stats": self.stats.as_dict(),
            "unmapped": [item.as_dict() for item in self.unmapped],
            "unmapped_counts": [
                {"char": ch, "codepoint": f"U+{ord(ch):04X}", "count": count}
                for ch, count in counts.items()
            ],
        }


# --- Styles and theme ----------------------------------------------------------

_Props = dict[str, dict[str, str]]


@dataclass
class _Style:
    kind: str
    based_on: str | None
    props: _Props


@dataclass
class _Styles:
    """What styles.xml and the theme say about fonts, bold, italic and size."""

    defaults: _Props = field(default_factory=dict)
    styles: dict[str, _Style] = field(default_factory=dict)
    default_paragraph: str | None = None
    #: Theme font names: ``major``/``minor`` + ``latin``/``cs``/``ea``.
    theme: dict[str, str] = field(default_factory=dict)

    def chain(self, style_id: str | None) -> list[_Props]:
        """The properties of a style and the styles it is based on, nearest first."""
        out: list[_Props] = []
        seen: set[str] = set()
        while style_id and style_id not in seen and style_id in self.styles:
            seen.add(style_id)
            style = self.styles[style_id]
            out.append(style.props)
            style_id = style.based_on
        return out

    def theme_font(self, value: str) -> str | None:
        """Resolve a theme font reference such as ``minorHAnsi``."""
        group = "major" if value.startswith("major") else "minor"
        rest = value[len(group) :].lower()
        script = {"bidi": "cs", "eastasia": "ea"}.get(rest, "latin")
        return self.theme.get(group + script)


def _local(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        uri, _, name = tag[1:].partition("}")
        return uri, name
    return "", tag


def _w_attrs(element: ElementTree.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, value in element.attrib.items():
        uri, local = _local(name)
        if uri in _W_NAMESPACES:
            out[local] = value
    return out


def _props_of(rpr: ElementTree.Element | None) -> _Props:
    props: _Props = {}
    if rpr is None:
        return props
    for child in rpr:
        uri, local = _local(child.tag)
        if uri in _W_NAMESPACES and local in ("rFonts", "b", "bCs", "i", "iCs", "sz", "szCs"):
            props[local] = _w_attrs(child)
    return props


def _child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    for child in element:
        uri, local = _local(child.tag)
        if uri in _W_NAMESPACES and local == name:
            return child
    return None


def _parse_xml(data: bytes, part: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise ValueError(f"{part} is not well-formed XML: {error}") from error


def _read_styles(styles_xml: bytes | None, theme_xml: bytes | None) -> _Styles:
    out = _Styles()
    if styles_xml is not None:
        root = _parse_xml(styles_xml, "word/styles.xml")
        defaults = _child(root, "docDefaults")
        if defaults is not None:
            rpr_default = _child(defaults, "rPrDefault")
            if rpr_default is not None:
                out.defaults = _props_of(_child(rpr_default, "rPr"))
        for style in root:
            uri, local = _local(style.tag)
            if uri not in _W_NAMESPACES or local != "style":
                continue
            attrs = _w_attrs(style)
            style_id = attrs.get("styleId")
            if not style_id:
                continue
            based = _child(style, "basedOn")
            based_on = _w_attrs(based).get("val") if based is not None else None
            kind = attrs.get("type", "paragraph")
            out.styles[style_id] = _Style(kind, based_on, _props_of(_child(style, "rPr")))
            if kind == "paragraph" and _on(attrs.get("default", "0")):
                out.default_paragraph = style_id
    if theme_xml is not None:
        root = _parse_xml(theme_xml, "word/theme/theme1.xml")
        for element in root.iter():
            uri, local = _local(element.tag)
            if uri not in _A_NAMESPACES or local not in ("majorFont", "minorFont"):
                continue
            group = local[:5]
            for font in element:
                font_uri, font_local = _local(font.tag)
                if font_uri in _A_NAMESPACES and font_local in ("latin", "cs", "ea"):
                    face = font.attrib.get("typeface", "")
                    if face:
                        out.theme[group + font_local] = face
    return out


def _on(value: str | None) -> bool:
    """Read an on/off attribute; a missing value means on."""
    return value is None or value.strip().lower() not in ("0", "false", "off")


# --- Reading a part ------------------------------------------------------------


@dataclass
class _Child:
    """A child element of a run's w:rPr."""

    local: str
    is_w: bool
    start: int
    end: int
    attrs: dict[str, str]


@dataclass
class _Text:
    """One w:t element."""

    start: int
    end: int
    text: str
    new_text: str | None = None


@dataclass
class _Run:
    prefix: str
    #: Just past the run's start tag: where a new w:rPr goes.
    body_start: int
    paragraph: _Paragraph
    rpr_span: tuple[int, int] | None = None
    children: list[_Child] = field(default_factory=list)
    texts: list[_Text] = field(default_factory=list)
    preeti: bool = False

    def direct(self) -> _Props:
        return {child.local: child.attrs for child in self.children if child.is_w}

    def style_id(self) -> str | None:
        for child in self.children:
            if child.is_w and child.local == "rStyle":
                return child.attrs.get("val")
        return None


@dataclass
class _Paragraph:
    index: int
    style_id: str | None = None
    #: Text elements and breaks, in document order. None is a break.
    items: list[tuple[_Run, _Text] | None] = field(default_factory=list)


def _tag_end(data: bytes, start: int) -> int:
    """Return the index just past the ``>`` that closes the tag at ``start``."""
    close = data.find(b">", start)
    if close == -1:
        raise ValueError("an XML tag is not closed")
    head = data[start:close]
    double = head.count(b'"')
    single = head.count(b"'")
    if double % 2 == 0 and single % 2 == 0 and not (double and single):
        return close + 1
    # A ">" inside an attribute value: walk the tag, minding the quotes.
    quote = 0
    i = start
    n = len(data)
    while i < n:
        byte = data[i]
        if quote:
            if byte == quote:
                quote = 0
        elif byte in (0x22, 0x27):
            quote = byte
        elif byte == 0x3E:
            return i + 1
        i += 1
    raise ValueError("an XML tag is not closed")


class _PartReader:
    """Find the paragraphs, runs and text elements of one part, with offsets."""

    def __init__(self, data: bytes, part: str) -> None:
        self.data = data
        self.part = part
        self.root: tuple[str, str] | None = None
        self.paragraphs: list[_Paragraph] = []
        self.runs: list[_Run] = []
        # (namespace, local name, start offset, end offset when it is an
        # empty element such as <w:b/>, else -1) of every open element.
        self._stack: list[tuple[str, str, int, int]] = []
        self._scopes: list[dict[str, str]] = [{"xml": "http://www.w3.org/XML/1998/namespace"}]
        self._open_paragraphs: list[tuple[_Paragraph, int]] = []
        self._open_runs: list[tuple[_Run, int]] = []
        self._loose = _Paragraph(0)
        self._text: list[str] | None = None
        self._parser = expat.ParserCreate()
        self._parser.buffer_text = True
        self._parser.StartElementHandler = self._start
        self._parser.EndElementHandler = self._end
        self._parser.CharacterDataHandler = self._chars

    def read(self) -> None:
        try:
            self._parser.Parse(self.data, True)
        except expat.ExpatError as error:
            raise ValueError(f"{self.part} is not well-formed XML: {error}") from error

    def _resolve(
        self, qname: str, scope: dict[str, str], attribute: bool = False
    ) -> tuple[str, str]:
        prefix, colon, local = qname.partition(":")
        if not colon:
            return ("" if attribute else scope.get("", "")), qname
        return scope.get(prefix, ""), local

    def _start(self, qname: str, attrs: dict[str, str]) -> None:
        offset = self._parser.CurrentByteIndex
        scope = self._scopes[-1]
        declared = {
            (name[6:] if name.startswith("xmlns:") else ""): value
            for name, value in attrs.items()
            if name == "xmlns" or name.startswith("xmlns:")
        }
        if declared:
            scope = {**scope, **declared}
        self._scopes.append(scope)
        uri, local = self._resolve(qname, scope)
        is_w = uri in _W_NAMESPACES
        depth = len(self._stack)
        tag_end = _tag_end(self.data, offset)
        empty = self.data[tag_end - 2 : tag_end - 1] == b"/"
        self._stack.append((uri, local, offset, tag_end if empty else -1))
        if self.root is None:
            self.root = (uri, local)
        run, run_depth = self._open_runs[-1] if self._open_runs else (None, -1)
        if is_w and local == "p":
            paragraph = _Paragraph(len(self.paragraphs) + 1)
            self.paragraphs.append(paragraph)
            self._open_paragraphs.append((paragraph, depth))
            return
        if is_w and local == "r":
            paragraph = self._open_paragraphs[-1][0] if self._open_paragraphs else self._loose
            new = _Run(qname.partition(":")[0] if ":" in qname else "", 0, paragraph)
            new.body_start = tag_end
            self._open_runs.append((new, depth))
            self.runs.append(new)
            return
        if run is not None and depth == run_depth + 1:
            if is_w and local == "rPr":
                return
            if is_w and local == "t":
                self._text = []
                return
            # A tab, a break, a picture, a field mark: the words stop here.
            run.paragraph.items.append(None)
            return
        if run is not None and depth == run_depth + 2:
            parent_uri, parent_local, _, _ = self._stack[-2]
            if parent_uri in _W_NAMESPACES and parent_local == "rPr":
                w_attrs: dict[str, str] = {}
                for name, value in attrs.items():
                    attr_uri, attr_local = self._resolve(name, scope, attribute=True)
                    if attr_uri in _W_NAMESPACES:
                        w_attrs[attr_local] = value
                run.children.append(_Child(local, is_w, offset, -1, w_attrs))
            return
        if is_w and local == "pStyle" and self._open_paragraphs and len(self._stack) >= 3:
            paragraph, paragraph_depth = self._open_paragraphs[-1]
            parent_uri, parent_local, _, _ = self._stack[-2]
            if (
                depth == paragraph_depth + 2
                and parent_uri in _W_NAMESPACES
                and parent_local == "pPr"
            ):
                for name, value in attrs.items():
                    attr_uri, attr_local = self._resolve(name, scope, attribute=True)
                    if attr_uri in _W_NAMESPACES and attr_local == "val":
                        paragraph.style_id = value

    def _chars(self, data: str) -> None:
        if self._text is not None:
            self._text.append(data)

    def _end(self, qname: str) -> None:
        offset = self._parser.CurrentByteIndex
        uri, local, start, empty_end = self._stack.pop()
        self._scopes.pop()
        depth = len(self._stack)
        is_w = uri in _W_NAMESPACES
        # For an empty element the parser reports the offset after the tag,
        # so its end was worked out when it opened.
        end = empty_end if empty_end != -1 else _tag_end(self.data, offset)
        if (
            self._open_paragraphs
            and self._open_paragraphs[-1][1] == depth
            and is_w
            and local == "p"
        ):
            self._open_paragraphs.pop()
            return
        if not self._open_runs:
            return
        run, run_depth = self._open_runs[-1]
        if depth == run_depth and is_w and local == "r":
            self._open_runs.pop()
            return
        if depth == run_depth + 1 and is_w:
            if local == "rPr":
                run.rpr_span = (start, end)
            elif local == "t" and self._text is not None:
                text = _Text(start, end, "".join(self._text))
                self._text = None
                run.texts.append(text)
                run.paragraph.items.append((run, text))
        elif (
            depth == run_depth + 2
            and run.children
            and run.children[-1].end == -1
            and run.children[-1].start == start
        ):
            run.children[-1].end = end


# --- Deciding and converting ---------------------------------------------------


def _lookup(layers: Iterable[_Props], name: str) -> dict[str, str] | None:
    for props in layers:
        if name in props:
            return props[name]
    return None


def _layers(run: _Run, styles: _Styles) -> list[_Props]:
    """Where a run's properties come from, nearest first.

    The run itself, its character style and what that is based on, the
    paragraph's style (or the default paragraph style) and what that is
    based on, then the document defaults.
    """
    layers = [run.direct()]
    layers.extend(styles.chain(run.style_id()))
    layers.extend(styles.chain(run.paragraph.style_id or styles.default_paragraph))
    layers.append(styles.defaults)
    return layers


def _font(layers: list[_Props], slot: str, styles: _Styles) -> str | None:
    """The font of one slot (``ascii`` or ``hAnsi``) after inheritance."""
    for props in layers:
        fonts = props.get("rFonts")
        if not fonts:
            continue
        theme = fonts.get(slot + "Theme")
        if theme:
            return styles.theme_font(theme)
        if slot in fonts:
            return fonts[slot]
    return None


def _same(name: str | None, wanted: frozenset[str]) -> bool:
    return name is not None and name.strip().casefold() in wanted


def _escape_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    return _escape_text(text).replace('"', "&quot;")


def _element(prefix: str, local: str, attrs: dict[str, str]) -> bytes:
    lead = f"{prefix}:" if prefix else ""
    parts = [f"<{lead}{local}"]
    parts.extend(f' {lead}{name}="{_escape_attr(value)}"' for name, value in attrs.items())
    parts.append("/>")
    return "".join(parts).encode("utf-8")


def _new_rpr(run: _Run, styles: _Styles, font: str, data: bytes) -> bytes:
    """Build the run's new w:rPr: same children, new font."""
    layers = _layers(run, styles)
    replace: dict[str, bytes] = {}
    old_fonts = run.direct().get("rFonts", {})
    fonts = {"ascii": font, "hAnsi": font, "cs": font}
    for name, value in old_fonts.items():
        if name in ("eastAsia", "eastAsiaTheme"):
            fonts[name] = value
    replace["rFonts"] = _element(run.prefix, "rFonts", fonts)
    # Devanagari is "complex script" text to a word processor, which reads
    # bold, italic and size for it from separate properties. Copy the
    # ordinary ones across where they differ, so the text keeps its look.
    for plain, complex_name in (("b", "bCs"), ("i", "iCs")):
        latin = _lookup(layers, plain)
        other = _lookup(layers, complex_name)
        wanted = latin is not None and _on(latin.get("val"))
        current = other is not None and _on(other.get("val"))
        if wanted != current:
            replace[complex_name] = _element(
                run.prefix, complex_name, {} if wanted else {"val": "0"}
            )
    size = (_lookup(layers, "sz") or {}).get("val", "20")
    complex_size = (_lookup(layers, "szCs") or {}).get("val", "20")
    if size != complex_size:
        replace["szCs"] = _element(run.prefix, "szCs", {"val": size})
    kept: list[tuple[int, bytes]] = []
    for child in run.children:
        if child.is_w and child.local in replace:
            continue
        rank = _RPR_RANK.get(child.local, len(_RPR_ORDER)) if child.is_w else len(_RPR_ORDER)
        kept.append((rank, data[child.start : child.end]))
    for local, raw in replace.items():
        rank = _RPR_RANK[local]
        at = len(kept)
        for index, (other_rank, _) in enumerate(kept):
            if other_rank > rank:
                at = index
                break
        kept.insert(at, (rank, raw))
    lead = f"{run.prefix}:" if run.prefix else ""
    body = b"".join(raw for _, raw in kept)
    return f"<{lead}rPr>".encode() + body + f"</{lead}rPr>".encode()


def _new_text(run: _Run, text: str) -> bytes:
    lead = f"{run.prefix}:" if run.prefix else ""
    return f'<{lead}t xml:space="preserve">{_escape_text(text)}</{lead}t>'.encode()


class _Converter:
    """Convert stretches of Preeti text, keeping words whole across runs."""

    def __init__(self, convert: Callable[[str], PreetiResult]) -> None:
        self._convert = convert
        self._cache: dict[str, PreetiResult] = {}
        self.moves = 0
        self.merged = 0

    def result(self, text: str) -> PreetiResult:
        if text not in self._cache:
            self._cache[text] = self._convert(text)
        return self._cache[text]

    def _joined(self, pieces: list[str]) -> str:
        return "".join(self.result(piece).text for piece in pieces)

    def split(self, texts: list[str]) -> list[str]:
        """Re-cut ``texts`` so that converting each piece gives the whole.

        Returns as many pieces as it was given, with the same characters in
        the same order. Converting the pieces one by one and joining the
        results gives exactly what converting the joined text gives. Where
        a letter and its sign sit in different pieces, the fewest leading
        characters are moved to the nearest piece before that has text.
        """
        pieces: list[str] = []
        for text in texts:
            if not pieces:
                pieces.append(text)
                continue
            whole = self.result("".join(pieces) + text).text
            at = len(pieces) - 1
            while at > 0 and not pieces[at]:
                at -= 1
            head = self._joined(pieces[:at])
            for moved in range(min(len(text), _MOVE_LIMIT) + 1):
                last = pieces[at] + text[:moved]
                rest = text[moved:]
                if head + self.result(last).text + self.result(rest).text == whole:
                    if moved:
                        self.moves += 1
                    pieces[at] = last
                    pieces.append(rest)
                    break
            else:
                # No cut works nearby. Keep the text right and give up the
                # run boundaries of this stretch: all of it goes to the
                # first run.
                self.merged += 1
                pieces = ["".join(pieces) + text] + [""] * len(pieces)
        return pieces


@dataclass
class _Tally:
    paragraphs: int = 0
    converted: int = 0
    untouched: int = 0
    partial: int = 0
    stats: PreetiStats = field(default_factory=PreetiStats)
    unmapped: list[DocxUnmapped] = field(default_factory=list)
    fonts: dict[str, int] = field(default_factory=dict)


def _convert_part(
    data: bytes,
    part: str,
    styles: _Styles,
    wanted: frozenset[str],
    font: str,
    converter: _Converter,
    tally: _Tally,
) -> bytes | None:
    """Convert one part. Returns None when the part is not a text part."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        raise ValueError(f"{part} is not UTF-8; only UTF-8 parts are supported")
    reader = _PartReader(data, part)
    reader.read()
    if reader.root is None or reader.root[0] not in _W_NAMESPACES:
        return None
    if reader.root[1] not in _PART_ROOTS:
        return None
    for run in reader.runs:
        if not run.texts:
            continue
        layers = _layers(run, styles)
        ascii_font = _font(layers, "ascii", styles)
        ansi_font = _font(layers, "hAnsi", styles)
        name = ascii_font or ansi_font or "(not stated)"
        tally.fonts[name] = tally.fonts.get(name, 0) + 1
        ascii_is = _same(ascii_font, wanted)
        ansi_is = _same(ansi_font, wanted)
        run.preeti = ascii_is and ansi_is
        if run.preeti:
            tally.converted += 1
        elif ascii_is or ansi_is:
            tally.partial += 1
        else:
            tally.untouched += 1
    edits: list[tuple[int, int, bytes]] = []
    for paragraph in [*reader.paragraphs, reader._loose]:
        group: list[_Text] = []
        groups: list[list[_Text]] = []
        for item in paragraph.items:
            if item is not None and item[0].preeti:
                group.append(item[1])
                continue
            if group:
                groups.append(group)
                group = []
        if group:
            groups.append(group)
        if not groups:
            continue
        tally.paragraphs += 1
        for texts in groups:
            pieces = converter.split([text.text for text in texts])
            for text, piece in zip(texts, pieces, strict=True):
                result = converter.result(piece)
                text.new_text = result.text
                tally.stats = tally.stats + result.stats
                tally.unmapped.extend(
                    DocxUnmapped(part, paragraph.index, item.char) for item in result.unmapped
                )
    for run in reader.runs:
        if not run.preeti:
            continue
        rpr = _new_rpr(run, styles, font, data)
        if run.rpr_span is None:
            edits.append((run.body_start, run.body_start, rpr))
        else:
            edits.append((run.rpr_span[0], run.rpr_span[1], rpr))
        for text in run.texts:
            new = text.text if text.new_text is None else text.new_text
            edits.append((text.start, text.end, _new_text(run, new)))
    if not edits:
        return data
    edits.sort(key=lambda edit: (edit[0], edit[1]))
    out: list[bytes] = []
    position = 0
    for start, end, replacement in edits:
        if start < position:
            raise ValueError(f"{part}: overlapping runs; the part was not changed")
        out.append(data[position:start])
        out.append(replacement)
        position = end
    out.append(data[position:])
    return b"".join(out)


def _check_font_name(font: str) -> str:
    if not isinstance(font, str) or not font.strip():
        raise ValueError("font must be a non-empty font name")
    if any(ord(ch) < 32 for ch in font):
        raise ValueError("font must not contain control characters")
    return font.strip()


def _open_docx(data: bytes) -> zipfile.ZipFile:
    """Open the bytes of a .docx file, or say plainly why they are not one."""
    if data[:4] == _OLE_MAGIC:
        raise ValueError(
            "this is an old .doc file or a password-protected file, not a .docx; "
            "open it in a word processor and save it as .docx first"
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError("this is not a .docx file (it is not a zip archive)") from error
    names = archive.namelist()
    if "word/document.xml" not in names or "[Content_Types].xml" not in names:
        archive.close()
        raise ValueError("this is not a Word .docx file (word/document.xml is missing)")
    return archive


def _check_paths(
    src: str | os.PathLike[str], dst: str | os.PathLike[str], overwrite: bool
) -> tuple[Path, Path]:
    """Check an input and an output path; the input is never the output."""
    source = Path(src)
    target = Path(dst)
    if not source.is_file():
        raise ValueError(f"no such file: {source}")
    if target.exists():
        if target.is_dir():
            raise ValueError(f"the output {target} is a directory")
        if os.path.samefile(source, target):
            raise ValueError("the output file is the input file; choose another name")
        if not overwrite:
            raise ValueError(f"the output file {target} already exists")
    elif source.resolve() == target.resolve():
        raise ValueError("the output file is the input file; choose another name")
    return source, target


def convert_docx_bytes(
    data: bytes,
    *,
    font: str = DEFAULT_DOCX_FONT,
    source_fonts: Iterable[str] = ("Preeti",),
    include_unconfirmed: bool = False,
    strict: bool = False,
    keep_links: bool = False,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
) -> tuple[bytes, DocxReport]:
    """Convert the Preeti runs of a .docx file held in memory.

    Returns the new file's bytes and a :class:`DocxReport`. See
    :func:`convert_docx` for what is converted.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be the bytes of a .docx file")
    data = bytes(data)
    font = _check_font_name(font)
    if isinstance(source_fonts, str):
        source_fonts = (source_fonts,)
    sources = tuple(_check_font_name(name) for name in source_fonts)
    if not sources:
        raise ValueError("source_fonts must name at least one font")
    wanted = frozenset(name.casefold() for name in sources)
    if font.casefold() in wanted:
        raise ValueError("font must differ from the source fonts")
    archive = _open_docx(data)
    with archive:
        names = archive.namelist()
        styles = _read_styles(
            archive.read("word/styles.xml") if "word/styles.xml" in names else None,
            archive.read("word/theme/theme1.xml") if "word/theme/theme1.xml" in names else None,
        )

        def convert(text: str) -> PreetiResult:
            return convert_preeti(
                text,
                include_unconfirmed=include_unconfirmed,
                strict=strict,
                keep_links=keep_links,
                keep=keep,
                keep_words=keep_words,
            )

        converter = _Converter(convert)
        tally = _Tally()
        parts: list[str] = []
        changed: list[str] = []
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as out:
            for info in archive.infolist():
                content = archive.read(info)
                if _PART_NAME.fullmatch(info.filename):
                    new = _convert_part(
                        content, info.filename, styles, wanted, font, converter, tally
                    )
                    if new is not None:
                        parts.append(info.filename)
                        if new != content:
                            changed.append(info.filename)
                            content = new
                copy = zipfile.ZipInfo(info.filename, info.date_time)
                copy.compress_type = info.compress_type
                copy.external_attr = info.external_attr
                copy.create_system = info.create_system
                out.writestr(copy, content)
    report = DocxReport(
        parts=tuple(parts),
        parts_changed=tuple(changed),
        paragraphs_changed=tally.paragraphs,
        runs_converted=tally.converted,
        runs_untouched=tally.untouched,
        runs_partial_font=tally.partial,
        boundary_moves=converter.moves,
        groups_merged=converter.merged,
        stats=tally.stats,
        unmapped=tuple(tally.unmapped),
        fonts_seen=dict(sorted(tally.fonts.items())),
        font=font,
        source_fonts=sources,
    )
    return buffer.getvalue(), report


def convert_docx(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
    *,
    overwrite: bool = False,
    font: str = DEFAULT_DOCX_FONT,
    source_fonts: Iterable[str] = ("Preeti",),
    include_unconfirmed: bool = False,
    strict: bool = False,
    keep_links: bool = False,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
) -> DocxReport:
    """Convert the Preeti runs of the Word file ``src`` and write ``dst``.

    The key table was checked against real Preeti PDFs, but this function
    has only seen .docx files built by the tests, and the result has not
    been opened in Microsoft Word.

    Only runs whose font is one of ``source_fonts`` (``Preeti`` unless you
    say otherwise; names are compared without regard to case) are
    converted. Their font is set to ``font``. Runs in any other font, and
    everything else in the file, are left as they are. The font of a run
    is read from the run itself, then its character style, then its
    paragraph's style, then the document defaults.

    ``src`` is never written to: ``dst`` must be a different file, and an
    existing ``dst`` is replaced only with ``overwrite=True``.

    Web and e-mail addresses are *not* protected here unless you pass
    ``keep_links=True``: in a Word file the font already says what is
    Preeti. ``keep`` and ``keep_words`` work as in
    :func:`aksharkit.convert_preeti`.
    """
    source, target = _check_paths(src, dst, overwrite)
    data, report = convert_docx_bytes(
        source.read_bytes(),
        font=font,
        source_fonts=source_fonts,
        include_unconfirmed=include_unconfirmed,
        strict=strict,
        keep_links=keep_links,
        keep=keep,
        keep_words=keep_words,
    )
    target.write_bytes(data)
    return report


# --- Unicode to Preeti ---------------------------------------------------------

#: The font name written on runs turned into Preeti key codes. The font is
#: not part of this package or of the output file.
DEFAULT_PREETI_FONT = "Preeti"


@dataclass(frozen=True)
class DocxLeft:
    """A stretch of Nepali text that :func:`encode_docx` left in Unicode."""

    #: The part of the archive, for example ``word/document.xml``.
    part: str
    #: The paragraph in that part, counting from 1 in document order.
    paragraph: int
    text: str
    #: ``"no key"`` (a character in it has no Preeti key) or ``"does not
    #: read back"`` (its keys would not convert back to the same text).
    reason: str
    #: The characters with no key, when that is the reason.
    chars: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "part": self.part,
            "paragraph": self.paragraph,
            "text": self.text,
            "reason": self.reason,
            "chars": [{"char": ch, "codepoint": f"U+{ord(ch):04X}"} for ch in self.chars],
        }


@dataclass(frozen=True)
class DocxEncodeReport:
    """What :func:`encode_docx` did."""

    #: The parts that were read, in archive order.
    parts: tuple[str, ...]
    #: The parts that were changed.
    parts_changed: tuple[str, ...]
    #: Paragraphs holding at least one stretch written as keys.
    paragraphs_changed: int
    #: Runs written wholly as keys and given ``font``.
    runs_converted: int
    #: Runs cut into pieces: keys in ``font``, the rest as it was.
    runs_split: int
    #: Runs with text that were left exactly as they were.
    runs_untouched: int
    #: Words that crossed a run boundary and were put into their first run.
    boundary_moves: int
    #: Word and character counts.
    stats: PreetiEncodeStats
    #: Every stretch of Nepali text left in Unicode, in document order.
    left: tuple[DocxLeft, ...]
    #: The font name written on the key-code runs.
    font: str = DEFAULT_PREETI_FONT

    @property
    def complete(self) -> bool:
        """True when every Nepali word was written as keys."""
        return not self.left

    def as_dict(self) -> dict[str, Any]:
        """Everything in the report as plain JSON-ready data."""
        return {
            "direction": "unicode-to-preeti",
            "status": PREETI_LABEL,
            "complete": self.complete,
            "font": self.font,
            "parts": list(self.parts),
            "parts_changed": list(self.parts_changed),
            "paragraphs_changed": self.paragraphs_changed,
            "runs_converted": self.runs_converted,
            "runs_split": self.runs_split,
            "runs_untouched": self.runs_untouched,
            "boundary_moves": self.boundary_moves,
            "stats": self.stats.as_dict(),
            "left": [item.as_dict() for item in self.left],
        }


@dataclass
class _EncodeTally:
    paragraphs: int = 0
    converted: int = 0
    split: int = 0
    untouched: int = 0
    moves: int = 0
    stats: PreetiEncodeStats = field(default_factory=PreetiEncodeStats)
    left: list[DocxLeft] = field(default_factory=list)


def _preeti_rpr(run: _Run, styles: _Styles, font: str, data: bytes) -> bytes:
    """Build the w:rPr for key codes: same children, the Preeti font name.

    A word processor reads bold, italic and size for Devanagari from the
    "complex script" properties and for key codes (plain Latin characters)
    from the ordinary ones. They are copied across where they differ, so the
    text keeps its look.
    """
    layers = _layers(run, styles)
    replace: dict[str, bytes] = {}
    fonts = {"ascii": font, "hAnsi": font, "cs": font}
    for name, value in run.direct().get("rFonts", {}).items():
        if name in ("eastAsia", "eastAsiaTheme"):
            fonts[name] = value
    replace["rFonts"] = _element(run.prefix, "rFonts", fonts)
    for plain, complex_name in (("b", "bCs"), ("i", "iCs")):
        latin = _lookup(layers, plain)
        other = _lookup(layers, complex_name)
        wanted = other is not None and _on(other.get("val"))
        current = latin is not None and _on(latin.get("val"))
        if wanted != current:
            replace[plain] = _element(run.prefix, plain, {} if wanted else {"val": "0"})
    size = (_lookup(layers, "sz") or {}).get("val", "20")
    complex_size = (_lookup(layers, "szCs") or {}).get("val", "20")
    if size != complex_size:
        replace["sz"] = _element(run.prefix, "sz", {"val": complex_size})
    kept: list[tuple[int, bytes]] = []
    for child in run.children:
        if child.is_w and child.local in replace:
            continue
        # These say "treat the text as complex script": not so for key codes.
        if child.is_w and child.local in ("cs", "rtl"):
            continue
        rank = _RPR_RANK.get(child.local, len(_RPR_ORDER)) if child.is_w else len(_RPR_ORDER)
        kept.append((rank, data[child.start : child.end]))
    for local, raw in replace.items():
        rank = _RPR_RANK[local]
        at = len(kept)
        for index, (other_rank, _) in enumerate(kept):
            if other_rank > rank:
                at = index
                break
        kept.insert(at, (rank, raw))
    lead = f"{run.prefix}:" if run.prefix else ""
    body = b"".join(raw for _, raw in kept)
    return f"<{lead}rPr>".encode() + body + f"</{lead}rPr>".encode()


_Pieces = list[tuple[str, bool]]


def _cut_group(texts: list[str], result: PreetiEncodeResult, tally: _EncodeTally) -> list[_Pieces]:
    """Share the segments of ``result`` out over the runs they came from.

    Returns, for every text, its pieces as ``(text, is keys)``. A stretch of
    keys that crosses a run boundary goes whole into the run it starts in.
    White space goes with the piece before it.
    """
    bounds = [0]
    for text in texts:
        bounds.append(bounds[-1] + len(text))
    raw: list[list[tuple[str, str]]] = [[] for _ in texts]
    index = 0
    for segment in result.segments:
        while index + 1 < len(texts) and segment.start >= bounds[index + 1]:
            index += 1
        if segment.kind == "keys":
            if segment.end > bounds[index + 1]:
                tally.moves += 1
            raw[index].append((segment.text, "keys"))
            continue
        at = index
        start = segment.start
        while start < segment.end:
            while start >= bounds[at + 1]:
                at += 1
            end = min(segment.end, bounds[at + 1])
            piece = segment.text[start - segment.start : end - segment.start]
            raw[at].append((piece, "space" if segment.kind == "space" else "kept"))
            start = end
    out: list[_Pieces] = []
    for items in raw:
        kinds = [kind for _, kind in items]
        for position, kind in enumerate(kinds):
            if kind != "space":
                continue
            before = next((k for k in reversed(kinds[:position]) if k != "space"), None)
            after = next((k for k in kinds[position + 1 :] if k != "space"), None)
            kinds[position] = before or after or "kept"
        pieces: _Pieces = []
        for (text, _), kind in zip(items, kinds, strict=True):
            keys = kind == "keys"
            if pieces and pieces[-1][1] == keys:
                pieces[-1] = (pieces[-1][0] + text, keys)
            else:
                pieces.append((text, keys))
        out.append(pieces)
    return out


def _encode_part(
    data: bytes,
    part: str,
    styles: _Styles,
    font: str,
    encode: Callable[[str], PreetiEncodeResult],
    tally: _EncodeTally,
) -> bytes | None:
    """Write the Devanagari of one part as keys. None when it is not a text part."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        raise ValueError(f"{part} is not UTF-8; only UTF-8 parts are supported")
    reader = _PartReader(data, part)
    reader.read()
    if reader.root is None or reader.root[0] not in _W_NAMESPACES:
        return None
    if reader.root[1] not in _PART_ROOTS:
        return None
    pieces_of: dict[int, _Pieces] = {}
    for paragraph in [*reader.paragraphs, reader._loose]:
        groups: list[list[_Text]] = [[]]
        for item in paragraph.items:
            if item is None:
                groups.append([])
            else:
                groups[-1].append(item[1])
        changed = False
        for group in groups:
            texts = [normalize(text.text, whitespace=False, danda=False) for text in group]
            joined = "".join(texts)
            if not any("\u0900" <= ch <= "\u097f" for ch in joined):
                continue
            result = encode(joined)
            tally.stats = tally.stats + result.stats
            holes = {item.offset: item.char for item in result.unmapped}
            for segment in result.segments:
                if segment.kind == "unmapped":
                    chars = tuple(
                        dict.fromkeys(
                            holes[at] for at in range(segment.start, segment.end) if at in holes
                        )
                    )
                    tally.left.append(
                        DocxLeft(part, paragraph.index, segment.text, "no key", chars)
                    )
                elif segment.kind == "skipped":
                    tally.left.append(
                        DocxLeft(part, paragraph.index, segment.text, "does not read back")
                    )
            cut_group = _cut_group(texts, result, tally)
            if not any(keys for pieces in cut_group for _, keys in pieces):
                continue
            changed = True
            for text, pieces in zip(group, cut_group, strict=True):
                pieces_of[id(text)] = pieces
        tally.paragraphs += changed
    edits: list[tuple[int, int, bytes]] = []
    for run in reader.runs:
        if not run.texts:
            continue
        cut = [pieces_of.get(id(text)) for text in run.texts]
        if not any(keys for chosen in cut for _, keys in chosen or ()):
            # Nothing here became keys. A run whose text went into the run
            # before it, to keep a word whole, is left empty.
            for text, chosen in zip(run.texts, cut, strict=True):
                if chosen is not None and not chosen and text.text:
                    edits.append((text.start, text.end, _new_text(run, "")))
            tally.untouched += 1
            continue
        lead = f"{run.prefix}:" if run.prefix else ""
        rpr = _preeti_rpr(run, styles, font, data)
        whole = all(chosen is not None and all(keys for _, keys in chosen) for chosen in cut)
        if whole:
            tally.converted += 1
            if run.rpr_span is None:
                edits.append((run.body_start, run.body_start, rpr))
            else:
                edits.append((run.rpr_span[0], run.rpr_span[1], rpr))
            for text, chosen in zip(run.texts, cut, strict=True):
                piece = chosen[0][0] if chosen else ""
                edits.append((text.start, text.end, _new_text(run, piece)))
            continue
        # A mixed run: each text element is closed out of the run and put
        # back as runs of its own, the keys in the new font and the rest
        # with the properties it had. The run is then opened again for
        # whatever follows (a tab, a break, more text).
        tally.split += 1
        old = b"" if run.rpr_span is None else data[run.rpr_span[0] : run.rpr_span[1]]
        open_run = f"<{lead}r>".encode()
        close_run = f"</{lead}r>".encode()
        for text, chosen in zip(run.texts, cut, strict=True):
            if chosen is None or (chosen and not any(keys for _, keys in chosen)):
                continue
            if not chosen:
                edits.append((text.start, text.end, _new_text(run, "")))
                continue
            parts = [close_run]
            for piece, keys in chosen:
                parts.append(open_run + (rpr if keys else old) + _new_text(run, piece) + close_run)
            parts.append(open_run + old)
            edits.append((text.start, text.end, b"".join(parts)))
    if not edits:
        return data
    edits.sort(key=lambda edit: (edit[0], edit[1]))
    out: list[bytes] = []
    position = 0
    for start, end, replacement in edits:
        if start < position:
            raise ValueError(f"{part}: overlapping runs; the part was not changed")
        out.append(data[position:start])
        out.append(replacement)
        position = end
    out.append(data[position:])
    return b"".join(out)


def encode_docx_bytes(
    data: bytes,
    *,
    font: str = DEFAULT_PREETI_FONT,
    strict: bool = False,
    include_unconfirmed: bool = False,
    digits: str = "keep",
    keep_links: bool = True,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
) -> tuple[bytes, DocxEncodeReport]:
    """Write the Devanagari of a .docx file held in memory as Preeti key codes.

    Returns the new file's bytes and a
    :class:`DocxEncodeReport`. See :func:`encode_docx` for what is changed.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be the bytes of a .docx file")
    data = bytes(data)
    font = _check_font_name(font)
    archive = _open_docx(data)
    with archive:
        names = archive.namelist()
        styles = _read_styles(
            archive.read("word/styles.xml") if "word/styles.xml" in names else None,
            archive.read("word/theme/theme1.xml") if "word/theme/theme1.xml" in names else None,
        )
        cache: dict[str, PreetiEncodeResult] = {}

        def encode(text: str) -> PreetiEncodeResult:
            if text not in cache:
                cache[text] = encode_preeti(
                    text,
                    strict=strict,
                    include_unconfirmed=include_unconfirmed,
                    normalise=False,
                    keep_links=keep_links,
                    keep=keep,
                    keep_words=keep_words,
                    digits=digits,
                    whole_words=True,
                )
            return cache[text]

        tally = _EncodeTally()
        parts: list[str] = []
        changed: list[str] = []
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as out:
            for info in archive.infolist():
                content = archive.read(info)
                if _PART_NAME.fullmatch(info.filename):
                    new = _encode_part(content, info.filename, styles, font, encode, tally)
                    if new is not None:
                        parts.append(info.filename)
                        if new != content:
                            changed.append(info.filename)
                            content = new
                copy = zipfile.ZipInfo(info.filename, info.date_time)
                copy.compress_type = info.compress_type
                copy.external_attr = info.external_attr
                copy.create_system = info.create_system
                out.writestr(copy, content)
    report = DocxEncodeReport(
        parts=tuple(parts),
        parts_changed=tuple(changed),
        paragraphs_changed=tally.paragraphs,
        runs_converted=tally.converted,
        runs_split=tally.split,
        runs_untouched=tally.untouched,
        boundary_moves=tally.moves,
        stats=tally.stats,
        left=tuple(tally.left),
        font=font,
    )
    return buffer.getvalue(), report


def encode_docx(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
    *,
    overwrite: bool = False,
    font: str = DEFAULT_PREETI_FONT,
    strict: bool = False,
    include_unconfirmed: bool = False,
    digits: str = "keep",
    keep_links: bool = True,
    keep: Keep | Iterable[Keep] | None = None,
    keep_words: Iterable[str] | None = None,
) -> DocxEncodeReport:
    """Write the Devanagari text of the Word file ``src`` as Preeti key codes in ``dst``.

    The key table was checked against real Preeti PDFs, but this function
    has only seen .docx files built by the tests, and the result has not
    been opened in Microsoft Word or looked at there in the Preeti font.

    Every stretch of Nepali text that can be written as keys which read
    back exactly is replaced by those keys, in a run whose font is set to
    ``font`` (``Preeti``; only the name is written, no font is added to the
    file). Everything else stays as it was, in the font it had: English
    words, ASCII numbers, web and e-mail addresses, and any Nepali word
    holding a character with no key. A run holding both kinds is cut into
    several runs. The words left in Unicode are listed in ``report.left``.

    Converting the result back with :func:`convert_docx` gives the same
    text, in runs set to that function's font.

    ``digits="devanagari"`` first rewrites ASCII numbers in Devanagari
    digits, as in :func:`aksharkit.encode_preeti`. ``src`` is never written
    to: ``dst`` must be a different file, and an existing ``dst`` is
    replaced only with ``overwrite=True``.
    """
    source, target = _check_paths(src, dst, overwrite)
    data, report = encode_docx_bytes(
        source.read_bytes(),
        font=font,
        strict=strict,
        include_unconfirmed=include_unconfirmed,
        digits=digits,
        keep_links=keep_links,
        keep=keep,
        keep_words=keep_words,
    )
    target.write_bytes(data)
    return report
