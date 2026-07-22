"""Conversions between ORM rows and domain entities."""
from app.adapters.persistence.orm import UserORM
from app.domain.entities import User


def user_to_entity(o: UserORM) -> User:
    """Convert a `UserORM` row into a domain `User`."""
    return User(id=o.id, username=o.username, password_hash=o.password_hash)
