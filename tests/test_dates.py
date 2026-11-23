from __future__ import annotations

import datetime as dt
import json
from importlib import resources
from typing import Any

import pytest

import aksharkit
from aksharkit import BSDate, DateRangeError, DisputedDateError, dates
from aksharkit.cli import main

FIRST_AD = dt.date(1943, 4, 14)
LAST_AD = dt.date(2027, 4, 13)
ONE_DAY = dt.timedelta(days=1)


def _table() -> dict[str, Any]:
    raw = (resources.files("aksharkit") / "data" / "bs_calendar.json").read_text("utf-8")
    loaded: dict[str, Any] = json.loads(raw)
    return loaded


TABLE = _table()
ANCHORS = [(tuple(a["bs"]), a["ad"], a.get("weekday")) for a in TABLE["anchors"]]

# --- the data table itself ----------------------------------------------------


def test_table_is_verified_and_lists_its_sources() -> None:
    assert TABLE["status"] == "verified"
    assert len(TABLE["sources"]) >= 2
    for source in TABLE["sources"]:
        assert source["url"].startswith("https://")
        assert source["licence"]
        assert source["fetched"]
    independent = [s for s in TABLE["sources"] if "independence" not in s]
    assert len(independent) >= 2


def test_table_shape() -> None:
    calendar = dates.load_calendar()
    assert sorted(calendar) == list(range(2000, 2084))
    for year, months in calendar.items():
        assert len(months) == 12, year
        assert all(29 <= n <= 32 for n in months), year
        assert sum(months) in (365, 366), year
        assert dates.days_in_year(year) == sum(months)


def test_month_length_patterns_seen_in_the_table() -> None:
    # First six months are the long ones, the last six the short ones.
    for year, months in dates.load_calendar().items():
        assert all(n >= 30 for n in months[:6]), year
        assert all(n <= 31 for n in months[6:]), year


def test_supported_range() -> None:
    assert dates.supported_range() == (FIRST_AD, LAST_AD)
    total = sum(sum(m) for m in dates.load_calendar().values())
    assert (LAST_AD - FIRST_AD).days + 1 == total


def test_load_calendar_returns_a_copy() -> None:
    calendar = dates.load_calendar()
    calendar.clear()
    assert dates.load_calendar()


# --- anchors: date pairs taken from sources outside the table -----------------


@pytest.mark.parametrize(("bs", "ad", "weekday"), ANCHORS)
def test_anchor_pairs(bs: tuple[int, int, int], ad: str, weekday: str | None) -> None:
    gregorian = dt.date.fromisoformat(ad)
    assert dates.bs_to_ad(*bs) == gregorian
    assert dates.ad_to_bs(gregorian) == BSDate(*bs)
    if weekday is not None:
        assert gregorian.strftime("%A") == weekday


def test_there_are_enough_anchors_and_they_span_the_table() -> None:
    years = sorted(bs[0] for bs, _, _ in ANCHORS)
    assert len(ANCHORS) >= 6
    assert years[0] == 2000
    assert years[-1] == 2083


# --- round trips ---------------------------------------------------------------


def test_every_day_in_range_round_trips_and_advances_by_one() -> None:
    day = FIRST_AD
    previous: BSDate | None = None
    count = 0
    while day <= LAST_AD:
        bs = dates.ad_to_bs(day, allow_disputed=True)
        assert dates.bs_to_ad(*bs, allow_disputed=True) == day
        assert dates.is_valid_bs(*bs)
        if previous is not None:
            assert bs > previous
            if bs.day != 1:
                assert bs == BSDate(previous.year, previous.month, previous.day + 1)
            elif bs.month != 1:
                assert (bs.year, bs.month) == (previous.year, previous.month + 1)
                assert previous.day == dates.days_in_month(previous.year, previous.month)
            else:
                assert (bs.year, previous.month, previous.day) == (
                    previous.year + 1,
                    12,
                    dates.days_in_month(previous.year, 12),
                )
        previous = bs
        day += ONE_DAY
        count += 1
    assert count == 30681
    assert previous == BSDate(2083, 12, 30)


def test_every_bs_date_in_the_table_round_trips() -> None:
    count = 0
    for year, months in dates.load_calendar().items():
        for month, length in enumerate(months, start=1):
            for day in range(1, length + 1):
                ad = dates.bs_to_ad(year, month, day, allow_disputed=True)
                assert dates.ad_to_bs(ad, allow_disputed=True) == (year, month, day)
                count += 1
    assert count == 30681


