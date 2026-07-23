"""Domain error hierarchy.

Every business-rule violation raises a `DomainError` subclass carrying a
stable machine-readable `code`, a human-readable `message` and the HTTP
`status` a web adapter should map it to. Controllers never inspect these
directly: a global exception handler translates them into responses.
"""

HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_FORBIDDEN = 403
HTTP_CONFLICT = 409


class DomainError(Exception):
    """Base class for all business-rule violations."""

    code = "DOMAIN_ERROR"
    status = HTTP_BAD_REQUEST

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotOnGrid(DomainError):
    """Start/end time does not fall on the 30-minute grid."""

    code, status = "NOT_ON_GRID", HTTP_BAD_REQUEST


class InvalidDuration(DomainError):
    """Duration is not a 30-minute multiple within [30, 180] minutes."""

    code, status = "INVALID_DURATION", HTTP_BAD_REQUEST


class EndBeforeStart(DomainError):
    """End time is not strictly after the start time."""

    code, status = "END_BEFORE_START", HTTP_BAD_REQUEST


class OutOfHours(DomainError):
    """Slot falls outside the operating hours window."""

    code, status = "OUT_OF_HOURS", HTTP_BAD_REQUEST


class NotAWeekday(DomainError):
    """Date is not a Monday-to-Friday weekday."""

    code, status = "NOT_A_WEEKDAY", HTTP_BAD_REQUEST


class InThePast(DomainError):
    """Requested start instant is not in the future."""

    code, status = "IN_THE_PAST", HTTP_BAD_REQUEST


class InvalidAttendees(DomainError):
    """Attendee count is below the minimum of one."""

    code, status = "INVALID_ATTENDEES", HTTP_BAD_REQUEST


class CapacityExceeded(DomainError):
    """Attendee count exceeds the room's capacity."""

    code, status = "CAPACITY_EXCEEDED", HTTP_BAD_REQUEST


class RoomNotFound(DomainError):
    """No room exists with the given code."""

    code, status = "ROOM_NOT_FOUND", HTTP_NOT_FOUND


class BookingNotFound(DomainError):
    """No booking exists with the given id."""

    code, status = "BOOKING_NOT_FOUND", HTTP_NOT_FOUND


class Overlap(DomainError):
    """Requested slot overlaps an existing booking in the same room."""

    code, status = "OVERLAP", HTTP_CONFLICT


class NotOwner(DomainError):
    """The acting user does not own the booking being modified."""

    code, status = "NOT_OWNER", HTTP_FORBIDDEN
