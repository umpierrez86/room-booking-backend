"""SQLAlchemy 2.0 ORM mapping for the persistence adapter.

These classes are the driven-side storage shape; they are converted to and
from domain entities by `mappers` and never leak past the repository
adapters in this package.
"""
import datetime as dt
import uuid

from sqlalchemy import DateTime, String
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
