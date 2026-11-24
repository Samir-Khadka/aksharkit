"""Command-line interface: ``aksharkit <command> ...``."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__, dates, detect, legacy, legacy_docx
from ._errors import DataNotVerifiedError
from .akshara import akshara_count, akshara_spans, truncate
from .collate import sorted_nepali
from .normalize import normalize
from .numerals import format_number, to_ascii_digits, to_devanagari_digits
from .tokens import sentences, tokenize
from .translit import SCHEMES, to_devanagari, to_roman
from .words import currency_to_words, number_to_words, ordinal_to_words, parse_words

__all__ = ["build_parser", "main"]


def _read(text: str | None) -> str:
    """Return the argument, or standard input when it is missing or ``-``."""
    if text is None or text == "-":
        return sys.stdin.read().rstrip("\n")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aksharkit",
        description="Nepali text tools. Pass '-' or omit TEXT to read standard input.",
    )
    parser.add_argument("--version", action="version", version=f"aksharkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p = sub.add_parser("normalize", help="canonical Unicode form")
    p.add_argument("text", nargs="?")
    p.add_argument("--joiners", choices=("safe", "strip", "keep"), default="safe")
    p.add_argument("--no-danda", action="store_true", help="leave | and ।। as they are")

    p = sub.add_parser("digits", help="convert digits between Devanagari and ASCII")
    p.add_argument("text", nargs="?")
    p.add_argument("--to", choices=("devanagari", "ascii"), default="devanagari")

    p = sub.add_parser("format", help="group digits the Nepali way (12,34,567)")
    p.add_argument("number", nargs="?")
    p.add_argument("--devanagari", action="store_true")

    p = sub.add_parser("words", help="spell a number in Nepali words")
    p.add_argument("number", nargs="?")
    p.add_argument("--currency", action="store_true", help="rupees and paisa")
    p.add_argument("--only", action="store_true", help="append मात्र (with --currency)")
    p.add_argument("--ordinal", action="store_true", help="first, second, ... (1 to 100)")

    p = sub.add_parser("number", help="read a number written in Nepali words")
    p.add_argument("text", nargs="?")
    p.add_argument("--devanagari", action="store_true", help="print Nepali digits")
    p.add_argument("--group", action="store_true", help="group digits the Nepali way")

    p = sub.add_parser(
        "detect",
        help="which script the text is in (by Unicode ranges; this is not language detection)",
    )
    p.add_argument("text", nargs="?")
    p.add_argument("--tokens", action="store_true", help="one token and its script per line")
    p.add_argument("--json", action="store_true", help="print everything as JSON")

    p = sub.add_parser("tokenize", help="split into words, or sentences with --sentences")
    p.add_argument("text", nargs="?")
    p.add_argument("--sentences", action="store_true")
    p.add_argument("--json", action="store_true", help="print a JSON array")

    p = sub.add_parser(
        "aksharas",
        help="split into aksharas (written syllables), one per line",
    )
    p.add_argument("text", nargs="?")
    p.add_argument("--count", action="store_true", help="print the number of aksharas")
    p.add_argument("--truncate", type=int, metavar="N", help="keep the first N aksharas")
    p.add_argument("--suffix", default="", help="text to add after a cut (with --truncate)")
    p.add_argument("--sep", metavar="TEXT", help="join with TEXT instead of one per line")
    p.add_argument("--json", action="store_true", help="print text and offsets as JSON")

    p = sub.add_parser(
        "sort",
        help="sort lines in Nepali alphabetical order (see docs/sorting.md)",
    )
    p.add_argument("text", nargs="?", help="lines to sort; '-' reads standard input")
    p.add_argument("--reverse", action="store_true")
    p.add_argument("--unique", action="store_true", help="drop repeated lines")
    p.add_argument(
        "--conjuncts-under-first",
        action="store_true",
        help="file क्ष, त्र, ज्ञ under क, त, ज instead of after ह",
    )

    p = sub.add_parser(
        "convert",
        help="Preeti legacy-font text or Word files to Unicode and back (tested on real documents)",
        description=(
            "Convert text typed in the Preeti font to Unicode, or Unicode back to Preeti "
            "keys. Status: "
            + legacy.PREETI_LABEL
            + ". Characters with no agreed entry are left unchanged and named on "
            "standard error; the exit code stays 0 unless --fail-on-unmapped is given. "
            "Use - for TEXT to read standard input. Web and "
            "e-mail addresses in plain text are left alone. An input file is never "
            "written to."
        ),
    )
    p.add_argument("font", choices=legacy.SUPPORTED_FONTS)
    p.add_argument("text", nargs="?")
    p.add_argument(
        "-i",
        "--input",
        action="append",
        metavar="FILE",
        help="read a plain-text file (- for standard input); repeat with --out-dir for several",
    )
    p.add_argument(
        "--docx",
        action="append",
        metavar="FILE",
        help="convert the Preeti runs of a Word .docx file (with --to preeti: write its "
        "Devanagari text as Preeti keys); needs -o or --out-dir",
    )
    p.add_argument("-o", "--output", metavar="FILE", help="write the result to FILE")
    p.add_argument(
        "--out-dir", metavar="DIR", help="write each input to DIR under its own file name"
    )
    p.add_argument("--force", action="store_true", help="replace an output file that exists")
    p.add_argument(
        "--encoding",
        default="utf-8",
        help="encoding of -i files (default utf-8, a byte-order mark is accepted); "
        "old Preeti text files are often cp1252",
    )
    p.add_argument(
        "--to",
        choices=("unicode", "preeti"),
        default="unicode",
        help="direction: Preeti to Unicode (default) or Unicode to Preeti keys",
    )
    p.add_argument(
        "--keep",
        action="append",
        metavar="REGEX",
        help="leave every match of this regular expression unconverted (repeatable)",
    )
    p.add_argument(
        "--keep-word",
        action="append",
        metavar="WORD",
        help="leave this word unconverted where it stands on its own (repeatable)",
    )
    p.add_argument(
        "--markers",
        nargs=2,
        metavar=("OPEN", "CLOSE"),
        help="leave text between OPEN and CLOSE unconverted and remove the markers",
    )
    p.add_argument(
        "--no-keep-links",
        action="store_true",
        help="convert web and e-mail addresses too (plain text only)",
    )
    p.add_argument(
        "--font",
        dest="docx_font",
        default=None,
        metavar="NAME",
        help="font name to put on converted .docx runs "
        f"(default {legacy_docx.DEFAULT_DOCX_FONT}, or {legacy_docx.DEFAULT_PREETI_FONT} "
        "with --to preeti; the font is not supplied)",
    )
    p.add_argument(
        "--digits",
        choices=legacy.DIGIT_MODES,
        default="keep",
        help="with --to preeti: keep ASCII digits as they are (default), or first rewrite "
        "ASCII numbers on Nepali lines in Devanagari digits, which have keys",
    )
    p.add_argument(
        "--mark-kept",
        nargs=2,
        metavar=("OPEN", "CLOSE"),
        help="with --to preeti on plain text: put OPEN and CLOSE round everything left as "
        "it was, so that converting back with --markers OPEN CLOSE gives the same text",
    )
    p.add_argument(
        "--source-font",
        action="append",
        metavar="NAME",
        help="font name to treat as Preeti in a .docx (default Preeti; repeatable)",
    )
    p.add_argument(
        "--report",
        action="store_true",
        help="list every unmapped character with its line and column, and a summary, "
        "on standard error",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="print a JSON report on standard output (it holds the text unless -o is used)",
    )
    p.add_argument(
        "--fail-on-unmapped",
        action="store_true",
        help="exit with status 1 when any character was left unconverted",
    )
    p.add_argument(
        "--include-unconfirmed",
        action="store_true",
        help="also use entries that only one table family has (both directions)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="leave out entries where two families agree but another table differs",
    )
    p.add_argument("--quiet", action="store_true", help="do not print the status notice")

    p = sub.add_parser(
        "translit",
        help="Devanagari to Roman letters and back (iast is exact, simple is approximate)",
    )
    p.add_argument("text", nargs="?")
    p.add_argument("--to", choices=("roman", "devanagari"), default="roman")
    p.add_argument("--scheme", choices=SCHEMES, default="iast")
    p.add_argument("--keep-digits", action="store_true", help="leave digits as they are")

    p = sub.add_parser(
        "date",
        help="convert a date between AD and BS (default: AD to BS; no DATE means today)",
    )
    p.add_argument(
        "date",
        nargs="?",
        help="YYYY-MM-DD ('-' reads standard input); a BS date may use a month name",
    )
    p.add_argument("--to", choices=("bs", "ad"), default="bs", help="target calendar")
    p.add_argument("--style", choices=("iso", "long", "full"), default="iso")
    p.add_argument(
        "--pattern",
        metavar="PATTERN",
        help="format a BS result with tokens: %%Y %%y %%m %%-m %%B %%d %%-d %%A %%a %%%%",
    )
    p.add_argument("--devanagari", action="store_true", help="Nepali digits and names")
    p.add_argument("--fiscal-year", action="store_true", help="print the fiscal year instead")
    p.add_argument("--calendar", metavar="YYYY-MM", help="print a BS month as a grid")
    p.add_argument("--add-days", type=int, metavar="N", help="BS DATE plus N days")
    p.add_argument("--add-months", type=int, metavar="N", help="BS DATE plus N BS months")
    p.add_argument("--until", metavar="BS_DATE", help="years, months and days from BS DATE")
    p.add_argument(
        "--age",
        action="store_true",
        help="completed years since BS DATE (to --until, or today in Nepal)",
    )
    p.add_argument(
        "--allow-disputed",
        action="store_true",
        help="use the majority reading inside the disputed span of BS 2062",
    )
    return parser


def _run(args: argparse.Namespace) -> str | None:
    command: str = args.command
    if command == "normalize":
        return normalize(_read(args.text), joiners=args.joiners, danda=not args.no_danda)
    if command == "digits":
        text = _read(args.text)
        return to_devanagari_digits(text) if args.to == "devanagari" else to_ascii_digits(text)
    if command == "format":
        return format_number(_read(args.number), devanagari=args.devanagari)
    if command == "words":
        number = _read(args.number)
        if args.ordinal:
            if args.currency or args.only:
                raise ValueError("--ordinal cannot be combined with --currency or --only")
            digits = to_ascii_digits(number).strip()
            if not digits.isdigit():
                raise ValueError(f"not a whole number: {number!r}")
            return ordinal_to_words(int(digits))
        if args.currency:
            return currency_to_words(number, only=args.only)
        return number_to_words(number)
    if command == "number":
        value = parse_words(_read(args.text))
        if args.group:
            return format_number(value, devanagari=args.devanagari)
        return to_devanagari_digits(str(value)) if args.devanagari else str(value)
    if command == "detect":
        return _run_detect(args)
    if command == "tokenize":
        text = _read(args.text)
        items = sentences(text) if args.sentences else tokenize(text)
        if args.json:
            return json.dumps(items, ensure_ascii=False)
        return "\n".join(items)
    if command == "aksharas":
        return _run_aksharas(args)
    if command == "sort":
        lines = _read(args.text).splitlines()
        if args.unique:
            lines = list(dict.fromkeys(lines))
        ordered = sorted_nepali(
            lines, reverse=args.reverse, conjunct_letters=not args.conjuncts_under_first
        )
        return "\n".join(ordered)
    if command == "convert":
        return _run_convert(args)
    if command == "translit":
        convert = to_roman if args.to == "roman" else to_devanagari
        return convert(_read(args.text), args.scheme, digits=not args.keep_digits)
    if command == "date":
        return _run_date(args)
    raise AssertionError(f"unhandled command {command!r}")  # pragma: no cover


def _percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "0.0%"


def _keep_options(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "keep": args.keep,
        "keep_words": args.keep_word,
    }


def _read_input(name: str, encoding: str) -> str:
    """Read a text input exactly: no line-ending changes, a byte-order mark dropped."""
    if name == "-":
        buffer = getattr(sys.stdin, "buffer", None)
        if buffer is None:
            return str(sys.stdin.read())
        data = buffer.read()
        shown = "standard input"
    else:
        path = Path(name)
        if path.is_dir():
            raise ValueError(f"{name} is a directory, not a file")
        try:
            data = path.read_bytes()
        except OSError as error:
            raise ValueError(f"cannot read {name}: {error.strerror or error}") from error
        shown = name
    if data[:4] == b"\xd0\xcf\x11\xe0" or data[:4] == b"PK\x03\x04":
        raise ValueError(
            f"{shown} is not plain text (it looks like a Word or zip file); "
            "for a .docx file use --docx"
        )
    codec = "utf-8-sig" if encoding.lower().replace("_", "-") in ("utf-8", "utf8") else encoding
    try:
        return str(data.decode(codec))
    except LookupError as error:
        raise ValueError(f"unknown encoding {encoding!r}") from error
    except UnicodeDecodeError as error:
        hint = (
            "; text saved by an old program is often Windows-1252: try --encoding cp1252"
            if codec == "utf-8-sig"
            else ""
        )
        raise ValueError(f"{shown} is not valid {encoding} (byte {error.start}){hint}") from error


def _check_output(target: Path, source: str | None, force: bool) -> None:
    """Refuse to write over the input, or over an existing file without --force."""
    if target.is_dir():
        raise ValueError(f"the output {target} is a directory")
    if source is not None and source != "-":
        origin = Path(source)
        same = (
            target.exists() and origin.exists() and target.samefile(origin)
        ) or target.resolve() == origin.resolve()
        if same:
            raise ValueError(f"the output file is the input file ({source}); choose another name")
    if target.exists() and not force:
        raise ValueError(f"the output file {target} already exists; use --force to replace it")
    if not target.parent.is_dir():
        raise ValueError(f"the output directory {target.parent} does not exist")


def _write_stdout(text: str) -> None:
    """Write ``text`` exactly: no added newline, no line-ending translation."""
    sys.stdout.flush()
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(text)
    else:
        buffer.write(text.encode("utf-8"))
        buffer.flush()


def _warn_text(result: legacy.PreetiResult | legacy.PreetiEncodeResult, report: bool) -> None:
    to_preeti = isinstance(result, legacy.PreetiEncodeResult)
    if result.unmapped:
        shown = " ".join(_describe_char(ch) for ch in result.unmapped_chars)
        what = "Preeti key" if to_preeti else "agreed Preeti entry"
        print(
            f"aksharkit: warning: {len(result.unmapped)} character(s) had no {what} "
            f"and were left unchanged: {shown}",
            file=sys.stderr,
        )
        if report:
            for item in result.unmapped:
                print(
                    f"  line {item.line}, column {item.column}: {_describe_char(item.char)}",
                    file=sys.stderr,
                )
    if isinstance(result, legacy.PreetiEncodeResult):
        if result.skipped:
            print(
                f"aksharkit: warning: {len(result.skipped)} word(s) were left in Unicode "
                "because their Preeti keys did not convert back to the same text",
                file=sys.stderr,
            )
            if report:
                for span in result.skipped:
                    print(f"  line {span.line}, column {span.column}: {span.text}", file=sys.stderr)
        if result.foreign and not result.mark_kept:
            print(
                f"aksharkit: note: {len(result.foreign)} stretch(es) with no Devanagari "
                "(English words, ASCII numbers) were left as they were; in the Preeti font "
                "they would show as other letters. Use --mark-kept to mark them",
                file=sys.stderr,
            )
        if report:
            for alien in result.foreign:
                print(
                    f"  line {alien.line}, column {alien.column}: left alone: {alien.text}",
                    file=sys.stderr,
                )
            if result.complete:
                print(
                    "aksharkit: every Nepali word was written as Preeti keys that convert "
                    "back to the same text",
                    file=sys.stderr,
                )
            _encode_summary(result.stats, len(result.protected))
        return
    if report:
        if not result.unmapped:
            print("aksharkit: every character had an agreed Preeti entry", file=sys.stderr)
        _summary(result.stats, len(result.protected))


def _encode_summary(stats: legacy.PreetiEncodeStats, protected_spans: int | None = None) -> None:
    line = (
        f"aksharkit: summary: {stats.words_encoded} of {stats.words} Nepali word(s) written "
        f"as keys ({_percent(stats.words_encoded, stats.words)}); {stats.encoded} character(s) "
        f"written as keys, {stats.unmapped} left with no key, {stats.skipped} in words that "
        f"did not read back, {stats.foreign} not Devanagari and left alone"
    )
    if protected_spans is not None:
        line += f"; {protected_spans} stretch(es) protected"
    print(line, file=sys.stderr)


def _summary(stats: legacy.PreetiStats, protected_spans: int | None = None) -> None:
    whole = stats.convertible
    line = (
        f"aksharkit: summary: {whole} character(s) to convert: "
        f"{stats.agreed} by agreed keys ({_percent(stats.agreed, whole)}), "
        f"{stats.majority} by majority keys ({_percent(stats.majority, whole)}), "
    )
    if stats.unconfirmed:
        line += f"{stats.unconfirmed} by unconfirmed keys ({_percent(stats.unconfirmed, whole)}), "
    line += f"{stats.unmapped} left unchanged ({_percent(stats.unmapped, whole)})"
    if protected_spans is not None:
        line += f"; {protected_spans} stretch(es) protected"
    print(line, file=sys.stderr)


def _convert_text(
    text: str, args: argparse.Namespace
) -> legacy.PreetiResult | legacy.PreetiEncodeResult:
    markers = (args.markers[0], args.markers[1]) if args.markers else None
    if args.to == "preeti":
        return legacy.encode_preeti(
            text,
            strict=args.strict,
            include_unconfirmed=args.include_unconfirmed,
            keep_links=not args.no_keep_links,
            markers=markers,
            digits=args.digits,
            mark_kept=(args.mark_kept[0], args.mark_kept[1]) if args.mark_kept else None,
            **_keep_options(args),
        )
    return legacy.convert_preeti(
        text,
        include_unconfirmed=args.include_unconfirmed,
        strict=args.strict,
        keep_links=not args.no_keep_links,
        markers=markers,
        **_keep_options(args),
    )


def _encode_docx(
    source: str, target: Path, args: argparse.Namespace
) -> legacy_docx.DocxEncodeReport:
    report = legacy_docx.encode_docx(
        source,
        target,
        overwrite=args.force,
        font=args.docx_font or legacy_docx.DEFAULT_PREETI_FONT,
        strict=args.strict,
        include_unconfirmed=args.include_unconfirmed,
        digits=args.digits,
        keep_links=not args.no_keep_links,
        **_keep_options(args),
    )
    if not report.stats.words:
        print(
            f"aksharkit: warning: {source} holds no Devanagari text; nothing was changed",
            file=sys.stderr,
        )
    if report.left:
        print(
            f"aksharkit: warning: {len(report.left)} stretch(es) of Nepali text were left in "
            "Unicode, in the font they had",
            file=sys.stderr,
        )
        if args.report:
            for item in report.left:
                why = item.reason
                if item.chars:
                    why += ": " + " ".join(_describe_char(ch) for ch in item.chars)
                print(
                    f"  {item.part}, paragraph {item.paragraph}: {item.text} ({why})",
                    file=sys.stderr,
                )
    if args.report:
        if report.stats.words and report.complete:
            print(
                "aksharkit: every Nepali word was written as Preeti keys that convert back "
                "to the same text",
                file=sys.stderr,
            )
        print(
            f"aksharkit: docx: {report.runs_converted} run(s) written as keys and set to "
            f"{report.font}, {report.runs_split} mixed run(s) cut into pieces, "
            f"{report.runs_untouched} run(s) left as they were, "
            f"{report.paragraphs_changed} paragraph(s) changed, "
            f"{report.boundary_moves} word(s) moved whole into their first run; parts read: "
            f"{', '.join(report.parts)}",
            file=sys.stderr,
        )
        _encode_summary(report.stats)
    return report


def _convert_docx(
    source: str, target: Path, args: argparse.Namespace
) -> legacy_docx.DocxReport | legacy_docx.DocxEncodeReport:
    if not source.lower().endswith(".docx"):
        raise ValueError(
            f"{source} does not end in .docx; an old .doc file must be saved as .docx first"
        )
    if not Path(source).is_file():
        raise ValueError(f"no such file: {source}")
    _check_output(target, source, args.force)
    if args.to == "preeti":
        return _encode_docx(source, target, args)
    report = legacy_docx.convert_docx(
        source,
        target,
        overwrite=args.force,
        font=args.docx_font or legacy_docx.DEFAULT_DOCX_FONT,
        source_fonts=args.source_font or ("Preeti",),
        include_unconfirmed=args.include_unconfirmed,
        strict=args.strict,
        keep_links=False,
        **_keep_options(args),
    )
    fonts = ", ".join(f"{name} ({count})" for name, count in report.fonts_seen.items()) or "none"
    if not report.runs_converted:
        wanted = ", ".join(report.source_fonts)
        print(
            f"aksharkit: warning: no run of {source} uses the font {wanted}; nothing was "
            f"converted. Fonts found on text runs: {fonts}",
            file=sys.stderr,
        )
    if report.runs_partial_font:
        print(
            f"aksharkit: warning: {report.runs_partial_font} run(s) use Preeti for only part "
            "of their characters and were left alone",
            file=sys.stderr,
        )
    if report.unmapped:
        shown = " ".join(_describe_char(ch) for ch in report.unmapped_chars)
        print(
            f"aksharkit: warning: {len(report.unmapped)} character(s) had no agreed "
            f"Preeti entry and were left unchanged: {shown}",
            file=sys.stderr,
        )
        if args.report:
            for item in report.unmapped:
                print(
                    f"  {item.part}, paragraph {item.paragraph}: {_describe_char(item.char)}",
                    file=sys.stderr,
                )
    if args.report:
        if report.runs_converted and not report.unmapped:
            print("aksharkit: every character had an agreed Preeti entry", file=sys.stderr)
        print(
            f"aksharkit: docx: {report.runs_converted} run(s) converted and set to "
            f"{report.font}, {report.runs_untouched} run(s) in other fonts left as they were, "
            f"{report.paragraphs_changed} paragraph(s) changed, "
            f"{report.boundary_moves} run boundary move(s); parts read: "
            f"{', '.join(report.parts)}",
            file=sys.stderr,
        )
        print(f"aksharkit: docx: fonts found on text runs: {fonts}", file=sys.stderr)
        _summary(report.stats)
    return report


def _run_convert(args: argparse.Namespace) -> str | None:
    """Convert Preeti text or files; warnings go to standard error."""
    inputs = args.input or []
    documents = args.docx or []
    if args.text is not None and (inputs or documents):
        raise ValueError("give TEXT, or -i FILE, or --docx FILE, not several of them")
    if args.output and args.out_dir:
        raise ValueError("give -o FILE or --out-dir DIR, not both")
    if args.to != "preeti" and (args.mark_kept or args.digits != "keep"):
        raise ValueError("--mark-kept and --digits apply to --to preeti only")
    if documents and (args.markers or args.mark_kept):
        raise ValueError("--markers and --mark-kept apply to plain text, not to .docx files")
    if documents and args.no_keep_links and args.to != "preeti":
        raise ValueError("--no-keep-links applies to plain text, not to .docx files")
    if documents and args.to == "preeti" and args.source_font:
        raise ValueError("--source-font has no meaning with --to preeti")
    if inputs.count("-") > 1:
        raise ValueError("standard input can be read only once")
    many = len(inputs) + len(documents) > 1
    if many and not args.out_dir:
        raise ValueError("several input files need --out-dir DIR")
    if documents and not (args.output or args.out_dir):
        raise ValueError("--docx needs -o FILE (or --out-dir DIR): a Word file is not printed")
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is not None:
        if not out_dir.is_dir():
            raise ValueError(f"the output directory {out_dir} does not exist")
        if "-" in inputs:
            raise ValueError("standard input cannot be used with --out-dir")
        names = [Path(name).name for name in [*inputs, *documents]]
        if len(set(names)) != len(names):
            raise ValueError("two input files have the same name; they would overwrite each other")
    if not args.quiet:
        print(f"aksharkit: note: Preeti conversion is {legacy.PREETI_LABEL}", file=sys.stderr)

    reports: list[dict[str, Any]] = []
    printed: str | None = None
    left = False

    def target_for(source: str) -> Path | None:
        if out_dir is not None:
            return out_dir / Path(source).name
        return Path(args.output) if args.output else None

    for source in inputs:
        text = _read_input(source, args.encoding)
        target = target_for(source)
        if target is not None:
            _check_output(target, source, args.force)
        if many:
            print(f"aksharkit: file {source}", file=sys.stderr)
        result = _convert_text(text, args)
        _warn_text(result, args.report)
        left = left or not result.complete
        entry = result.as_dict()
        entry["input"] = "standard input" if source == "-" else source
        if target is not None:
            target.write_bytes(result.text.encode("utf-8"))
            entry["output"] = str(target)
            del entry["text"]
        elif not args.json:
            _write_stdout(result.text)
        reports.append(entry)
    for source in documents:
        target = target_for(source)
        assert target is not None
        if many:
            print(f"aksharkit: file {source}", file=sys.stderr)
        report = _convert_docx(source, target, args)
        left = left or not report.complete
        entry = report.as_dict()
        entry["input"] = source
        entry["output"] = str(target)
        reports.append(entry)
    if not inputs and not documents:
        if args.out_dir:
            raise ValueError("--out-dir needs input files (-i FILE or --docx FILE)")
        result = _convert_text(_read(args.text), args)
        _warn_text(result, args.report)
        left = not result.complete
        entry = result.as_dict()
        if args.output:
            target = Path(args.output)
            _check_output(target, None, args.force)
            target.write_bytes((result.text + "\n").encode("utf-8"))
            entry["output"] = str(target)
            del entry["text"]
        elif not args.json:
            printed = result.text
        reports.append(entry)
    args.left_unconverted = bool(args.fail_on_unmapped and left)
    if args.json:
        payload: Any = reports[0] if len(reports) == 1 else {"files": reports}
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return printed


def _describe_char(ch: str) -> str:
    shown = ch if ch.isprintable() else "?"
    return f"{shown} (U+{ord(ch):04X})"


def _run_aksharas(args: argparse.Namespace) -> str:
    text = _read(args.text)
    if args.truncate is not None:
        if args.count or args.json or args.sep is not None:
            raise ValueError("--truncate cannot be combined with --count, --json or --sep")
        return truncate(text, args.truncate, suffix=args.suffix)
    if args.suffix:
        raise ValueError("--suffix needs --truncate")
    if args.count:
        return str(akshara_count(text))
    units = akshara_spans(text)
    if args.json:
        rows = [{"text": unit.text, "start": unit.start, "end": unit.end} for unit in units]
        return json.dumps(rows, ensure_ascii=False)
    separator = "\n" if args.sep is None else args.sep
    return separator.join(unit.text for unit in units)


def _format_bs(bs: dates.BSDate, args: argparse.Namespace) -> str:
    style = args.style if args.pattern is None else args.pattern
    if args.pattern is not None and "%" not in args.pattern:
        raise ValueError(f"--pattern has no % token: {args.pattern!r}")
    return dates.format_bs(bs, style, devanagari=args.devanagari)


def _run_detect(args: argparse.Namespace) -> str:
    text = _read(args.text)
    pairs = detect.token_scripts(text)
    if args.json:
        report = {
            "script": detect.detect_script(text),
            "counts": detect.script_counts(text),
            "shares": detect.script_shares(text),
            "tokens": [{"text": token, "script": script} for token, script in pairs],
            "romanised_nepali_score": detect.romanised_nepali_score(text),
            "looks_romanised_nepali": detect.looks_romanised_nepali(text),
        }
        return json.dumps(report, ensure_ascii=False)
    if args.tokens:
        return "\n".join(f"{token}\t{script}" for token, script in pairs)
    shares = detect.script_shares(text)
    lines = [f"script: {detect.detect_script(text)}"]
    lines += [f"{name}: {shares[name]:.1%}" for name in detect.SCRIPTS]
    return "\n".join(lines)


_YEAR_MONTH = re.compile(r"^\s*(\d{4})\s*[-/.]\s*(\d{1,2})\s*$")


def _run_date_tools(args: argparse.Namespace) -> str | None:
    """The BS-only tools of ``date``. Returns None when none was asked for."""
    allow: bool = args.allow_disputed
    arithmetic = args.add_days is not None or args.add_months is not None or args.until or args.age
    if args.calendar is not None:
        if arithmetic or args.date is not None:
            raise ValueError("--calendar takes only a month (YYYY-MM) and no DATE")
        match = _YEAR_MONTH.match(to_ascii_digits(args.calendar))
        if match is None:
            raise ValueError(f"not a BS month in YYYY-MM form: {args.calendar!r}")
        return dates.format_month_calendar(
            int(match[1]), int(match[2]), devanagari=args.devanagari, allow_disputed=allow
        )
    if not arithmetic:
        return None
    if args.to == "ad":
        raise ValueError("--add-days, --add-months, --until and --age work on BS dates only")
    if args.date is None:
        raise ValueError("a BS date is required")
    bs = dates.parse_bs(_read(args.date))
    if args.add_days is not None or args.add_months is not None:
        if args.until or args.age:
            raise ValueError("--add-days/--add-months cannot be combined with --until or --age")
        if args.add_months is not None:
            bs = dates.add_months(bs, args.add_months, allow_disputed=allow)
        if args.add_days is not None:
            bs = dates.add_days(bs, args.add_days, allow_disputed=allow)
        return _format_bs(bs, args)
    end = dates.parse_bs(args.until) if args.until else dates.today_bs()
    gap = dates.difference(bs, end, allow_disputed=allow)
    if args.age:
        out = str(gap.years)
    else:
        total = dates.days_between(bs, end, allow_disputed=allow)
        out = f"{gap.years} years, {gap.months} months, {gap.days} days ({total} days)"
    return to_devanagari_digits(out) if args.devanagari else out


def _run_date(args: argparse.Namespace) -> str:
    allow: bool = args.allow_disputed
    tool = _run_date_tools(args)
    if tool is not None:
        return tool
    if args.pattern is not None and (args.to == "ad" or args.fiscal_year):
        raise ValueError("--pattern formats BS dates only")
    if args.to == "ad":
        if args.date is None:
            raise ValueError("a BS date is required with --to ad")
        bs = dates.parse_bs(_read(args.date))
        if args.fiscal_year:
            return dates.fiscal_year(bs, devanagari=args.devanagari)
        ad = dates.bs_to_ad(*bs, allow_disputed=allow)
        if args.style == "iso":
            out = ad.isoformat()
        else:
            out = f"{ad.day} {ad.strftime('%B')} {ad.year}"
            if args.style == "full":
                out += f", {ad.strftime('%A')}"
        return to_devanagari_digits(out) if args.devanagari and args.style == "iso" else out
    if args.date is None:
        bs = dates.today_bs()
    else:
        text = to_ascii_digits(_read(args.date)).strip()
        try:
            ad = _dt.date.fromisoformat(text)
        except ValueError:
            raise ValueError(f"not an AD date in YYYY-MM-DD form: {text!r}") from None
        bs = dates.ad_to_bs(ad, allow_disputed=allow)
    if args.fiscal_year:
        return dates.fiscal_year(bs, devanagari=args.devanagari)
    return _format_bs(bs, args)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns the process exit code."""
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    if extra:
        # argparse gives up on an optional TEXT that comes after an option
        # ("convert preeti --quiet TEXT"). One left-over word is that text.
        text_first = args.command == "convert" and args.text is None and len(extra) == 1
        if not text_first or (extra[0].startswith("-") and extra[0] != "-"):
            parser.error("unrecognized arguments: " + " ".join(extra))
        args.text = extra[0]
    try:
        output = _run(args)
    except DataNotVerifiedError as exc:
        print(f"aksharkit: {exc}", file=sys.stderr)
        return 3
    except (ValueError, TypeError, NotImplementedError) as exc:
        print(f"aksharkit: error: {exc}", file=sys.stderr)
        return 2
    if output is not None:
        print(output)
    return 1 if getattr(args, "left_unconverted", False) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
