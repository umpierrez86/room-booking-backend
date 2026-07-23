"""`BookingRepository` adapter backed by SQLAlchemy."""
import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.persistence import mappers
from app.adapters.persistence.orm import BookingORM
from app.domain.entities import Booking
from app.domain.errors import Overlap


class SqlBookingRepository:
    """`BookingRepository` port implementation over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, b: Booking) -> Booking:
        """Persist `b` and return the stored booking.

        The service-level overlap check is the first line of defence, but two
        concurrent requests can both pass it (TOCTOU). The Postgres exclusion
        constraint is the DB-level barrier that lets exactly one win; the loser
        raises `IntegrityError`, which is translated back into the domain's
        `Overlap` so callers see a single, consistent error.
        """
        o = mappers.booking_to_orm(b)
        self._session.add(o)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise Overlap(f"La sala {b.room_code} ya está ocupada en ese horario.") from exc
        self._session.refresh(o)
        return mappers.booking_to_entity(o)

    def get(self, id: uuid.UUID) -> Booking | None:
        """Return the booking with `id`, or None if it does not exist."""
        o = self._session.get(BookingORM, id)
        return mappers.booking_to_entity(o) if o else None

    def delete(self, id: uuid.UUID) -> None:
        """Remove the booking with `id`, if it exists."""
        o = self._session.get(BookingORM, id)
        if o:
            self._session.delete(o)
            self._session.commit()

    def list_by_owner(self, owner_id: uuid.UUID) -> list[Booking]:
        """Return every booking owned by `owner_id`."""
        rows = self._session.scalars(
            select(BookingORM).where(BookingORM.owner_id == owner_id)
        ).all()
        return [mappers.booking_to_entity(o) for o in rows]

    def list_by_room_on_date(
        self, room_code: str, day_start_utc: dt.datetime, day_end_utc: dt.datetime
    ) -> list[Booking]:
        """Return bookings for `room_code` overlapping the given UTC day window."""
        rows = self._session.scalars(
            select(BookingORM).where(
                BookingORM.room_code == room_code,
                BookingORM.starts_at < day_end_utc,
                BookingORM.ends_at > day_start_utc,
            )
        ).all()
        return [mappers.booking_to_entity(o) for o in rows]
