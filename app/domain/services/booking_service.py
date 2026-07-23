"""Booking service: orchestrates rules, overlap detection and ports.

The agent (LangGraph) and the REST adapter both call this service instead of
reimplementing business rules.
"""
import datetime as dt
import uuid
from typing import TypedDict

from app.domain import rules
from app.domain import timeutils as tu
from app.domain.entities import Booking, Room
from app.domain.errors import BookingNotFound, NotOwner, Overlap, RoomNotFound
from app.domain.overlap import find_overlap
from app.domain.ports import BookingRepository, Clock, RoomCatalog

FreeBlock = tuple[dt.time, dt.time]
PROBE_ATTENDEES = 0


class RoomSchedule(TypedDict):
    """A room's occupied bookings and free blocks for a single day."""

    room: str
    capacity: int
    occupied: list[Booking]
    free: list[FreeBlock]


class BookingService:
    """Coordinates booking creation, cancellation, availability and schedule."""

    def __init__(
        self,
        bookings: BookingRepository,
        rooms: RoomCatalog,
        clock: Clock,
        tz: str,
        open_t: dt.time,
        close_t: dt.time,
    ) -> None:
        self.bookings = bookings
        self.rooms = rooms
        self.clock = clock
        self.tz = tz
        self.open_t = open_t
        self.close_t = close_t

    def create(
        self,
        owner_id: uuid.UUID,
        room: str,
        d: dt.date,
        start: dt.time,
        end: dt.time,
        title: str,
        attendees: int,
    ) -> Booking:
        """Validate and persist a new booking, or raise a `DomainError`."""
        found_room = self._room(room)
        rules.validate_slot(d, start, end, self.tz, self.open_t, self.close_t)
        rules.validate_attendees(attendees, found_room.capacity)
        starts_at = tu.local_naive_to_utc(d, start, self.tz)
        ends_at = tu.local_naive_to_utc(d, end, self.tz)
        rules.validate_not_past(starts_at, self.clock)
        candidate = Booking(
            room_code=room,
            owner_id=owner_id,
            starts_at=starts_at,
            ends_at=ends_at,
            title=title,
            attendees=attendees,
        )
        self._reject_if_overlapping(candidate, d)
        return self.bookings.add(candidate)

    def cancel(self, owner_id: uuid.UUID, booking_id: uuid.UUID) -> None:
        """Delete a booking owned by `owner_id`, or raise a `DomainError`."""
        booking = self._owned_booking(owner_id, booking_id)
        self.bookings.delete(booking.id)

    def availability(
        self, d: dt.date, start: dt.time, end: dt.time, attendees: int
    ) -> list[Room]:
        """Return rooms with enough capacity and no overlap for the given slot."""
        starts_at = tu.local_naive_to_utc(d, start, self.tz)
        ends_at = tu.local_naive_to_utc(d, end, self.tz)
        day_start, day_end = self._day_bounds_utc(d)
        return [
            room
            for room in self.rooms.all()
            if room.capacity >= attendees
            and self._is_free(room.code, starts_at, ends_at, day_start, day_end)
        ]

    def schedule(self, room: str, d: dt.date) -> RoomSchedule:
        """Return the room's occupied bookings and free blocks for `d`."""
        found_room = self._room(room)
        day_start, day_end = self._day_bounds_utc(d)
        occupied = sorted(
            self.bookings.list_by_room_on_date(room, day_start, day_end),
            key=lambda b: b.starts_at,
        )
        return RoomSchedule(
            room=room,
            capacity=found_room.capacity,
            occupied=occupied,
            free=self._free_blocks(occupied),
        )

    def list_by_owner(self, owner_id: uuid.UUID) -> list[Booking]:
        """Return every booking owned by `owner_id`."""
        return self.bookings.list_by_owner(owner_id)

    def _room(self, code: str) -> Room:
        room = self.rooms.get(code)
        if room is None:
            raise RoomNotFound(f"La sala {code} no existe.")
        return room

    def _owned_booking(self, owner_id: uuid.UUID, booking_id: uuid.UUID) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise BookingNotFound("La reserva no existe.")
        if booking.owner_id != owner_id:
            raise NotOwner("Solo podés cancelar tus propias reservas.")
        return booking

    def _day_bounds_utc(self, d: dt.date) -> tuple[dt.datetime, dt.datetime]:
        day_start = tu.local_naive_to_utc(d, dt.time.min, self.tz)
        return day_start, day_start + dt.timedelta(days=1)

    def _is_free(
        self,
        room_code: str,
        starts_at: dt.datetime,
        ends_at: dt.datetime,
        day_start: dt.datetime,
        day_end: dt.datetime,
    ) -> bool:
        probe = Booking(
            room_code=room_code,
            owner_id=uuid.uuid4(),
            starts_at=starts_at,
            ends_at=ends_at,
            title="",
            attendees=PROBE_ATTENDEES,
        )
        existing = self.bookings.list_by_room_on_date(room_code, day_start, day_end)
        return find_overlap(probe, existing) is None

    def _reject_if_overlapping(self, candidate: Booking, d: dt.date) -> None:
        day_start, day_end = self._day_bounds_utc(d)
        existing = self.bookings.list_by_room_on_date(candidate.room_code, day_start, day_end)
        if find_overlap(candidate, existing) is not None:
            raise Overlap(f"La sala {candidate.room_code} ya está ocupada en ese horario.")

    def _free_blocks(self, occupied: list[Booking]) -> list[FreeBlock]:
        free: list[FreeBlock] = []
        cursor = self.open_t
        for booking in occupied:
            start_local = tu.to_local(booking.starts_at, self.tz).time()
            end_local = tu.to_local(booking.ends_at, self.tz).time()
            if start_local > cursor:
                free.append((cursor, start_local))
            cursor = max(cursor, end_local)
        if cursor < self.close_t:
            free.append((cursor, self.close_t))
        return free
