"""LangChain tools exposing `BookingService` to the conversational agent.

Tools never reimplement business rules: every call delegates to
`BookingService`, catching `DomainError` and returning its `message` as
plain text so the LLM can relay it to the user. The acting user's id is
never an LLM-visible argument — each tool obtains it by calling
`get_user_id()`, which resolves the identity carried by the JWT (see
`app.adapters.agent.context.current_user_id`), so the model can never
impersonate another user.

The `BookingService` is likewise resolved on each call via `get_service()`
rather than captured in a closure, so the graph these tools belong to can be
compiled once and reused while each turn still acts through the current
request's DB session (see `app.adapters.agent.context.current_booking_service`).
"""
import datetime as dt
import uuid
from collections.abc import Callable

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.domain import timeutils as tu
from app.domain.entities import Booking
from app.domain.errors import DomainError
from app.domain.services.booking_service import BookingService, RoomSchedule

DEFAULT_ATTENDEES = 1
NO_FREE_ROOMS_LABEL = "ninguna"
NO_OCCUPIED_BLOCKS_LABEL = "nada"
NO_FREE_BLOCKS_LABEL = "nada"
NO_OWN_BOOKINGS_MESSAGE = "No tenés reservas."
BOOKING_CANCELLED_MESSAGE = "Reserva cancelada."
# Shared with `app.adapters.agent.router`, which sniffs these to decide
# whether a `booking_changed` event should be emitted after a tool call.
BOOKING_CREATED_PREFIX = "Reserva creada"

GetUserId = Callable[[], uuid.UUID]
GetService = Callable[[], BookingService]


class CreateBookingInput(BaseModel):
    """Arguments the LLM supplies to create a booking."""

    room: str = Field(description="Código de la sala (A, B, C, D o E).")
    date: str = Field(description="Fecha en formato YYYY-MM-DD.")
    start: str = Field(description="Hora de inicio en formato HH:MM.")
    end: str = Field(description="Hora de fin en formato HH:MM.")
    title: str = Field(description="Título o motivo de la reunión.")
    attendees: int = Field(description="Cantidad de asistentes.")


class AvailabilityInput(BaseModel):
    """Arguments the LLM supplies to search for available rooms."""

    date: str = Field(description="Fecha en formato YYYY-MM-DD.")
    start: str = Field(description="Hora de inicio en formato HH:MM.")
    end: str = Field(description="Hora de fin en formato HH:MM.")
    attendees: int = Field(
        default=DEFAULT_ATTENDEES, description="Cantidad de asistentes."
    )


def make_tools(get_service: GetService, get_user_id: GetUserId) -> list[BaseTool]:
    """Build the agent's five tools, resolving `service` and `user_id` per call."""

    @tool("create_booking", args_schema=CreateBookingInput)
    def create_booking(
        room: str, date: str, start: str, end: str, title: str, attendees: int
    ) -> str:
        """Crea una reserva para la sala/fecha/horario/título/asistentes indicados."""
        try:
            booking = get_service().create(
                get_user_id(),
                room,
                dt.date.fromisoformat(date),
                tu.parse_hhmm(start),
                tu.parse_hhmm(end),
                title,
                attendees,
            )
        except DomainError as exc:
            return exc.message
        return f"{BOOKING_CREATED_PREFIX}: Sala {booking.room_code} {date} {start}-{end} ({title})."

    @tool("list_available_rooms", args_schema=AvailabilityInput)
    def list_available_rooms(
        date: str, start: str, end: str, attendees: int = DEFAULT_ATTENDEES
    ) -> str:
        """Lista las salas libres para el rango horario y cantidad de asistentes."""
        rooms = get_service().availability(
            dt.date.fromisoformat(date), tu.parse_hhmm(start), tu.parse_hhmm(end), attendees
        )
        codes = ", ".join(f"{r.code} (cap {r.capacity})" for r in rooms)
        return f"Salas libres: {codes or NO_FREE_ROOMS_LABEL}"

    @tool
    def get_room_schedule(room: str, date: str) -> str:
        """Devuelve los bloques ocupados y libres de una sala para una fecha."""
        svc = get_service()
        try:
            schedule = svc.schedule(room, dt.date.fromisoformat(date))
        except DomainError as exc:
            return exc.message
        return _render_schedule(room, date, schedule, svc.tz)

    @tool
    def list_my_bookings() -> str:
        """Lista las reservas del usuario actual, con sus ids, para poder cancelarlas."""
        svc = get_service()
        bookings = svc.list_by_owner(get_user_id())
        lines = [_render_own_booking(b, svc.tz) for b in bookings]
        return "\n".join(lines) or NO_OWN_BOOKINGS_MESSAGE

    @tool
    def cancel_booking(booking_id: str) -> str:
        """Cancela una reserva propia dado su id."""
        try:
            get_service().cancel(get_user_id(), uuid.UUID(booking_id))
        except DomainError as exc:
            return exc.message
        return BOOKING_CANCELLED_MESSAGE

    return [create_booking, list_available_rooms, get_room_schedule, list_my_bookings, cancel_booking]


def _render_schedule(room: str, date: str, schedule: RoomSchedule, tz: str) -> str:
    """Render a room's occupied/free blocks as a short, local-time summary."""
    occupied = "; ".join(
        f"{b.title} {tu.format_hhmm(tu.to_local(b.starts_at, tz).time())}"
        for b in schedule["occupied"]
    )
    free = "; ".join(f"{tu.format_hhmm(s)}-{tu.format_hhmm(e)}" for s, e in schedule["free"])
    return (
        f"Sala {room} ({date}). "
        f"Ocupado: {occupied or NO_OCCUPIED_BLOCKS_LABEL}. "
        f"Libre: {free or NO_FREE_BLOCKS_LABEL}."
    )


def _render_own_booking(booking: Booking, tz: str) -> str:
    """Render one of the caller's bookings as `id · room date time · title`."""
    local_start = tu.to_local(booking.starts_at, tz)
    return f"{booking.id} · Sala {booking.room_code} {local_start:%Y-%m-%d %H:%M} · {booking.title}"
