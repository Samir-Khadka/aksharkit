"""Command-line interface: ``aksharkit <command> ...``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__, legacy
from ._errors import DataNotVerifiedError
from .normalize import normalize
from .numerals import format_number, to_ascii_digits, to_devanagari_digits
from .tokens import sentences, tokenize
from .words import currency_to_words, number_to_words

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

    p = sub.add_parser("tokenize", help="split into words, or sentences with --sentences")
    p.add_argument("text", nargs="?")
    p.add_argument("--sentences", action="store_true")
    p.add_argument("--json", action="store_true", help="print a JSON array")

    p = sub.add_parser("convert", help="legacy font to Unicode (not available yet)")
    p.add_argument("font", choices=legacy.SUPPORTED_FONTS)
    p.add_argument("text", nargs="?")

    p = sub.add_parser("date", help="BS/AD date conversion (not available yet)")
    p.add_argument("date", nargs="?")
    return parser


def _run(args: argparse.Namespace) -> str:
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
        if args.currency:
            return currency_to_words(number, only=args.only)
        return number_to_words(number)
    if command == "tokenize":
        text = _read(args.text)
        items = sentences(text) if args.sentences else tokenize(text)
        if args.json:
            return json.dumps(items, ensure_ascii=False)
        return "\n".join(items)
    if command == "convert":
        return legacy.to_unicode(_read(args.text), args.font)
    if command == "date":
        from . import dates

        dates.load_calendar()
        raise NotImplementedError("date conversion is not implemented yet")
    raise AssertionError(f"unhandled command {command!r}")  # pragma: no cover


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = _run(args)
    except DataNotVerifiedError as exc:
        print(f"aksharkit: {exc}", file=sys.stderr)
        return 3
    except (ValueError, TypeError, NotImplementedError) as exc:
        print(f"aksharkit: error: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
