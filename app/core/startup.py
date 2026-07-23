"""Database migration and idempotent demo-data seeding.

Run once at application startup (see the `lifespan` in
`app.adapters.web.main`): brings the schema up to date by running the
Alembic migrations, then seeds the fixed room catalog and the two demo
users, skipping rows that already exist so re-running it is a no-op.

The tests do not go through here: their fixtures build the schema directly
with `Base.metadata.create_all` on in-memory SQLite.
"""
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.adapters.persistence.orm import RoomORM, UserORM
from app.core.db import SessionLocal
from app.core.security import hash_password

ROOM_CAPACITIES = {"A": 4, "B": 6, "C": 6, "D": 8, "E": 10}
DEFAULT_DEMO_PASSWORD = "demo1234"
DEMO_USERS = (("User1", "USER1_PASSWORD"), ("User2", "USER2_PASSWORD"))

# Project root holds `alembic.ini`; resolve it absolutely so migrations run
# regardless of the process's working directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"


def init_db() -> None:
    """Bring the schema up to date by running Alembic migrations to head.

    The Postgres-only anti-overlap exclusion constraint lives inside the
    migration, so it is applied here too (and skipped on other dialects).
    """
    command.upgrade(_alembic_config(), "head")


def _alembic_config() -> Config:
    """Build an Alembic `Config` bound to the project's migration scripts."""
    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
    return config


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
