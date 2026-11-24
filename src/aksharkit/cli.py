"""Command-line interface: ``aksharkit <command> ...``."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections.abc import Sequence

from . import __version__, dates, detect, legacy
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

    p = sub.add_parser("convert", help="legacy font to Unicode (not available yet)")
    p.add_argument("font", choices=legacy.SUPPORTED_FONTS)
    p.add_argument("text", nargs="?")

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
        return legacy.to_unicode(_read(args.text), args.font)
    if command == "translit":
        convert = to_roman if args.to == "roman" else to_devanagari
        return convert(_read(args.text), args.scheme, digits=not args.keep_digits)
    if command == "date":
        return _run_date(args)
    raise AssertionError(f"unhandled command {command!r}")  # pragma: no cover


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
