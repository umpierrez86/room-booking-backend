"""Tests for pure slot/attendee validation rules."""
import datetime as dt

import pytest

from app.domain import rules
from app.domain.errors import (
    CapacityExceeded,
    EndBeforeStart,
    InvalidAttendees,
    InvalidDuration,
    NotAWeekday,
    NotOnGrid,
    OutOfHours,
)

TZ = "America/Montevideo"
OPEN, CLOSE = dt.time(8, 0), dt.time(20, 0)
D = dt.date(2026, 7, 21)  # martes


@pytest.mark.parametrize(
    "start,end,exc",
    [
        (dt.time(10, 15), dt.time(11, 0), NotOnGrid),
        (dt.time(11, 0), dt.time(10, 0), EndBeforeStart),
        (dt.time(10, 0), dt.time(13, 30), InvalidDuration),  # 3.5h > 180
        (dt.time(7, 30), dt.time(8, 0), OutOfHours),
        (dt.time(19, 30), dt.time(20, 30), OutOfHours),
    ],
)
def test_slot_invalid(start: dt.time, end: dt.time, exc: type[Exception]) -> None:
    with pytest.raises(exc):
        rules.validate_slot(D, start, end, TZ, OPEN, CLOSE)


def test_slot_valid() -> None:
    rules.validate_slot(D, dt.time(10, 0), dt.time(11, 30), TZ, OPEN, CLOSE)  # no raise


def test_weekend_rejected() -> None:
    with pytest.raises(NotAWeekday):
        rules.validate_slot(
            dt.date(2026, 7, 25), dt.time(10, 0), dt.time(11, 0), TZ, OPEN, CLOSE
        )


@pytest.mark.parametrize("n,cap,exc", [(0, 6, InvalidAttendees), (7, 6, CapacityExceeded)])
def test_attendees_invalid(n: int, cap: int, exc: type[Exception]) -> None:
    with pytest.raises(exc):
        rules.validate_attendees(n, cap)


def test_attendees_valid() -> None:
    rules.validate_attendees(6, 6)