@pytest.mark.parametrize("year", range(2000, 2084))
def test_new_year_falls_in_mid_april(year: int) -> None:
    new_year = dates.bs_to_ad(year, 1, 1)
    assert new_year.year == year - 57
    assert new_year.month == 4
    assert 12 <= new_year.day <= 15


# --- boundaries and leap handling ----------------------------------------------


def test_first_and_last_days() -> None:
    assert dates.ad_to_bs(FIRST_AD) == (2000, 1, 1)
    assert dates.ad_to_bs(LAST_AD) == (2083, 12, 30)
    assert dates.bs_to_ad(2000, 1, 1) == FIRST_AD
    assert dates.bs_to_ad(2083, 12, 30) == LAST_AD


@pytest.mark.parametrize("day", [FIRST_AD - ONE_DAY, LAST_AD + ONE_DAY, dt.date(1900, 1, 1)])
def test_ad_outside_range(day: dt.date) -> None:
    with pytest.raises(DateRangeError, match="outside the verified table"):
        dates.ad_to_bs(day)


@pytest.mark.parametrize("year", [1999, 2084, 0, -2080, 20830])
def test_bs_year_outside_range(year: int) -> None:
    with pytest.raises(DateRangeError, match="outside the verified table"):
        dates.bs_to_ad(year, 1, 1)
    assert not dates.is_valid_bs(year, 1, 1)


@pytest.mark.parametrize(
    "leap_day", [dt.date(1944, 2, 29), dt.date(2000, 2, 29), dt.date(2024, 2, 29)]
)
def test_gregorian_leap_days(leap_day: dt.date) -> None:
    bs = dates.ad_to_bs(leap_day)
    assert dates.bs_to_ad(*bs) == leap_day
    assert dates.ad_to_bs(leap_day + ONE_DAY) > bs
    assert dates.bs_to_ad(*dates.ad_to_bs(leap_day - ONE_DAY)) == leap_day - ONE_DAY


def test_bs_years_of_366_days_exist_and_convert() -> None:
    long_years = [y for y in range(2000, 2084) if dates.days_in_year(y) == 366]
    assert long_years
    for year in long_years:
        last = dates.days_in_month(year, 12)
        gap = dates.bs_to_ad(year, 12, last) - dates.bs_to_ad(year, 1, 1)
        assert gap.days == 365


def test_a_32_day_month() -> None:
    assert dates.days_in_month(2083, 3) == 32
    assert dates.bs_to_ad(2083, 3, 32) + ONE_DAY == dates.bs_to_ad(2083, 4, 1)


def test_datetime_is_accepted() -> None:
    assert dates.ad_to_bs(dt.datetime(2026, 11, 23, 23, 59)) == (2083, 8, 7)


# --- invalid input ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "month", "day"),
    [(2083, 0, 1), (2083, 13, 1), (2083, 1, 0), (2083, 1, 32), (2083, 2, 32), (2083, 12, 31)],
)
def test_invalid_bs_dates(year: int, month: int, day: int) -> None:
    assert not dates.is_valid_bs(year, month, day)
    with pytest.raises(DateRangeError):
        dates.bs_to_ad(year, month, day)


