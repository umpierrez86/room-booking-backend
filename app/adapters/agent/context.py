"""Resolves the acting user's id from the ambient LangChain run config.

The agent's tools never take `user_id` as an LLM-visible argument: the
identity always comes from the verified JWT (see `deps.get_current_user`),
gets injected into `config["configurable"]` when the graph is invoked, and
is read back here through LangChain's ambient `RunnableConfig` — no
explicit parameter threading needed between the graph and the tools.
"""
import uuid
from typing import Final, Literal, cast

from langchain_core.runnables import ensure_config

from app.domain.services.booking_service import BookingService

# Typed as `Literal` (not plain `str`) so mypy can resolve the exact field
# type of `RunnableConfig.get(CONFIGURABLE_KEY, ...)` instead of widening it.
CONFIGURABLE_KEY: Final[Literal["configurable"]] = "configurable"
USER_ID_KEY = "user_id"
BOOKING_SERVICE_KEY = "booking_service"


def current_user_id() -> uuid.UUID:
    """Return the acting user's id carried by the current run's config."""
    config = ensure_config()
    configurable = config.get(CONFIGURABLE_KEY, {})
    return uuid.UUID(str(configurable[USER_ID_KEY]))


def current_booking_service() -> BookingService:
    """Return the request-scoped `BookingService` carried by the run's config.

    The service is per-request (it wraps a live DB session), so it is passed
    through `config["configurable"]` on each invocation rather than captured
    in a closure — this lets the graph be compiled once and reused, while the
    tools still act through the current request's session.
    """
    config = ensure_config()
    configurable = config.get(CONFIGURABLE_KEY, {})
    return cast("BookingService", configurable[BOOKING_SERVICE_KEY])
