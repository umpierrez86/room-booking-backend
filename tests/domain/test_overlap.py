"""Tests for pure overlap detection between bookings."""
import datetime as dt
import uuid

from app.domain.entities import Booking
from app.domain.overlap import find_overlap


def b(h1: int, h2: int) -> Booking:
    utc = dt.timezone.utc
    return Booking(
        room_code="C",
        owner_id=uuid.uuid4(),
        starts_at=dt.datetime(2026, 7, 21, h1, 0, tzinfo=utc),
        ends_at=dt.datetime(2026, 7, 21, h2, 0, tzinfo=utc),
        title="x",
        attendees=1,
    )


def test_overlaps() -> None:
    assert find_overlap(b(10, 12), [b(11, 13)]) is not None


def test_adjacent_no_overlap() -> None:
    assert find_overlap(b(10, 11), [b(11, 12)]) is None  # bordes tocan, no pisan


def test_no_overlap() -> None:
    assert find_overlap(b(10, 11), [b(12, 13)]) is None
