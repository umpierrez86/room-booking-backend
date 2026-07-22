"""Database initialization and idempotent demo-data seeding.

Run once at application startup (see the `lifespan` in
`app.adapters.web.main`): creates the schema if missing, then seeds the
fixed room catalog and the two demo users, skipping rows that already
exist so re-running it is a no-op.
"""
import os

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.adapters.persistence.orm import Base, RoomORM, UserORM
from app.core.db import SessionLocal, engine
from app.core.security import hash_password

ROOM_CAPACITIES = {"A": 4, "B": 6, "C": 6, "D": 8, "E": 10}
DEFAULT_DEMO_PASSWORD = "demo1234"
DEMO_USERS = (("User1", "USER1_PASSWORD"), ("User2", "USER2_PASSWORD"))
POSTGRES_DIALECT = "postgresql"
NO_OVERLAP_CONSTRAINT = "bookings_no_overlap"

# Postgres-only barrier against double-booking (TOCTOU): even if two concurrent
# requests both pass the service-level overlap check, this exclusion constraint
# lets at most one succeed. `btree_gist` is required for the `=` operator on
# `room_code` inside a GiST exclusion. Wrapped in a DO block so re-running
# startup is idempotent (older Postgres has no `ADD CONSTRAINT IF NOT EXISTS`).
_ENABLE_BTREE_GIST = "CREATE EXTENSION IF NOT EXISTS btree_gist;"
_ADD_NO_OVERLAP_CONSTRAINT = f"""
DO $$
BEGIN
    ALTER TABLE bookings ADD CONSTRAINT {NO_OVERLAP_CONSTRAINT}
        EXCLUDE USING gist (room_code WITH =, tstzrange(starts_at, ends_at) WITH &&);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""


def init_db() -> None:
    """Create every table declared under `Base`, if it does not exist yet."""
    Base.metadata.create_all(engine)
    _apply_no_overlap_constraint(engine)


def _apply_no_overlap_constraint(bound_engine: Engine) -> None:
    """Install the Postgres exclusion constraint that blocks overlapping bookings.

    Skipped on any non-Postgres dialect (the smoke tests run on in-memory
    SQLite, which supports neither `btree_gist` nor GiST exclusion constraints);
    the service-level overlap check remains the sole barrier there.
    """
    if bound_engine.dialect.name != POSTGRES_DIALECT:
        return
    with bound_engine.begin() as connection:
        connection.execute(text(_ENABLE_BTREE_GIST))
        connection.execute(text(_ADD_NO_OVERLAP_CONSTRAINT))


def seed(session: Session) -> None:
    """Insert the fixed room catalog and demo users, skipping existing rows."""
    _seed_rooms(session)
    _seed_demo_users(session)
    session.commit()


def _seed_rooms(session: Session) -> None:
    existing_codes = {r.code for r in session.scalars(select(RoomORM)).all()}
    for code, capacity in ROOM_CAPACITIES.items():
        if code not in existing_codes:
            session.add(RoomORM(code=code, capacity=capacity))


def _seed_demo_users(session: Session) -> None:
    existing_names = {u.username for u in session.scalars(select(UserORM)).all()}
    for username, password_env_var in DEMO_USERS:
        if username not in existing_names:
            password = os.getenv(password_env_var, DEFAULT_DEMO_PASSWORD)
            session.add(UserORM(username=username, password_hash=hash_password(password)))


def run_startup() -> None:
    """Initialize the schema and seed demo data. Called from the app lifespan."""
    init_db()
    with SessionLocal() as session:
        seed(session)
