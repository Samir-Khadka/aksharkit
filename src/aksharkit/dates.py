"""Bikram Sambat (BS) and Gregorian (AD) date conversion. NOT IMPLEMENTED YET.

BS month lengths are published, not computed: each year's twelve lengths
come from the official calendar. The table lives in ``data/bs_calendar.json``
and is currently empty. It will not be guessed. Until it is filled from a
trusted source and cross-checked against known date pairs, every function
here raises :class:`aksharkit.DataNotVerifiedError`.
"""

from __future__ import annotations

import datetime as _dt

from ._data import load_table, require_verified

__all__ = ["BS_MONTHS", "ad_to_bs", "bs_to_ad", "load_calendar"]

#: Names of the twelve BS months, Baishakh first. (Names only; no lengths.)
BS_MONTHS: tuple[str, ...] = (
    "वैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज",
    "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत",
)  # fmt: skip


def load_calendar() -> dict[int, tuple[int, ...]]:
    """Return ``{bs_year: (twelve month lengths)}`` from the verified table.

    Raises :class:`aksharkit.DataNotVerifiedError` while the table is empty
    or unverified.
    """
    table = load_table("bs_calendar")
    years = require_verified(table, "BS/AD date conversion", "years")
    calendar: dict[int, tuple[int, ...]] = {}
    for year, lengths in years.items():
        months = tuple(int(n) for n in lengths)
        if len(months) != 12 or not all(29 <= n <= 32 for n in months):
            raise ValueError(f"BS calendar table is malformed for year {year}")
        calendar[int(year)] = months
    return calendar


def bs_to_ad(year: int, month: int, day: int) -> _dt.date:
    """Convert a BS date to a Gregorian date. Not implemented yet."""
    load_calendar()
    raise NotImplementedError(  # pragma: no cover - reachable only with verified data
        "BS to AD conversion is not implemented yet"
    )


def ad_to_bs(date: _dt.date) -> tuple[int, int, int]:
    """Convert a Gregorian date to ``(bs_year, bs_month, bs_day)``. Not implemented yet."""
    load_calendar()
    raise NotImplementedError(  # pragma: no cover - reachable only with verified data
        "AD to BS conversion is not implemented yet"
    )
