"""Smoke test for the SQLAlchemy-backed booking repository."""
import datetime as dt
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.persistence.orm import Base, RoomORM
from app.adapters.persistence.sql_booking_repo import SqlBookingRepository
from app.domain.entities import Booking

UTC = dt.timezone.utc


@pytest.fixture
def session() -> Iterator[Session]:
    """Yield a `Session` on an in-memory SQLite DB, seeded with room C."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_ = sessionmaker(bind=engine)()
    session_.add(RoomORM(code="C", capacity=6))
    session_.commit()
    yield session_
    session_.close()


def test_add_and_list_by_room_on_date(session: Session) -> None:
    """A booking added via the repo is found by `list_by_room_on_date`."""
    repo = SqlBookingRepository(session)
    booking = Booking(
        room_code="C",
        owner_id=uuid.uuid4(),
        starts_at=dt.datetime(2026, 7, 21, 13, tzinfo=UTC),
        ends_at=dt.datetime(2026, 7, 21, 14, tzinfo=UTC),
        title="x",
        attendees=2,
    )

    repo.add(booking)
    found = repo.list_by_room_on_date(
        "C",
        dt.datetime(2026, 7, 21, 0, tzinfo=UTC),
        dt.datetime(2026, 7, 22, 0, tzinfo=UTC),
    )

    assert len(found) == 1
    assert found[0].title == "x"
