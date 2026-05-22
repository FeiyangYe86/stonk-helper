from datetime import UTC, date, datetime

from stonk_helper.clock import (
    financial_year_bounds,
    financial_year_for,
    to_new_york,
    to_sydney,
    trade_date_sydney,
)


def test_financial_year_for_boundaries() -> None:
    assert financial_year_for(date(2026, 6, 30)) == 2026
    assert financial_year_for(date(2026, 7, 1)) == 2027
    assert financial_year_for(date(2026, 1, 15)) == 2026
    assert financial_year_for(date(2025, 12, 31)) == 2026


def test_financial_year_bounds() -> None:
    start, end = financial_year_bounds(2026)
    assert start == date(2025, 7, 1)
    assert end == date(2026, 6, 30)


def test_trade_date_sydney_crosses_midnight() -> None:
    # 21:00 UTC on 30 Jun = 07:00 AEST on 1 Jul — the AU FY boundary.
    dt = datetime(2026, 6, 30, 21, 0, tzinfo=UTC)
    assert trade_date_sydney(dt) == date(2026, 7, 1)
    assert financial_year_for(trade_date_sydney(dt)) == 2027


def test_tz_conversion_round_trips() -> None:
    dt = datetime(2026, 5, 21, 14, 30, tzinfo=UTC)
    syd = to_sydney(dt)
    ny = to_new_york(dt)
    assert syd.utcoffset() is not None
    assert ny.utcoffset() is not None
    assert syd.astimezone(UTC) == dt
    assert ny.astimezone(UTC) == dt
