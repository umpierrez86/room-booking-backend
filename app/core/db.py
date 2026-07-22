"""Database engine and session factory, configured from `Settings`."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Yield a `Session`, closing it once the caller is done."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
