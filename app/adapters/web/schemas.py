"""Request/response DTOs for the REST web adapter."""
import datetime as dt
import uuid

from pydantic import BaseModel, Field

MIN_ATTENDEES = 1
MIN_TITLE_LENGTH = 1

TOKEN_TYPE = "bearer"


class LoginRequest(BaseModel):
    """Credentials submitted to `POST /auth/login`."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """A freshly issued JWT access token."""

    access_token: str
    token_type: str = TOKEN_TYPE


class BookingCreate(BaseModel):
    """Payload to create a booking. `start`/`end` are local `HH:MM` strings."""

    room: str
    date: dt.date
    start: str
    end: str
    title: str = Field(min_length=MIN_TITLE_LENGTH)
    attendees: int = Field(ge=MIN_ATTENDEES)


class BookingOut(BaseModel):
    """A booking rendered in `APP_TIMEZONE`-local date/time strings."""

    id: uuid.UUID
    room: str
    date: dt.date
    start: str
    end: str
    title: str
    attendees: int


class RoomOut(BaseModel):
    """A bookable room and its seating capacity."""

    code: str
    capacity: int


class OccupiedBlock(BaseModel):
    """A single occupied slot within a room's daily schedule."""

    id: uuid.UUID
    start: str
    end: str
    title: str


class FreeBlockOut(BaseModel):
    """A single free slot within a room's daily schedule."""

    start: str
    end: str


class OperatingHours(BaseModel):
    """The configured daily operating window, as local `HH:MM` strings."""

    start: str
    end: str


class RoomScheduleOut(BaseModel):
    """A room's occupied/free blocks for a single day."""

    room: str
    date: dt.date
    capacity: int
    operating: OperatingHours
    occupied: list[OccupiedBlock]
    free: list[FreeBlockOut]


class DaySchedule(BaseModel):
    """The schedule of every room for a single day."""

    date: dt.date
    rooms: list[RoomScheduleOut]
