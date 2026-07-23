"""In-memory fakes implementing the domain ports, used by tests."""
import datetime as dt
import uuid

from app.domain.entities import Booking, Room, User


class InMemoryBookingRepository:
    """`BookingRepository` backed by a plain dict, for tests."""

    def __init__(self) -> None:
        self._items: dict[uuid.UUID, Booking] = {}

    def add(self, b: Booking) -> Booking:
        """Store `b` under its id and return it."""
        self._items[b.id] = b
        return b

    def get(self, id: uuid.UUID) -> Booking | None:
        """Return the booking with `id`, or None if absent."""
        return self._items.get(id)

    def delete(self, id: uuid.UUID) -> None:
        """Remove the booking with `id`, if present."""
        self._items.pop(id, None)

    def list_by_owner(self, owner_id: uuid.UUID) -> list[Booking]:
        """Return every booking owned by `owner_id`."""
        return [b for b in self._items.values() if b.owner_id == owner_id]

    def list_by_room_on_date(
        self, room_code: str, day_start_utc: dt.datetime, day_end_utc: dt.datetime
    ) -> list[Booking]:
        """Return bookings for `room_code` overlapping the given UTC day window."""
        return [
            b
            for b in self._items.values()
            if b.room_code == room_code and b.starts_at < day_end_utc and b.ends_at > day_start_utc
        ]


class InMemoryUserRepository:
    """`UserRepository` backed by a plain dict, for tests."""

    def __init__(self, users: list[User] | None = None) -> None:
        self._by_name = {u.username: u for u in (users or [])}

    def get_by_username(self, username: str) -> User | None:
        """Return the user with `username`, or None if absent."""
        return self._by_name.get(username)


class InMemoryRoomCatalog:
    """`RoomCatalog` backed by a plain dict, for tests."""

    def __init__(self, rooms: list[Room]) -> None:
        self._by_code = {r.code: r for r in rooms}

    def get(self, code: str) -> Room | None:
        """Return the room with `code`, or None if absent."""
        return self._by_code.get(code)

    def all(self) -> list[Room]:
        """Return every room in the catalog."""
        return list(self._by_code.values())


class FixedClock:
    """`Clock` returning a fixed instant, for deterministic tests."""

    def __init__(self, now: dt.datetime) -> None:
        self._now = now

    def now(self) -> dt.datetime:
        """Return the fixed instant this clock was constructed with."""
        return self._now
