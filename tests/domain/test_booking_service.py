"""Tests for `BookingService`, exercised through in-memory fakes."""
import datetime as dt
import uuid

import pytest

from app.domain.entities import Room
from app.domain.errors import CapacityExceeded, NotOwner, OutOfHours, Overlap, RoomNotFound
from app.domain.services.booking_service import BookingService
from tests.fakes import FixedClock, InMemoryBookingRepository, InMemoryRoomCatalog, SpyMetrics

TZ = "America/Montevideo"
OPEN, CLOSE = dt.time(8, 0), dt.time(20, 0)
NOW = dt.datetime(2026, 7, 20, 12, 0, tzinfo=dt.timezone.utc)  # lunes, antes de la fecha de test
ROOMS = [Room("A", 4), Room("B", 6), Room("C", 6), Room("D", 8), Room("E", 10)]
D = dt.date(2026, 7, 21)


def make() -> BookingService:
    """Build a `BookingService` wired with in-memory fakes."""
    return make_with_metrics(SpyMetrics())


def make_with_metrics(metrics: SpyMetrics) -> BookingService:
    """Build a `BookingService` over in-memory fakes with the given metrics spy."""
    return BookingService(
        InMemoryBookingRepository(), InMemoryRoomCatalog(ROOMS), FixedClock(NOW), metrics, TZ,
        OPEN, CLOSE,
    )


def test_create_ok() -> None:
    svc = make()
    owner = uuid.uuid4()
    booking = svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 30), "Sprint", 6)
    assert booking.room_code == "C"
    assert booking.owner_id == owner


def test_create_overlap() -> None:
    svc = make()
    owner = uuid.uuid4()
    svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 0), "x", 2)
    with pytest.raises(Overlap):
        svc.create(owner, "C", D, dt.time(10, 30), dt.time(11, 30), "y", 2)


def test_create_capacity() -> None:
    with pytest.raises(CapacityExceeded):
        make().create(uuid.uuid4(), "A", D, dt.time(10, 0), dt.time(11, 0), "x", 5)


def test_create_unknown_room() -> None:
    with pytest.raises(RoomNotFound):
        make().create(uuid.uuid4(), "Z", D, dt.time(10, 0), dt.time(11, 0), "x", 1)


def test_cancel_not_owner() -> None:
    svc = make()
    owner, other = uuid.uuid4(), uuid.uuid4()
    booking = svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 0), "x", 1)
    with pytest.raises(NotOwner):
        svc.cancel(other, booking.id)


def test_availability_filters_capacity_and_overlap() -> None:
    svc = make()
    owner = uuid.uuid4()
    svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 0), "x", 2)
    free = {room.code for room in svc.availability(D, dt.time(10, 0), dt.time(11, 0), 6)}
    assert "C" not in free  # ocupada
    assert "A" not in free  # capacidad 4 < 6
    assert {"B", "D", "E"} <= free


def test_availability_rejects_slots_outside_operating_hours() -> None:
    with pytest.raises(OutOfHours):
        make().availability(D, dt.time(7, 30), dt.time(8, 0), 2)


def test_schedule_free_blocks() -> None:
    svc = make()
    owner = uuid.uuid4()
    svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 30), "x", 2)
    schedule = svc.schedule("C", D)
    assert len(schedule["occupied"]) == 1
    assert (dt.time(8, 0), dt.time(10, 0)) in schedule["free"]


def test_create_records_booking_created() -> None:
    metrics = SpyMetrics()
    make_with_metrics(metrics).create(uuid.uuid4(), "C", D, dt.time(10, 0), dt.time(11, 0), "x", 2)
    assert metrics.created == 1
    assert metrics.overlaps == 0


def test_overlap_records_overlap_rejected() -> None:
    metrics = SpyMetrics()
    svc = make_with_metrics(metrics)
    owner = uuid.uuid4()
    svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 0), "x", 2)
    with pytest.raises(Overlap):
        svc.create(owner, "C", D, dt.time(10, 30), dt.time(11, 30), "y", 2)
    assert metrics.overlaps == 1
    assert metrics.created == 1  # only the first booking succeeded


def test_cancel_records_booking_cancelled() -> None:
    metrics = SpyMetrics()
    svc = make_with_metrics(metrics)
    owner = uuid.uuid4()
    booking = svc.create(owner, "C", D, dt.time(10, 0), dt.time(11, 0), "x", 2)
    svc.cancel(owner, booking.id)
    assert metrics.cancelled == 1
