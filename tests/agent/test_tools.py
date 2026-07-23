"""Tests for the agent's LangChain tools, exercised through fakes."""
import datetime as dt
import uuid
from unittest.mock import patch

from app.adapters.agent.tools import make_tools
from app.domain.entities import Room
from app.domain.errors import DomainError
from app.domain.services.booking_service import BookingService
from tests.fakes import FixedClock, InMemoryBookingRepository, InMemoryRoomCatalog, SpyMetrics

ROOMS = [Room("A", 4), Room("B", 6), Room("C", 6), Room("D", 8), Room("E", 10)]
NOW = dt.datetime(2026, 7, 20, 12, tzinfo=dt.timezone.utc)


def make_service() -> BookingService:
    """Build a `BookingService` wired with in-memory fakes."""
    return BookingService(
        InMemoryBookingRepository(),
        InMemoryRoomCatalog(ROOMS),
        FixedClock(NOW),
        SpyMetrics(),
        "America/Montevideo",
        dt.time(8, 0),
        dt.time(20, 0),
    )


def test_create_tool_uses_injected_user() -> None:
    uid = uuid.uuid4()
    svc = make_service()
    tools = {t.name: t for t in make_tools(lambda: svc, lambda: uid)}
    out = tools["create_booking"].invoke(
        {"room": "C", "date": "2026-07-21", "start": "10:00", "end": "11:30", "title": "x", "attendees": 6}
    )
    assert "C" in out and svc.list_by_owner(uid)  # se creó a nombre del user inyectado


def test_create_tool_returns_domain_error_message() -> None:
    svc = make_service()
    tools = {t.name: t for t in make_tools(lambda: svc, lambda: uuid.uuid4())}
    out = tools["create_booking"].invoke(
        {"room": "A", "date": "2026-07-21", "start": "10:00", "end": "11:00", "title": "x", "attendees": 5}
    )
    assert "capacidad" in out.lower()


def test_availability_tool_returns_domain_error_message() -> None:
    svc = make_service()
    tools = {t.name: t for t in make_tools(lambda: svc, lambda: uuid.uuid4())}

    with patch.object(svc, "availability", side_effect=DomainError("El horario ya pasó.")):
        out = tools["list_available_rooms"].invoke(
            {"date": "2026-07-17", "start": "10:00", "end": "11:00", "attendees": 4}
        )

    assert out == "El horario ya pasó."
