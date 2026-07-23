"""The acting user's identity must never be an LLM-visible tool argument.

Each tool resolves `user_id` internally via `get_user_id()`, so no tool's
`args`/`args_schema` may expose it; otherwise the model could try to set it
and impersonate another user.
"""
import datetime as dt
import uuid

from app.adapters.agent.tools import make_tools
from app.domain.entities import Room
from app.domain.services.booking_service import BookingService
from tests.fakes import (
    FixedClock,
    InMemoryBookingRepository,
    InMemoryRoomCatalog,
    SpyMetrics,
)

ROOMS = [Room("A", 4), Room("B", 6), Room("C", 6), Room("D", 8), Room("E", 10)]
NOW = dt.datetime(2026, 7, 20, 12, tzinfo=dt.timezone.utc)
FORBIDDEN_FIELD = "user_id"


def _service() -> BookingService:
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


def test_no_tool_exposes_user_id() -> None:
    tools = make_tools(_service(), uuid.uuid4)
    assert tools, "expected the agent to expose at least one tool"
    for tool in tools:
        assert FORBIDDEN_FIELD not in tool.args, f"{tool.name} exposes {FORBIDDEN_FIELD} in args"
        schema = tool.args_schema
        fields = getattr(schema, "model_fields", {}) if schema is not None else {}
        assert FORBIDDEN_FIELD not in fields, (
            f"{tool.name}.args_schema exposes {FORBIDDEN_FIELD}"
        )
