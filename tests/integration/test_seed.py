"""Tests for startup seed behavior."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.persistence.orm import Base, RoomORM, UserORM
from app.core.startup import seed

EXPECTED_ROOM_COUNT = 5
EXPECTED_USER_COUNT = 2


def test_seed_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER1_PASSWORD", "demo1234")
    monkeypatch.setenv("USER2_PASSWORD", "demo1234")
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        seed(session)
    with session_factory() as session:
        seed(session)  # second run must not duplicate rows

    with session_factory() as session:
        assert len(session.scalars(select(RoomORM)).all()) == EXPECTED_ROOM_COUNT
        assert len(session.scalars(select(UserORM)).all()) == EXPECTED_USER_COUNT


def test_seed_can_skip_demo_users() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        seed(session, include_demo_users=False)

    with session_factory() as session:
        assert len(session.scalars(select(RoomORM)).all()) == EXPECTED_ROOM_COUNT
        assert len(session.scalars(select(UserORM)).all()) == 0
