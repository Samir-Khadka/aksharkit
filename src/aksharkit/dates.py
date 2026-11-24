"""Bikram Sambat (BS) and Gregorian (AD) date conversion.

BS month lengths are published, not computed. The table in
``data/bs_calendar.json`` covers BS 2000-2083 (AD 1943-04-14 to 2027-04-13).
It was built by comparing five published tables year by year; see
``docs/sources.md``. Dates outside the table raise :class:`DateRangeError`.

One span is disputed: the sources split on the lengths of Baishakh and
Jestha 2062, so AD 2005-05-14 to 2005-06-14 has two possible BS readings one
day apart. Conversions inside that span raise :class:`DisputedDateError`
unless ``allow_disputed=True`` is passed, in which case the majority reading
is used.
"""

from __future__ import annotations

import datetime as _dt
import re
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
from typing import NamedTuple

from ._data import load_table, require_verified
from .numerals import to_ascii_digits, to_devanagari_digits

__all__ = [
    "BS_MONTHS",
    "BS_MONTHS_ROMAN",
    "PATTERN_TOKENS",
    "WEEKDAYS",
    "WEEKDAYS_ROMAN",
    "BSDate",
    "BSDifference",
    "DateRangeError",
    "DisputedDateError",
    "ad_to_bs",
    "add_days",
    "add_months",
    "age",
    "bs_to_ad",
    "days_between",
    "days_in_month",
    "days_in_year",
    "difference",
    "fiscal_year",
    "format_bs",
    "format_month_calendar",
    "is_valid_bs",
    "load_calendar",
    "month_calendar",
    "month_name",
    "parse_bs",
    "supported_range",
    "today_bs",
    "weekday_name",
]

#: Names of the twelve BS months, Baishakh first.
BS_MONTHS: tuple[str, ...] = (
    "वैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज",
    "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत",
)  # fmt: skip

#: Romanised month names, in the same order.
BS_MONTHS_ROMAN: tuple[str, ...] = (
    "Baishakh", "Jestha", "Asar", "Shrawan", "Bhadra", "Asoj",
    "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra",
)  # fmt: skip

#: Weekday names, Sunday first (the Nepali week starts on Sunday).
WEEKDAYS: tuple[str, ...] = (
    "आइतबार", "सोमबार", "मङ्गलबार", "बुधबार", "बिहीबार", "शुक्रबार", "शनिबार",
)  # fmt: skip

#: Romanised weekday names, Sunday first.
WEEKDAYS_ROMAN: tuple[str, ...] = (
    "Aaitabar", "Sombar", "Mangalbar", "Budhabar", "Bihibar", "Shukrabar", "Shanibar",
)  # fmt: skip

#: The fiscal year starts on 1 Shrawan, the fourth month.
_FISCAL_START_MONTH = 4


class DateRangeError(ValueError):
    """The date is outside the verified table, or is not a real BS date."""


class DisputedDateError(ValueError):
    """The date falls in a span where the published tables disagree."""


class BSDate(NamedTuple):
    """A Bikram Sambat date. Compares and sorts like ``(year, month, day)``."""

    year: int
    month: int
    day: int

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


@dataclass(frozen=True)
class _Calendar:
    months: dict[int, tuple[int, ...]]
    first_year: int
    last_year: int
    epoch_ad: _dt.date
    year_starts: tuple[int, ...]  # day offset of 1 Baishakh for each year, plus the end
    disputed: tuple[tuple[BSDate, BSDate], ...]

    @property
    def last_ad(self) -> _dt.date:
        return self.epoch_ad + _dt.timedelta(days=self.year_starts[-1] - 1)


@lru_cache(maxsize=1)
def _calendar() -> _Calendar:
    table = load_table("bs_calendar")
    years = require_verified(table, "BS/AD date conversion", "years")
    months: dict[int, tuple[int, ...]] = {}
    for year, lengths in years.items():
        row = tuple(int(n) for n in lengths)
        if len(row) != 12 or not all(29 <= n <= 32 for n in row) or sum(row) not in (365, 366):
            raise ValueError(f"BS calendar table is malformed for year {year}")
        months[int(year)] = row
    first, last = min(months), max(months)
    if sorted(months) != list(range(first, last + 1)):
        raise ValueError("BS calendar table has a gap between years")
    epoch = table.get("epoch") or {}
    if tuple(epoch.get("bs", ())) != (first, 1, 1):
        raise ValueError("BS calendar table: the epoch must be 1 Baishakh of the first year")
    starts = [0]
    for year in range(first, last + 1):
        starts.append(starts[-1] + sum(months[year]))
    disputed = tuple(
        (BSDate(*span["from"]), BSDate(*span["to"])) for span in table.get("disputed", [])
    )
    return _Calendar(
        months=months,
        first_year=first,
        last_year=last,
        epoch_ad=_dt.date.fromisoformat(epoch["ad"]),
        year_starts=tuple(starts),
        disputed=disputed,
    )