def test_wrong_types() -> None:
    with pytest.raises(TypeError):
        dates.bs_to_ad("2083", 1, 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        dates.bs_to_ad(2083, 1, True)
    with pytest.raises(TypeError):
        dates.bs_to_ad(2083, 1.0, 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        dates.ad_to_bs("2026-11-23")  # type: ignore[arg-type]
    assert not dates.is_valid_bs(2083, 1, True)
    assert not dates.is_valid_bs("2083", 1, 1)  # type: ignore[arg-type]


def test_range_errors_are_value_errors() -> None:
    assert issubclass(DateRangeError, ValueError)
    assert issubclass(DisputedDateError, ValueError)


# --- the disputed span of 2062 ----------------------------------------------------


def test_disputed_span_is_refused_by_default() -> None:
    for day in (dt.date(2005, 5, 14), dt.date(2005, 5, 30), dt.date(2005, 6, 14)):
        with pytest.raises(DisputedDateError, match="disagree"):
            dates.ad_to_bs(day)
    for bs in ((2062, 2, 1), (2062, 2, 23), (2062, 2, 32)):
        with pytest.raises(DisputedDateError):
            dates.bs_to_ad(*bs)


def test_disputed_span_uses_majority_reading_when_allowed() -> None:
    assert dates.ad_to_bs(dt.date(2005, 5, 14), allow_disputed=True) == (2062, 2, 1)
    assert dates.ad_to_bs(dt.date(2005, 6, 6), allow_disputed=True) == (2062, 2, 24)
    assert dates.bs_to_ad(2062, 2, 32, allow_disputed=True) == dt.date(2005, 6, 14)


def test_days_around_the_disputed_span_are_not_affected() -> None:
    assert dates.ad_to_bs(dt.date(2005, 5, 13)) == (2062, 1, 30)
    assert dates.ad_to_bs(dt.date(2005, 6, 15)) == (2062, 3, 1)
    assert dates.bs_to_ad(2062, 1, 1) == dt.date(2005, 4, 14)


def test_disputed_span_matches_the_table_note() -> None:
    (span,) = TABLE["disputed"]
    assert span["from"] == [2062, 1, 31]
    assert span["to"] == [2062, 2, 32]
    blocked = 0
    day = dt.date(2005, 4, 1)
    while day < dt.date(2005, 7, 1):
        try:
            dates.ad_to_bs(day)
        except DisputedDateError:
            blocked += 1
        day += ONE_DAY
    assert blocked == 32


# --- names, parsing, formatting ---------------------------------------------------


def test_names() -> None:
    assert len(dates.BS_MONTHS) == len(set(dates.BS_MONTHS)) == 12
    assert len(dates.BS_MONTHS_ROMAN) == len(set(dates.BS_MONTHS_ROMAN)) == 12
    assert len(dates.WEEKDAYS) == len(set(dates.WEEKDAYS)) == 7
    assert len(dates.WEEKDAYS_ROMAN) == len(set(dates.WEEKDAYS_ROMAN)) == 7
    assert dates.month_name(1) == "वैशाख"
    assert dates.month_name(8, roman=True) == "Mangsir"
    assert dates.month_name(12) == "चैत"
    for bad in (0, 13, True):
        with pytest.raises(DateRangeError):
            dates.month_name(bad)


def test_weekday_names() -> None:
    monday = dt.date(2026, 11, 23)
    assert dates.weekday_name(monday) == "सोमबार"
    assert dates.weekday_name(monday, roman=True) == "Sombar"
    assert dates.weekday_name(BSDate(2083, 8, 7)) == "सोमबार"
    assert dates.weekday_name(BSDate(2083, 1, 1), roman=True) == "Mangalbar"
    week = [dates.weekday_name(dt.date(2026, 11, 22) + i * ONE_DAY) for i in range(7)]
    assert tuple(week) == dates.WEEKDAYS


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2083-08-07", (2083, 8, 7)),
        ("2083/8/7", (2083, 8, 7)),
        ("2083.08.07", (2083, 8, 7)),
        ("२०८३-०८-०७", (2083, 8, 7)),
        ("  २०७२/६/३ ", (2072, 6, 3)),
    ],
)
def test_parse_bs(text: str, expected: tuple[int, int, int]) -> None:
    parsed = dates.parse_bs(text)
    assert parsed == expected
    assert isinstance(parsed, BSDate)


