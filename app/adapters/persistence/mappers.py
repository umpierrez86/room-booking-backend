"""Conversions between ORM rows and domain entities."""
from app.adapters.persistence.orm import BookingORM, RoomORM, UserORM
from app.domain.entities import Booking, Room, User


def booking_to_entity(o: BookingORM) -> Booking:
    """Convert a `BookingORM` row into a domain `Booking`."""
    return Booking(
        id=o.id,
        room_code=o.room_code,
        owner_id=o.owner_id,
        starts_at=o.starts_at,
        ends_at=o.ends_at,
        title=o.title,
        attendees=o.attendees,
        created_at=o.created_at,
    )


def booking_to_orm(b: Booking) -> BookingORM:
    """Convert a domain `Booking` into a `BookingORM` row, ready to persist."""
    return BookingORM(
        id=b.id,
        room_code=b.room_code,
        owner_id=b.owner_id,
        starts_at=b.starts_at,
        ends_at=b.ends_at,
        title=b.title,
        attendees=b.attendees,
    )


def user_to_entity(o: UserORM) -> User:
    """Convert a `UserORM` row into a domain `User`."""
    return User(id=o.id, username=o.username, password_hash=o.password_hash)


def room_to_entity(o: RoomORM) -> Room:
    """Convert a `RoomORM` row into a domain `Room`."""
    return Room(code=o.code, capacity=o.capacity)
