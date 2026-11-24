"""Date arithmetic on the verified table, checked against the AD calendar."""

from __future__ import annotations

import datetime as dt
import random

import pytest

from aksharkit import (
    BSDate,
    BSDifference,
    DateRangeError,
    DisputedDateError,
    ad_to_bs,
    add_days,
    add_months,
    age,
    bs_to_ad,
    dates,
    days_between,
    days_in_month,
    difference,
    format_month_calendar,
    month_calendar,
)

FIRST_AD, LAST_AD = dates.supported_range()
FIRST_BS, LAST_BS = BSDate(2000, 1, 1), BSDate(2083, 12, 30)
SPAN_START, SPAN_END = BSDate(2062, 1, 31), BSDate(2062, 2, 32)


def _random_ad(rng: random.Random) -> dt.date:
    return FIRST_AD + dt.timedelta(days=rng.randrange((LAST_AD - FIRST_AD).days + 1))


def test_range_constants_match_the_table() -> None:
    assert ad_to_bs(FIRST_AD) == FIRST_BS
    assert ad_to_bs(LAST_AD) == LAST_BS


# --- add_days and days_between -------------------------------------------------


def test_add_days_matches_ad_arithmetic() -> None:
    rng = random.Random(1)
    for _ in range(5_000):
        start = _random_ad(rng)
        step = rng.randint(-4_000, 4_000)
        target = start + dt.timedelta(days=step)
        bs = ad_to_bs(start, allow_disputed=True)
        if FIRST_AD <= target <= LAST_AD:
            result = add_days(bs, step, allow_disputed=True)
            assert bs_to_ad(*result, allow_disputed=True) == target
            assert days_between(bs, result, allow_disputed=True) == step
            assert days_between(result, bs, allow_disputed=True) == -step
        else:
            with pytest.raises(DateRangeError):
                add_days(bs, step, allow_disputed=True)


def test_add_one_day_walks_every_date_in_the_table() -> None:
    bs = FIRST_BS
    count = 0
    while bs != LAST_BS:
        following = add_days(bs, 1, allow_disputed=True)
        assert following > bs
        assert following.day == bs.day + 1 or following.day == 1
        bs = following
        count += 1
    assert count == (LAST_AD - FIRST_AD).days


def test_add_days_basics() -> None:
    assert add_days(BSDate(2083, 8, 7), 0) == BSDate(2083, 8, 7)
    assert add_days((2083, 8, 7), 30) == BSDate(2083, 9, 8)
    assert add_days(BSDate(2083, 1, 1), -1) == BSDate(2082, 12, 30)
    assert isinstance(add_days((2083, 8, 7), 1), BSDate)
    assert days_between((2083, 1, 1), (2083, 8, 7)) == 223
    assert days_between(FIRST_BS, LAST_BS) == (LAST_AD - FIRST_AD).days


def test_add_days_range_and_type_errors() -> None:
    with pytest.raises(DateRangeError, match="outside the verified table"):
        add_days(LAST_BS, 1)
    with pytest.raises(DateRangeError, match="outside the verified table"):
        add_days(FIRST_BS, -1)
    with pytest.raises(DateRangeError):
        add_days((2083, 8, 30), 1)  # Mangsir 2083 has 29 days
    for bad in (1.5, "1", None, True):
        with pytest.raises(TypeError):
            add_days(FIRST_BS, bad)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            add_months(FIRST_BS, bad)  # type: ignore[arg-type]


# --- add_months ----------------------------------------------------------------


def test_add_months_keeps_the_day_or_clamps() -> None:
    rng = random.Random(2)
    table = dates.load_calendar()
    for _ in range(5_000):
        bs = ad_to_bs(_random_ad(rng), allow_disputed=True)
        step = rng.randint(-600, 600)
        index = bs.year * 12 + bs.month - 1 + step
        year, month = divmod(index, 12)
        month += 1
        if year not in table:
            with pytest.raises(DateRangeError):
                add_months(bs, step, allow_disputed=True)
            continue
        result = add_months(bs, step, allow_disputed=True)
        assert (result.year, result.month) == (year, month)
        assert result.day == min(bs.day, table[year][month - 1])
        assert dates.is_valid_bs(*result)


