from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

SYDNEY = ZoneInfo("Australia/Sydney")
NEW_YORK = ZoneInfo("America/New_York")


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_sydney(dt: datetime) -> datetime:
    return dt.astimezone(SYDNEY)


def to_new_york(dt: datetime) -> datetime:
    return dt.astimezone(NEW_YORK)


def trade_date_sydney(dt: datetime) -> date:
    """Calendar date in Sydney — used for FX snapping and CGT holding period math."""
    return dt.astimezone(SYDNEY).date()


def financial_year_for(d: date) -> int:
    """AU FY ends 30 June. Returns the FY-end year (e.g. FY2026 = 1 Jul 2025 - 30 Jun 2026)."""
    return d.year if d.month <= 6 else d.year + 1


def financial_year_bounds(fy_end_year: int) -> tuple[date, date]:
    return date(fy_end_year - 1, 7, 1), date(fy_end_year, 6, 30)