def load_calendar() -> dict[int, tuple[int, ...]]:
    """Return ``{bs_year: (twelve month lengths)}`` from the verified table."""
    return dict(_calendar().months)


def supported_range() -> tuple[_dt.date, _dt.date]:
    """Return the first and last Gregorian dates that can be converted."""
    cal = _calendar()
    return cal.epoch_ad, cal.last_ad


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_year_month(year: int, month: int) -> _Calendar:
    cal = _calendar()
    for name, value in (("year", year), ("month", month)):
        if not _is_int(value):
            raise TypeError(f"BS {name} must be an int, not {type(value).__name__}")
    if not cal.first_year <= year <= cal.last_year:
        raise DateRangeError(
            f"BS year {year} is outside the verified table ({cal.first_year} to {cal.last_year})"
        )
    if not 1 <= month <= 12:
        raise DateRangeError(f"BS month must be 1 to 12, not {month}")
    return cal


def days_in_month(year: int, month: int) -> int:
    """Number of days in a BS month."""
    return _check_year_month(year, month).months[year][month - 1]


def days_in_year(year: int) -> int:
    """Number of days in a BS year (365 or 366)."""
    return sum(_check_year_month(year, 1).months[year])


def is_valid_bs(year: int, month: int, day: int) -> bool:
    """True if the BS date exists in the verified table."""
    try:
        length = days_in_month(year, month)
    except (DateRangeError, TypeError):
        return False
    return _is_int(day) and 1 <= day <= length


def _require_valid(bs: BSDate) -> _Calendar:
    cal = _check_year_month(bs.year, bs.month)
    if not _is_int(bs.day):
        raise TypeError(f"BS day must be an int, not {type(bs.day).__name__}")
    length = cal.months[bs.year][bs.month - 1]
    if not 1 <= bs.day <= length:
        raise DateRangeError(
            f"{BS_MONTHS_ROMAN[bs.month - 1]} {bs.year} has {length} days; day {bs.day} is invalid"
        )
    return cal


def _check_disputed(cal: _Calendar, bs: BSDate, allow: bool) -> None:
    if allow:
        return
    for start, end in cal.disputed:
        if start <= bs <= end:
            raise DisputedDateError(
                f"BS {bs} falls in a span ({start} to {end}) where the published "
                "calendars disagree by one day. Pass allow_disputed=True to use the "
                "majority reading. See docs/sources.md."
            )


def bs_to_ad(year: int, month: int, day: int, *, allow_disputed: bool = False) -> _dt.date:
    """Convert a BS date to a Gregorian date.

    Raises :class:`DateRangeError` for a date outside the table or a day that
    does not exist in that month, and :class:`DisputedDateError` inside the
    disputed span of 2062 unless ``allow_disputed`` is true.
    """
    bs = BSDate(year, month, day)
    cal = _require_valid(bs)
    _check_disputed(cal, bs, allow_disputed)
    row = cal.months[year]
    offset = cal.year_starts[year - cal.first_year] + sum(row[: month - 1]) + day - 1
    return cal.epoch_ad + _dt.timedelta(days=offset)


def ad_to_bs(date: _dt.date, *, allow_disputed: bool = False) -> BSDate:
    """Convert a Gregorian date (or datetime) to a :class:`BSDate`."""
    if isinstance(date, _dt.datetime):
        date = date.date()
    if not isinstance(date, _dt.date):
        raise TypeError(f"expected a datetime.date, not {type(date).__name__}")
    cal = _calendar()
    offset = (date - cal.epoch_ad).days
    if not 0 <= offset < cal.year_starts[-1]:
        raise DateRangeError(
            f"AD {date.isoformat()} is outside the verified table "
            f"({cal.epoch_ad.isoformat()} to {cal.last_ad.isoformat()})"
        )
    index = bisect_right(cal.year_starts, offset) - 1
    year = cal.first_year + index
    remaining = offset - cal.year_starts[index]
    month = 1
    for length in cal.months[year]:
        if remaining < length:
            break
        remaining -= length
        month += 1
    bs = BSDate(year, month, remaining + 1)
    _check_disputed(cal, bs, allow_disputed)
    return bs