def test_add_months_examples() -> None:
    assert add_months((2083, 8, 7), 0) == BSDate(2083, 8, 7)
    assert add_months((2083, 8, 7), 1) == BSDate(2083, 9, 7)
    assert add_months((2083, 8, 7), -8) == BSDate(2082, 12, 7)
    assert add_months((2083, 8, 7), 4) == BSDate(2083, 12, 7)
    assert add_months((2082, 1, 15), 12) == BSDate(2083, 1, 15)
    # 32 Asar 2083 -> Shrawan 2083 has 31 days.
    assert days_in_month(2083, 3) == 32
    assert days_in_month(2083, 4) == 31
    assert add_months((2083, 3, 32), 1) == BSDate(2083, 4, 31)
    with pytest.raises(DateRangeError):
        add_months((2083, 8, 7), 5)
    with pytest.raises(DateRangeError):
        add_months((2000, 1, 1), -1)


# --- difference and age --------------------------------------------------------


def test_difference_rebuilds_the_end_date() -> None:
    rng = random.Random(3)
    for _ in range(5_000):
        a = ad_to_bs(_random_ad(rng), allow_disputed=True)
        b = ad_to_bs(_random_ad(rng), allow_disputed=True)
        start, end = min(a, b), max(a, b)
        gap = difference(start, end, allow_disputed=True)
        assert isinstance(gap, BSDifference)
        assert gap.years >= 0
        assert 0 <= gap.months < 12
        assert 0 <= gap.days < 32
        anchor = add_months(start, gap.years * 12 + gap.months, allow_disputed=True)
        assert add_days(anchor, gap.days, allow_disputed=True) == end
        # One more whole month would overshoot.
        months = gap.years * 12 + gap.months + 1
        index = start.year * 12 + start.month - 1 + months
        if index // 12 <= 2083:
            assert add_months(start, months, allow_disputed=True) > end


def test_difference_examples() -> None:
    assert difference((2083, 8, 7), (2083, 8, 7)) == (0, 0, 0)
    assert difference((2083, 8, 7), (2083, 8, 8)) == (0, 0, 1)
    assert difference((2083, 7, 7), (2083, 8, 7)) == (0, 1, 0)
    assert difference((2082, 8, 7), (2083, 8, 7)) == (1, 0, 0)
    assert difference((2082, 8, 8), (2083, 8, 7)) == (0, 11, days_in_month(2083, 7) - 1)
    assert difference((2059, 5, 12), (2083, 8, 7)) == BSDifference(24, 2, 25)
    with pytest.raises(ValueError, match="before the start date"):
        difference((2083, 8, 8), (2083, 8, 7))


def test_age_matches_a_plain_birthday_rule() -> None:
    rng = random.Random(4)
    table = dates.load_calendar()
    for _ in range(5_000):
        a = ad_to_bs(_random_ad(rng), allow_disputed=True)
        b = ad_to_bs(_random_ad(rng), allow_disputed=True)
        birth, on = min(a, b), max(a, b)
        # Birthday this year, clamped to the month's last day.
        birthday = (birth.month, min(birth.day, table[on.year][birth.month - 1]))
        expected = on.year - birth.year - ((on.month, on.day) < birthday)
        assert age(birth, on, allow_disputed=True) == expected


def test_age_examples(monkeypatch: pytest.MonkeyPatch) -> None:
    assert age((2059, 5, 12), (2083, 8, 7)) == 24
    assert age((2059, 8, 7), (2083, 8, 6)) == 23
    assert age((2059, 8, 7), (2083, 8, 7)) == 24
    assert age((2083, 8, 7), (2083, 8, 7)) == 0
    with pytest.raises(ValueError, match="before the start date"):
        age((2083, 8, 8), (2083, 8, 7))
    monkeypatch.setattr(dates, "today_bs", lambda: BSDate(2083, 8, 8))
    assert age((2060, 8, 8)) == 23


# --- month calendar ------------------------------------------------------------


def test_month_calendar_against_ad_weekdays() -> None:
    for year, row in dates.load_calendar().items():
        for month, length in enumerate(row, start=1):
            weeks = month_calendar(year, month, allow_disputed=True)
            assert all(len(week) == 7 for week in weeks)
            assert 4 <= len(weeks) <= 6
            assert [day for week in weeks for day in week if day] == list(range(1, length + 1))
            assert any(weeks[0]) and any(weeks[-1])
            for week in weeks:
                for column, day in enumerate(week):
                    if day:
                        ad = bs_to_ad(year, month, day, allow_disputed=True)
                        assert (ad.weekday() + 1) % 7 == column  # Sunday is column 0


