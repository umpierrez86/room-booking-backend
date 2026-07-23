"""`RoomCatalog` adapter backed by SQLAlchemy."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.persistence import mappers
from app.adapters.persistence.orm import RoomORM
from app.domain.entities import Room


class SqlRoomCatalog:
    """`RoomCatalog` port implementation over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, code: str) -> Room | None:
        """Return the room with `code`, or None if it does not exist."""
        o = self._session.get(RoomORM, code)
        return mappers.room_to_entity(o) if o else None

    def all(self) -> list[Room]:
        """Return every room in the catalog."""
        return [mappers.room_to_entity(o) for o in self._session.scalars(select(RoomORM)).all()]
