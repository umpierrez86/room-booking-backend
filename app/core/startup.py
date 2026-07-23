"""Database initialization and idempotent demo-data seeding.

Run once at application startup (see the `lifespan` in
`app.adapters.web.main`): creates the schema if missing, then seeds the
demo users, skipping rows that already exist so re-running it is a no-op.
"""
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.persistence.orm import Base, UserORM
from app.core.db import SessionLocal, engine
from app.core.security import hash_password

DEFAULT_DEMO_PASSWORD = "demo1234"
DEMO_USERS = (("User1", "USER1_PASSWORD"), ("User2", "USER2_PASSWORD"))


def init_db() -> None:
    """Create every table declared under `Base`, if it does not exist yet."""
    Base.metadata.create_all(engine)


def seed(session: Session) -> None:
    """Insert the demo users, skipping existing rows."""
    _seed_demo_users(session)
    session.commit()


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