def today_bs() -> BSDate:
    """Today's BS date in Nepal Standard Time (UTC+05:45)."""
    npt = _dt.timezone(_dt.timedelta(hours=5, minutes=45))
    return ad_to_bs(_dt.datetime.now(npt).date())


def month_name(month: int, *, roman: bool = False) -> str:
    """Name of BS month ``month`` (1 = Baishakh)."""
    if not _is_int(month) or not 1 <= month <= 12:
        raise DateRangeError(f"BS month must be 1 to 12, not {month!r}")
    return (BS_MONTHS_ROMAN if roman else BS_MONTHS)[month - 1]


def weekday_name(date: _dt.date | BSDate, *, roman: bool = False) -> str:
    """Weekday name for a Gregorian date or a :class:`BSDate`.

    The weekday of a BS date inside the disputed span follows the majority
    reading.
    """
    ad = bs_to_ad(*date, allow_disputed=True) if isinstance(date, BSDate) else date
    index = (ad.weekday() + 1) % 7  # Python: Monday = 0; here Sunday = 0
    return (WEEKDAYS_ROMAN if roman else WEEKDAYS)[index]


_BS_PATTERN = re.compile(r"^\s*(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*$")
_YEAR_TOKEN = re.compile(r"\d{4}")
_DAY_TOKEN = re.compile(r"\d{1,2}")
_YEAR_WORD = "साल"
_DAY_WORD = "गते"
_NAMED_FORMS = "'YYYY month D' or 'D month YYYY'"


def _month_number(name: str) -> int | None:
    """The month a name stands for; only the spellings in this module."""
    if name in BS_MONTHS:
        return BS_MONTHS.index(name) + 1
    folded = name.casefold()
    for number, roman in enumerate(BS_MONTHS_ROMAN, start=1):
        if folded == roman.casefold():
            return number
    return None


def _weekday_index(name: str) -> int | None:
    if name in WEEKDAYS:
        return WEEKDAYS.index(name)
    folded = name.casefold()
    for index, roman in enumerate(WEEKDAYS_ROMAN):
        if folded == roman.casefold():
            return index
    return None


def _parse_named(text: str) -> BSDate:
    """Parse a date written with a month name. Raises rather than guesses."""

    def fail(reason: str) -> ValueError:
        return ValueError(f"not a BS date: {text!r} ({reason}); use YYYY-MM-DD or {_NAMED_FORMS}")

    tokens = to_ascii_digits(text).replace(",", " ").split()
    weekday = _weekday_index(tokens[-1]) if len(tokens) > 3 else None
    weekday_text = tokens.pop() if weekday is not None else ""
    # साल may follow the year and गते the day; nowhere else.
    parts: list[str] = []
    for token in tokens:
        if token == _YEAR_WORD and parts and _YEAR_TOKEN.fullmatch(parts[-1]):
            continue
        if token == _DAY_WORD and parts and _DAY_TOKEN.fullmatch(parts[-1]):
            continue
        parts.append(token)
    if len(parts) != 3:
        raise fail("expected a year, a month name and a day")
    first, name, last = parts
    month = _month_number(name)
    if month is None:
        if _month_number(first) is not None or _month_number(last) is not None:
            raise fail("the month name goes between the year and the day")
        if name.isdigit():
            raise fail("write numeric dates as YYYY-MM-DD")
        raise fail(f"unknown month name {name!r}")
    if _YEAR_TOKEN.fullmatch(first) and _DAY_TOKEN.fullmatch(last):
        year, day = int(first), int(last)
    elif _DAY_TOKEN.fullmatch(first) and _YEAR_TOKEN.fullmatch(last):
        year, day = int(last), int(first)
    else:
        raise fail("the year needs four digits and the day one or two")
    bs = BSDate(year, month, day)
    cal = _require_valid(bs)
    if weekday is not None:
        # Inside the disputed span the weekday cannot be checked.
        _check_disputed(cal, bs, False)
        actual = (bs_to_ad(*bs).weekday() + 1) % 7
        if actual != weekday:
            raise ValueError(
                f"BS {bs} is a {WEEKDAYS_ROMAN[actual]} ({WEEKDAYS[actual]}), not {weekday_text}"
            )
    return bs


