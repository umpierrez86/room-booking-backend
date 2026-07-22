"""Core domain entities: rooms, users and bookings.

`Room` and `User` are immutable value-like records. `Booking` carries its
own identity (`id`) and is created before being persisted, so it stays a
plain (mutable) dataclass.
"""
import datetime as dt
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Room:
    """A bookable room with a fixed seating capacity."""

    code: str
    capacity: int


@dataclass(frozen=True)
class User:
    """An authenticated user, identified by a unique username."""

    id: uuid.UUID
    username: str
    password_hash: str


@dataclass
class Booking:
    """A reservation of a room for a time range, owned by a user.

    `starts_at` and `ends_at` are always UTC-aware instants.
    """

    room_code: str
    owner_id: uuid.UUID
    starts_at: dt.datetime
    ends_at: dt.datetime
    title: str
    attendees: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: dt.datetime | None = None
