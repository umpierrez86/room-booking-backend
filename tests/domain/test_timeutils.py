"""Tests for pure time-grid helpers used by domain rules."""
import datetime as dt

from app.domain.timeutils import format_hhmm, is_on_grid, is_weekday, parse_hhmm, within_hours


def test_on_grid() -> None:
    assert is_on_grid(dt.time(10, 0)) and is_on_grid(dt.time(10, 30))
    assert not is_on_grid(dt.time(10, 15))


def test_weekday() -> None:
    assert is_weekday(dt.date(2026, 7, 21))  # martes
    assert not is_weekday(dt.date(2026, 7, 25))  # sábado


def test_within_hours() -> None:
    assert within_hours(dt.time(8, 0), dt.time(8, 0), dt.time(20, 0))
    assert not within_hours(dt.time(20, 30), dt.time(8, 0), dt.time(20, 0))


def test_hhmm_roundtrip() -> None:
    assert parse_hhmm("08:30") == dt.time(8, 30)
    assert format_hhmm(dt.time(8, 30)) == "08:30"