def parse_bs(text: str) -> BSDate:
    """Parse a BS date written with numbers or with a month name.

    Accepted forms (Devanagari digits allowed everywhere):

    * ``YYYY-MM-DD``, also with ``/`` or ``.``: ``2083-08-07``, ``२०८३/८/७``;
    * year, month name, day: ``२०८३ मंसिर ८``, ``2083 Mangsir 8``;
    * day, month name, year: ``8 Mangsir 2083``, ``८ मंसिर २०८३``.

    Month names are the ones in :data:`BS_MONTHS` and
    :data:`BS_MONTHS_ROMAN` (any letter case) and no other spelling. With a
    month name, ``साल`` may follow the year, ``गते`` may follow the day, commas
    are ignored, and a weekday name from :data:`WEEKDAYS` or
    :data:`WEEKDAYS_ROMAN` may come last; it is checked against the date and
    a wrong one raises ``ValueError``. The year must have four digits, so
    ``8 Mangsir 83`` is refused rather than guessed.

    The result is checked against the table, so a day that does not exist
    raises :class:`DateRangeError`.
    """
    match = _BS_PATTERN.match(to_ascii_digits(text))
    if match is None:
        if any(ch.isalpha() for ch in text):
            return _parse_named(text)
        raise ValueError(f"not a BS date in YYYY-MM-DD form: {text!r}")
    bs = BSDate(*(int(part) for part in match.groups()))
    _require_valid(bs)
    return bs


_PATTERN_TOKEN = re.compile(r"%(-?.|$)", re.DOTALL)
#: The tokens :func:`format_bs` understands in a pattern.
PATTERN_TOKENS: dict[str, str] = {
    "%Y": "year, four digits (2083)",
    "%y": "year, last two digits (83)",
    "%m": "month number, two digits (08)",
    "%-m": "month number without the leading zero (8)",
    "%B": "month name (Mangsir, or मंसिर with devanagari=True)",
    "%d": "day, two digits (07)",
    "%-d": "day without the leading zero (7)",
    "%A": "weekday name (Sombar, or सोमबार with devanagari=True)",
    "%a": "short weekday name (Som, or सोम with devanagari=True)",
    "%%": "a literal %",
}


def _format_pattern(bs: BSDate, pattern: str, devanagari: bool) -> str:
    def digits(value: str) -> str:
        return to_devanagari_digits(value) if devanagari else value

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token == "%Y":
            return digits(f"{bs.year:04d}")
        if token == "%y":
            return digits(f"{bs.year % 100:02d}")
        if token == "%m":
            return digits(f"{bs.month:02d}")
        if token == "%-m":
            return digits(str(bs.month))
        if token == "%d":
            return digits(f"{bs.day:02d}")
        if token == "%-d":
            return digits(str(bs.day))
        if token == "%B":
            return month_name(bs.month, roman=not devanagari)
        if token == "%A":
            return weekday_name(bs, roman=not devanagari)
        if token == "%a":
            name = weekday_name(bs, roman=not devanagari)
            return name.removesuffix("बार") if devanagari else name[:3]
        if token == "%%":
            return "%"
        known = ", ".join(PATTERN_TOKENS)
        raise ValueError(f"unknown token {token!r} in pattern {pattern!r}; use {known}")

    return _PATTERN_TOKEN.sub(replace, pattern)