def test_month_calendar_example() -> None:
    # 1 Mangsir 2083 is Tuesday 17 November 2026.
    assert bs_to_ad(2083, 8, 1) == dt.date(2026, 11, 17)
    assert dt.date(2026, 11, 17).strftime("%A") == "Tuesday"
    assert month_calendar(2083, 8) == [
        [0, 0, 1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10, 11, 12],
        [13, 14, 15, 16, 17, 18, 19],
        [20, 21, 22, 23, 24, 25, 26],
        [27, 28, 29, 0, 0, 0, 0],
    ]


def test_format_month_calendar() -> None:
    text = format_month_calendar(2083, 8)
    lines = text.split("\n")
    assert lines[0] == "Mangsir 2083"
    assert lines[1] == "Aai\tSom\tMan\tBud\tBih\tShu\tSha"
    assert lines[2] == "\t\t1\t2\t3\t4\t5"
    assert lines[-1] == "27\t28\t29"
    assert len(lines) == 7
    nepali = format_month_calendar(2083, 8, devanagari=True).split("\n")
    assert nepali[0] == "मंसिर २०८३"
    assert nepali[1] == "आइत\tसोम\tमङ्गल\tबुध\tबिही\tशुक्र\tशनि"
    assert nepali[2] == "\t\t१\t२\t३\t४\t५"


@pytest.mark.parametrize(("year", "month"), [(1999, 1), (2084, 1), (2083, 0), (2083, 13)])
def test_month_calendar_range(year: int, month: int) -> None:
    with pytest.raises(DateRangeError):
        month_calendar(year, month)
    with pytest.raises(DateRangeError):
        format_month_calendar(year, month)


# --- the disputed span of 2062 ---------------------------------------------------


def test_disputed_span_is_refused_by_default() -> None:
    inside = BSDate(2062, 2, 10)
    with pytest.raises(DisputedDateError):
        add_days(inside, 1)
    with pytest.raises(DisputedDateError):
        add_days((2062, 1, 1), 40)  # lands inside
    with pytest.raises(DisputedDateError):
        add_months(inside, 1)
    with pytest.raises(DisputedDateError):
        add_months((2061, 12, 15), 2)  # lands on 15 Jestha 2062
    with pytest.raises(DisputedDateError):
        days_between(inside, (2063, 1, 1))
    with pytest.raises(DisputedDateError):
        days_between((2061, 1, 1), inside)
    with pytest.raises(DisputedDateError):
        difference(inside, (2063, 1, 1))
    with pytest.raises(DisputedDateError):
        difference((2061, 1, 1), inside)
    with pytest.raises(DisputedDateError):
        age(inside, (2083, 8, 7))
    # The last whole month ends inside the span, so the day count is unsure.
    with pytest.raises(DisputedDateError):
        difference((2060, 1, 31), (2062, 3, 5))
    # Clamping into a month whose length is disputed.
    with pytest.raises(DisputedDateError, match="length"):
        add_months((2062, 3, 31), -2)  # Baishakh 2062: 30 or 31 days?
    for month in (1, 2):
        with pytest.raises(DisputedDateError, match="length"):
            month_calendar(2062, month)
        with pytest.raises(DisputedDateError):
            format_month_calendar(2062, month)


def test_disputed_span_with_the_flag_uses_the_majority_reading() -> None:
    assert add_days((2062, 1, 1), 40, allow_disputed=True) == BSDate(2062, 2, 11)
    assert add_months((2061, 12, 15), 2, allow_disputed=True) == BSDate(2062, 2, 15)
    assert days_between((2062, 2, 1), (2062, 2, 32), allow_disputed=True) == 31
    assert len(month_calendar(2062, 1, allow_disputed=True)) == 5
    assert format_month_calendar(2062, 2, allow_disputed=True).startswith("Jestha 2062")
    assert difference((2060, 1, 31), (2062, 3, 5), allow_disputed=True).years == 2


def test_crossing_the_disputed_span_is_fine() -> None:
    # Both readings give Baishakh + Jestha 2062 the same total, so dates on
    # either side are not affected.
    before, after = BSDate(2062, 1, 30), BSDate(2062, 3, 1)
    assert days_between(before, after) == 33
    assert add_days(before, 33) == after
    assert add_days(after, -33) == before
    assert add_months((2061, 12, 15), 4) == BSDate(2062, 4, 15)
    assert month_calendar(2062, 3)[0].count(0) < 7
    assert month_calendar(2061, 12)
    assert difference((2061, 1, 1), (2063, 1, 1)) == (2, 0, 0)
    assert age((2050, 6, 1), (2083, 8, 7)) == 33
    assert SPAN_START < SPAN_END
