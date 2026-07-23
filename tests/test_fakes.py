"""Tests for the in-memory test fakes backing the domain ports."""
import datetime as dt
import uuid

from app.domain.entities import Booking
from tests.fakes import FixedClock, InMemoryBookingRepository


def test_repo_roundtrip() -> None:
    repo = InMemoryBookingRepository()
    utc = dt.timezone.utc
    b = Booking(
        room_code="C",
        owner_id=uuid.uuid4(),
        starts_at=dt.datetime(2026, 7, 21, 10, tzinfo=utc),
        ends_at=dt.datetime(2026, 7, 21, 11, tzinfo=utc),
        title="x",
        attendees=1,
    )
    saved = repo.add(b)
    assert repo.get(saved.id) == saved
    assert repo.list_by_owner(b.owner_id) == [saved]


def test_fixed_clock() -> None:
    now = dt.datetime(2026, 7, 21, 9, tzinfo=dt.timezone.utc)
    assert FixedClock(now).now() == now
