"""`UserRepository` adapter backed by SQLAlchemy."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.persistence import mappers
from app.adapters.persistence.orm import UserORM
from app.domain.entities import User


class SqlUserRepository:
    """`UserRepository` port implementation over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_username(self, username: str) -> User | None:
        """Return the user with `username`, or None if it does not exist."""
        o = self._session.scalar(select(UserORM).where(UserORM.username == username))
        return mappers.user_to_entity(o) if o else None