def format_bs(
    date: BSDate | tuple[int, int, int],
    style: str = "iso",
    *,
    devanagari: bool = False,
) -> str:
    """Format a BS date with a named style or a pattern.

    ``style`` is ``"iso"`` (``2083-08-07``), ``"long"`` (``2083 Mangsir 7``) or
    ``"full"`` (long plus the weekday). With ``devanagari=True`` the digits and
    names are Nepali: ``२०८३ मंसिर ७, सोमबार``.

    Any ``style`` containing ``%`` is a pattern instead; its tokens are listed
    in :data:`PATTERN_TOKENS`. ``format_bs(d, "%-d %B %Y")`` gives
    ``7 Mangsir 2083``, and with ``devanagari=True`` ``७ मंसिर २०८३``. Only the
    tokens change with ``devanagari``; other text in the pattern is copied as
    it is. An unknown token raises ``ValueError``.
    """
    bs = BSDate(*date)
    _require_valid(bs)
    if "%" in style:
        return _format_pattern(bs, style, devanagari)
    if style == "iso":
        out = str(bs)
    elif style in ("long", "full"):
        out = f"{bs.year} {month_name(bs.month, roman=not devanagari)} {bs.day}"
        if style == "full":
            out += f", {weekday_name(bs, roman=not devanagari)}"
    else:
        raise ValueError(
            f"unknown style {style!r}; use 'iso', 'long', 'full' or a pattern such as '%Y-%m-%d'"
        )
    return to_devanagari_digits(out) if devanagari else out


def fiscal_year(date: BSDate | _dt.date, *, devanagari: bool = False) -> str:
    """Nepal's fiscal year for a date, such as ``2083/84``.

    The fiscal year starts on 1 Shrawan. A Gregorian date is converted first.
    """
    bs = date if isinstance(date, BSDate) else ad_to_bs(date, allow_disputed=True)
    _require_valid(bs)
    start = bs.year if bs.month >= _FISCAL_START_MONTH else bs.year - 1
    out = f"{start}/{(start + 1) % 100:02d}"
    return to_devanagari_digits(out) if devanagari else out


# --- arithmetic --------------------------------------------------------------


class BSDifference(NamedTuple):
    """The gap between two BS dates in whole years, whole months and days."""

    years: int
    months: int
    days: int


def _as_bs(date: BSDate | tuple[int, int, int]) -> BSDate:
    bs = BSDate(*date)
    _require_valid(bs)
    return bs


def _month_is_disputed(cal: _Calendar, year: int, month: int) -> bool:
    return any(
        (start.year, start.month) <= (year, month) <= (end.year, end.month)
        for start, end in cal.disputed
    )


def add_days(
    date: BSDate | tuple[int, int, int], days: int, *, allow_disputed: bool = False
) -> BSDate:
    """The BS date ``days`` days after ``date`` (before it, if negative).

    Raises :class:`DateRangeError` when the result leaves the table and
    :class:`DisputedDateError` when ``date`` or the result is inside the
    disputed span of 2062, unless ``allow_disputed`` is true. Stepping right
    across that span is safe: the two readings agree again after it.
    """
    if not _is_int(days):
        raise TypeError(f"days must be an int, not {type(days).__name__}")
    bs = _as_bs(date)
    start = bs_to_ad(*bs, allow_disputed=allow_disputed)
    cal = _calendar()
    offset = (start - cal.epoch_ad).days + days
    if not 0 <= offset < cal.year_starts[-1]:
        raise DateRangeError(
            f"{days:+d} days from BS {bs} is outside the verified table "
            f"({cal.first_year} to {cal.last_year})"
        )
    return ad_to_bs(cal.epoch_ad + _dt.timedelta(days=offset), allow_disputed=allow_disputed)


def add_months(
    date: BSDate | tuple[int, int, int], months: int, *, allow_disputed: bool = False
) -> BSDate:
    """The same day of the month ``months`` BS months later (earlier, if negative).

    When the target month is shorter, the day is clamped to its last day:
    32 Asar plus one month is the last day of Shrawan. Use ``12 * n`` for
    years. Errors are as for :func:`add_days`.
    """
    if not _is_int(months):
        raise TypeError(f"months must be an int, not {type(months).__name__}")
    bs = _as_bs(date)
    cal = _calendar()
    _check_disputed(cal, bs, allow_disputed)
    index = bs.year * 12 + (bs.month - 1) + months
    year, month = index // 12, index % 12 + 1
    if not cal.first_year <= year <= cal.last_year:
        raise DateRangeError(
            f"{months:+d} months from BS {bs} is outside the verified table "
            f"({cal.first_year} to {cal.last_year})"
        )
    length = cal.months[year][month - 1]
    result = BSDate(year, month, min(bs.day, length))
    _check_disputed(cal, result, allow_disputed)
    if bs.day > length and not allow_disputed and _month_is_disputed(cal, year, month):
        raise DisputedDateError(
            f"BS {bs} {months:+d} months ends in {BS_MONTHS_ROMAN[month - 1]} {year}, whose "
            "length the published calendars disagree on. Pass allow_disputed=True to use "
            "the majority reading. See docs/sources.md."
        )
    return result