@pytest.mark.parametrize("text", ["", "2083", "2083-08", "83-08-07", "2083-08-07-01", "abc"])
def test_parse_bs_rejects_other_shapes(text: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        dates.parse_bs(text)


@pytest.mark.parametrize("text", ["2083-13-01", "2083-02-32", "2099-01-01", "2083-00-10"])
def test_parse_bs_rejects_dates_that_do_not_exist(text: str) -> None:
    with pytest.raises(DateRangeError):
        dates.parse_bs(text)


def test_format_bs() -> None:
    bs = BSDate(2083, 8, 7)
    assert str(bs) == "2083-08-07"
    assert dates.format_bs(bs) == "2083-08-07"
    assert dates.format_bs(bs, devanagari=True) == "२०८३-०८-०७"
    assert dates.format_bs(bs, "long") == "2083 Mangsir 7"
    assert dates.format_bs(bs, "long", devanagari=True) == "२०८३ मंसिर ७"
    assert dates.format_bs(bs, "full") == "2083 Mangsir 7, Sombar"
    assert dates.format_bs(bs, "full", devanagari=True) == "२०८३ मंसिर ७, सोमबार"
    assert dates.format_bs((2000, 1, 1), "long") == "2000 Baishakh 1"
    with pytest.raises(ValueError, match="unknown style"):
        dates.format_bs(bs, "short")
    with pytest.raises(DateRangeError):
        dates.format_bs((2083, 2, 32))


@pytest.mark.parametrize(
    ("bs", "expected"),
    [
        ((2083, 4, 1), "2083/84"),
        ((2083, 3, 32), "2082/83"),
        ((2083, 8, 7), "2083/84"),
        ((2083, 12, 30), "2083/84"),
        ((2083, 1, 1), "2082/83"),
        ((2000, 1, 1), "1999/00"),
        ((2000, 4, 1), "2000/01"),
        ((2099 - 16, 5, 1), "2083/84"),
    ],
)
def test_fiscal_year(bs: tuple[int, int, int], expected: str) -> None:
    assert dates.fiscal_year(BSDate(*bs)) == expected


def test_fiscal_year_from_gregorian_and_in_devanagari() -> None:
    assert dates.fiscal_year(dt.date(2026, 11, 23)) == "2083/84"
    assert dates.fiscal_year(dt.date(2026, 7, 16)) == "2082/83"
    assert dates.fiscal_year(dt.date(2026, 7, 17)) == "2083/84"
    assert dates.fiscal_year(BSDate(2083, 8, 7), devanagari=True) == "२०८३/८४"
    with pytest.raises(DateRangeError):
        dates.fiscal_year(BSDate(2083, 2, 32))


def test_today_bs_is_in_range(monkeypatch: pytest.MonkeyPatch) -> None:
    today = dates.today_bs()
    assert dates.is_valid_bs(*today)

    class Fixed(dt.datetime):
        @classmethod
        def now(cls, tz: dt.tzinfo | None = None) -> Fixed:
            # 18:30 UTC is already the next day in Nepal (UTC+05:45).
            return cls(2026, 11, 22, 18, 30, tzinfo=dt.timezone.utc).astimezone(tz)

    monkeypatch.setattr(dt, "datetime", Fixed)
    assert dates.today_bs() == (2083, 8, 7)


def test_top_level_exports() -> None:
    assert aksharkit.bs_to_ad(2083, 8, 7) == dt.date(2026, 11, 23)
    assert aksharkit.ad_to_bs(dt.date(2026, 11, 23)) == (2083, 8, 7)
    assert aksharkit.parse_bs("2083-08-07") == aksharkit.BSDate(2083, 8, 7)
    assert aksharkit.format_bs((2083, 8, 7), "long") == "2083 Mangsir 7"
    assert aksharkit.fiscal_year(dt.date(2026, 11, 23)) == "2083/84"


# --- command line ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["date", "2026-11-23"], "2083-08-07"),
        (["date", "२०२६-११-२३"], "2083-08-07"),
        (["date", "--devanagari", "2026-11-23"], "२०८३-०८-०७"),
        (["date", "--style", "long", "2026-11-23"], "2083 Mangsir 7"),
        (["date", "--style", "full", "--devanagari", "2026-11-23"], "२०८३ मंसिर ७, सोमबार"),
        (["date", "--to", "ad", "2083-08-07"], "2026-11-23"),
        (["date", "--to", "ad", "२०७२/६/३"], "2015-09-20"),
        (["date", "--to", "ad", "--style", "long", "2083-01-01"], "14 April 2026"),
        (["date", "--to", "ad", "--style", "full", "2083-01-01"], "14 April 2026, Tuesday"),
        (["date", "--fiscal-year", "2026-11-23"], "2083/84"),
        (["date", "--to", "ad", "--fiscal-year", "--devanagari", "2083-03-15"], "२०८२/८३"),
        (["date", "--allow-disputed", "2005-06-06"], "2062-02-24"),
    ],
)
def test_cli_date(argv: list[str], expected: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 0
    assert capsys.readouterr().out == expected + "\n"


def test_cli_date_defaults_to_today(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["date"]) == 0
    assert capsys.readouterr().out.strip() == str(dates.today_bs())


@pytest.mark.parametrize(
    "argv",
    [
        ["date", "2027-04-14"],
        ["date", "1943-04-13"],
        ["date", "23/11/2026"],
        ["date", "2005-05-20"],
        ["date", "--to", "ad", "2083-02-32"],
        ["date", "--to", "ad", "2084-01-01"],
        ["date", "--to", "ad"],
        ["date", "--to", "ad", "2062-02-10"],
    ],
)
def test_cli_date_errors_exit_2(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("aksharkit: error:")
