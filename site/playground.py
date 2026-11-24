"""Glue between the browser playground and aksharkit.

The page (``site/app.js``) calls :func:`run` with a tool name and a JSON
payload and gets a JSON string back. Only aksharkit's public API is used
here, so the playground shows exactly what the library does.

This file is not part of the installed package. ``scripts/build_site.py``
adds it to the archive the page loads, as ``aksharkit_playground.py``.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from collections.abc import Callable
from typing import Any

import aksharkit as ak
from aksharkit import dates

__all__ = ["TOOLS", "run"]


def _info(_: dict[str, Any]) -> dict[str, Any]:
    first, last = dates.supported_range()
    today_ad = today_bs = ""
    try:  # today is outside the table once the verified range has run out
        today = ak.today_bs()
        today_ad = dates.bs_to_ad(*today, allow_disputed=True).isoformat()
        today_bs = str(today)
    except ValueError:
        pass
    return {
        "version": ak.__version__,
        "python": sys.version.split()[0],
        "ad_first": first.isoformat(),
        "ad_last": last.isoformat(),
        "today_ad": today_ad,
        "today_bs": today_bs,
    }


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", ""))
    out = ak.normalize(
        text,
        joiners=str(payload.get("joiners", "safe")),
        danda=bool(payload.get("danda", True)),
    )
    return {"text": out, "changed": out != text, "before": len(text), "after": len(out)}


def _attempt(call: Callable[[], str]) -> dict[str, Any]:
    """Run one conversion; a failure is reported for that field only."""
    try:
        return {"ok": True, "value": call()}
    except (ValueError, TypeError, ArithmeticError) as exc:
        return {"ok": False, "value": str(exc)}


def _numbers(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("type a number")
    value = ak.parse_number(text)
    only = bool(payload.get("only", False))
    return {
        "ascii": _attempt(lambda: ak.to_ascii_digits(text)),
        "devanagari": _attempt(lambda: ak.to_devanagari_digits(text)),
        "grouped": _attempt(lambda: ak.format_number(value)),
        "grouped_devanagari": _attempt(lambda: ak.format_number(value, devanagari=True)),
        "words": _attempt(lambda: ak.number_to_words(value)),
        "currency": _attempt(lambda: ak.currency_to_words(value, only=only)),
    }


def _dates(payload: dict[str, Any]) -> dict[str, Any]:
    direction = str(payload.get("direction", "ad2bs"))
    allow = bool(payload.get("allow_disputed", False))
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("type a date as YYYY-MM-DD")
    if direction == "bs2ad":
        bs = ak.parse_bs(text)
        ad = ak.bs_to_ad(*bs, allow_disputed=allow)
    elif direction == "ad2bs":
        try:
            ad = _dt.date.fromisoformat(ak.to_ascii_digits(text))
        except ValueError:
            raise ValueError(f"not an AD date in YYYY-MM-DD form: {text!r}") from None
        bs = ak.ad_to_bs(ad, allow_disputed=allow)
    else:
        raise ValueError(f"unknown direction {direction!r}")
    return {
        "bs_iso": ak.format_bs(bs),
        "bs_iso_ne": ak.format_bs(bs, devanagari=True),
        "bs_long": ak.format_bs(bs, "full"),
        "bs_long_ne": ak.format_bs(bs, "full", devanagari=True),
        "ad_iso": ad.isoformat(),
        "ad_long": f"{ad.day} {ad.strftime('%B')} {ad.year}, {ad.strftime('%A')}",
        "fiscal_year": ak.fiscal_year(bs),
        "fiscal_year_ne": ak.fiscal_year(bs, devanagari=True),
    }


def _tokenize(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", ""))
    tokens = ak.tokenize_spans(text)
    return {
        "tokens": [
            {"text": t.text, "kind": t.kind, "stop": ak.is_stopword(t.text)} for t in tokens
        ],
        "sentences": ak.sentences(text),
        "words": sum(1 for t in tokens if t.kind in ("word", "latin")),
    }


def _translit(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", ""))
    scheme = str(payload.get("scheme", "iast"))
    direction = str(payload.get("direction", "roman"))
    if direction == "roman":
        out = ak.to_roman(text, scheme)
    elif direction == "devanagari":
        out = ak.to_devanagari(text, scheme)
    else:
        raise ValueError(f"unknown direction {direction!r}")
    return {
        "text": out,
        "approximate": scheme == "simple",
        "lang": "ne-Latn" if direction == "roman" else "ne",
    }


def _words(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("type a number in Nepali words")
    value = ak.parse_words(text)
    return {
        "number": _attempt(lambda: str(value)),
        "grouped": _attempt(lambda: ak.format_number(value)),
        "grouped_devanagari": _attempt(lambda: ak.format_number(value, devanagari=True)),
        "respelt": _attempt(lambda: ak.number_to_words(value)),
    }


def _detect(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", ""))
    return {
        "script": ak.detect_script(text),
        "counts": ak.script_counts(text),
        "shares": ak.script_shares(text),
        "tokens": [{"text": token, "script": script} for token, script in ak.token_scripts(text)],
        "romanised_score": ak.romanised_nepali_score(text),
        "romanised": ak.looks_romanised_nepali(text),
    }


_YEAR_MONTH = re.compile(r"^(\d{4})\s*[-/.]\s*(\d{1,2})$")


def _long_ad(ad: _dt.date) -> str:
    return f"{ad.day} {ad.strftime('%B')} {ad.year}"


def _calendar(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", "")).strip()
    match = _YEAR_MONTH.match(ak.to_ascii_digits(text))
    if match is None:
        raise ValueError(f"type a BS month as YYYY-MM, not {text!r}")
    year, month = int(match[1]), int(match[2])
    allow = bool(payload.get("allow_disputed", False))
    nepali = bool(payload.get("devanagari", True))
    grid = ak.format_month_calendar(year, month, devanagari=nepali, allow_disputed=allow)
    title, head, *rows = grid.split("\n")
    length = ak.days_in_month(year, month)
    first = ak.bs_to_ad(year, month, 1, allow_disputed=True)
    last = ak.bs_to_ad(year, month, length, allow_disputed=True)
    return {
        "title": title,
        "head": head.split("\t"),
        "weeks": [(row.split("\t") + [""] * 7)[:7] for row in rows],
        "span": f"{length} days: {_long_ad(first)} to {_long_ad(last)}",
        "text": grid,
        "lang": "ne" if nepali else "en",
    }


def _whole(payload: dict[str, Any], field: str) -> int:
    text = ak.to_ascii_digits(str(payload.get(field, ""))).strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"{field} must be a whole number, not {text!r}") from None


def _datemath(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text", "")).strip()
    if not text:
        raise ValueError("type a BS date as YYYY-MM-DD")
    start = ak.parse_bs(text)
    allow = bool(payload.get("allow_disputed", False))
    days = _whole(payload, "days")
    months = _whole(payload, "months")
    until = str(payload.get("until", "")).strip()

    def moved() -> ak.BSDate:
        later = ak.add_months(start, months, allow_disputed=allow)
        return ak.add_days(later, days, allow_disputed=allow)

    def end() -> ak.BSDate:
        return ak.parse_bs(until) if until else ak.today_bs()

    def gap() -> str:
        found = ak.difference(start, end(), allow_disputed=allow)
        return f"{found.years} years, {found.months} months, {found.days} days"

    return {
        "moved": _attempt(lambda: ak.format_bs(moved())),
        "moved_ne": _attempt(lambda: ak.format_bs(moved(), "full", devanagari=True)),
        "moved_ad": _attempt(lambda: _long_ad(ak.bs_to_ad(*moved(), allow_disputed=allow))),
        "until": _attempt(lambda: ak.format_bs(end())),
        "gap": _attempt(gap),
        "days": _attempt(lambda: str(ak.days_between(start, end(), allow_disputed=allow))),
        "age": _attempt(lambda: str(ak.age(start, end(), allow_disputed=allow))),
    }


TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "info": _info,
    "normalize": _normalize,
    "numbers": _numbers,
    "words": _words,
    "dates": _dates,
    "calendar": _calendar,
    "datemath": _datemath,
    "tokenize": _tokenize,
    "detect": _detect,
    "translit": _translit,
}


def run(tool: str, payload: str = "{}") -> str:
    """Run one playground tool. Never raises: errors come back as JSON.

    Returns ``{"ok": true, "result": {...}}`` or
    ``{"ok": false, "kind": "ValueError", "error": "..."}``.
    """
    try:
        handler = TOOLS.get(tool)
        if handler is None:
            raise ValueError(f"unknown tool {tool!r}")
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("payload must be a JSON object")
        answer: dict[str, Any] = {"ok": True, "result": handler(data)}
    except (ValueError, TypeError, ArithmeticError, NotImplementedError) as exc:
        answer = {"ok": False, "kind": type(exc).__name__, "error": str(exc)}
    return json.dumps(answer, ensure_ascii=False)