def days_between(
    start: BSDate | tuple[int, int, int],
    end: BSDate | tuple[int, int, int],
    *,
    allow_disputed: bool = False,
) -> int:
    """Number of days from ``start`` to ``end``; negative if ``end`` is earlier."""
    first = bs_to_ad(*_as_bs(start), allow_disputed=allow_disputed)
    last = bs_to_ad(*_as_bs(end), allow_disputed=allow_disputed)
    return (last - first).days


def difference(
    start: BSDate | tuple[int, int, int],
    end: BSDate | tuple[int, int, int],
    *,
    allow_disputed: bool = False,
) -> BSDifference:
    """Whole BS years, months and remaining days from ``start`` to ``end``.

    Months are counted on the BS calendar with :func:`add_months` (so a day
    that does not exist in a later month is clamped), and the days are what
    is left after the last whole month. ``end`` must not be before ``start``.
    The disputed span is refused for either date, and also when the last
    whole month ends inside it, because the day count would then be unsure.
    """
    first, last = _as_bs(start), _as_bs(end)
    if last < first:
        raise ValueError(f"the end date BS {last} is before the start date BS {first}")
    cal = _calendar()
    _check_disputed(cal, first, allow_disputed)
    _check_disputed(cal, last, allow_disputed)
    months = (last.year - first.year) * 12 + (last.month - first.month)
    anchor = add_months(first, months, allow_disputed=True)
    if anchor > last:
        months -= 1
        anchor = add_months(first, months, allow_disputed=True)
    _check_disputed(cal, anchor, allow_disputed)
    days = days_between(anchor, last, allow_disputed=True)
    return BSDifference(months // 12, months % 12, days)


def age(
    birth: BSDate | tuple[int, int, int],
    on: BSDate | tuple[int, int, int] | None = None,
    *,
    allow_disputed: bool = False,
) -> int:
    """Completed years from a BS date of birth to ``on`` (default: today in Nepal).

    Someone born on a day that does not exist in a later year's month (for
    example the 32nd) completes the year on that month's last day.
    """
    today = today_bs() if on is None else on
    return difference(birth, today, allow_disputed=allow_disputed).years


def month_calendar(year: int, month: int, *, allow_disputed: bool = False) -> list[list[int]]:
    """Weeks of a BS month as rows of seven day numbers, Sunday first.

    Days outside the month are ``0``, like :func:`calendar.monthcalendar`.
    Baishakh and Jestha 2062 raise :class:`DisputedDateError` unless
    ``allow_disputed`` is true, because their weekdays depend on the reading.
    """
    cal = _check_year_month(year, month)
    length = cal.months[year][month - 1]
    if not allow_disputed and _month_is_disputed(cal, year, month):
        raise DisputedDateError(
            f"{BS_MONTHS_ROMAN[month - 1]} {year} is a month whose length the published "
            "calendars disagree on. Pass allow_disputed=True to use the majority reading. "
            "See docs/sources.md."
        )
    lead = (bs_to_ad(year, month, 1, allow_disputed=True).weekday() + 1) % 7
    cells = [0] * lead + list(range(1, length + 1))
    cells += [0] * (-len(cells) % 7)
    return [cells[i : i + 7] for i in range(0, len(cells), 7)]


def format_month_calendar(
    year: int, month: int, *, devanagari: bool = False, allow_disputed: bool = False
) -> str:
    """A month as plain text: a title, a weekday row and one row per week.

    Columns are separated by tabs so they line up whatever the font does with
    Devanagari. The weekday row uses the first three letters of the romanised
    names, or the Nepali names without ``बार``.
    """
    weeks = month_calendar(year, month, allow_disputed=allow_disputed)
    title = f"{month_name(month, roman=not devanagari)} {year}"
    if devanagari:
        head = [name.removesuffix("बार") for name in WEEKDAYS]
    else:
        head = [name[:3] for name in WEEKDAYS_ROMAN]
    rows = ["\t".join(str(day) if day else "" for day in week).rstrip("\t") for week in weeks]
    out = "\n".join([title, "\t".join(head), *rows])
    return to_devanagari_digits(out) if devanagari else out
