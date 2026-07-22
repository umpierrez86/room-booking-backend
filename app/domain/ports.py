"""Driven-side ports (abstractions) that the domain depends on.

Expressed as `Protocol`s so adapters and test fakes satisfy them by duck
typing, with mypy static guarantees and no inheritance required.
"""
import datetime as dt
import uuid
from typing import Protocol

from app.domain.entities import Booking, Room, User


class Clock(Protocol):
    """Source of the current instant, always UTC-aware."""

    def now(self) -> dt.datetime:
        """Return the current instant as a UTC-aware datetime."""
        ...


class BookingRepository(Protocol):
    """Persistence port for bookings."""

    def add(self, b: Booking) -> Booking:
        """Persist `b` and return the stored booking."""
        ...

    def get(self, id: uuid.UUID) -> Booking | None:
        """Return the booking with `id`, or None if it does not exist."""
        ...

    def delete(self, id: uuid.UUID) -> None:
        """Remove the booking with `id`, if it exists."""
        ...

    def list_by_owner(self, owner_id: uuid.UUID) -> list[Booking]:
        """Return every booking owned by `owner_id`."""
        ...

    def list_by_room_on_date(
        self, room_code: str, day_start_utc: dt.datetime, day_end_utc: dt.datetime
    ) -> list[Booking]:
        """Return bookings for `room_code` overlapping the given UTC day window."""
        ...


class UserRepository(Protocol):
    """Persistence port for users."""

    def get_by_username(self, username: str) -> User | None:
        """Return the user with `username`, or None if it does not exist."""
        ...


class RoomCatalog(Protocol):
    """Read-only port for the fixed set of bookable rooms."""

    def get(self, code: str) -> Room | None:
        """Return the room with `code`, or None if it does not exist."""
        ...

    def all(self) -> list[Room]:
        """Return every room in the catalog."""
        ...
