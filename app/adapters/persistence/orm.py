"""SQLAlchemy 2.0 ORM mapping for the persistence adapter.

These classes are the driven-side storage shape; they are converted to and
from domain entities by `mappers` and never leak past the repository
adapters in this package.
"""
import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utc_now() -> dt.datetime:
    """Return the current instant as a UTC-aware datetime."""
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in this adapter."""


class UserORM(Base):
    """Row shape for the `users` table."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class RoomORM(Base):
    """Row shape for the `rooms` table."""

    __tablename__ = "rooms"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    capacity: Mapped[int] = mapped_column(Integer)


class BookingORM(Base):
    """Row shape for the `bookings` table."""

    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_code: Mapped[str] = mapped_column(ForeignKey("rooms.code"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String)
    attendees: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
