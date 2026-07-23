"""Pure booking validation rules: no DB, no I/O, deterministic given inputs."""
import datetime as dt

from app.domain import timeutils as tu
from app.domain.errors import (
    CapacityExceeded,
    EndBeforeStart,
    InThePast,
    InvalidAttendees,
    InvalidDuration,
    NotAWeekday,
    NotOnGrid,
    OutOfHours,
)
from app.domain.ports import Clock

MIN_DURATION_MINUTES = 30
MAX_DURATION_MINUTES = 180
DURATION_STEP_MINUTES = 30
MIN_ATTENDEES = 1
SECONDS_PER_MINUTE = 60


def validate_slot(
    d: dt.date,
    start: dt.time,
    end: dt.time,
    tz: str,
    open_t: dt.time,
    close_t: dt.time,
) -> None:
    """Validate that a slot lands on a weekday, on-grid, well-formed and
    within operating hours. Raises the corresponding `DomainError` subclass.
    """
    if not tu.is_weekday(d):
        raise NotAWeekday("Solo se puede reservar de lunes a viernes.")
    if not (tu.is_on_grid(start) and tu.is_on_grid(end)):
        raise NotOnGrid("Las horas deben caer en :00 o :30.")
    if end <= start:
        raise EndBeforeStart("La hora de fin debe ser posterior a la de inicio.")
    _validate_duration(d, start, end)
    if not (tu.within_hours(start, open_t, close_t) and tu.within_hours(end, open_t, close_t)):
        raise OutOfHours(f"Fuera del horario de operación ({open_t:%H:%M}–{close_t:%H:%M}).")


def _validate_duration(d: dt.date, start: dt.time, end: dt.time) -> None:
    """Raise `InvalidDuration` unless the slot is a 30-min multiple in [30, 180]."""
    duration = dt.datetime.combine(d, end) - dt.datetime.combine(d, start)
    minutes = int(duration.total_seconds()) // SECONDS_PER_MINUTE
    is_step_aligned = minutes % DURATION_STEP_MINUTES == 0
    is_in_range = MIN_DURATION_MINUTES <= minutes <= MAX_DURATION_MINUTES
    if not (is_step_aligned and is_in_range):
        raise InvalidDuration(
            "La reserva debe durar entre 30 min y 3 horas, en bloques de 30 min."
        )


def validate_attendees(n: int, capacity: int) -> None:
    """Validate the attendee count against the room's capacity."""
    if n < MIN_ATTENDEES:
        raise InvalidAttendees("La reserva debe tener al menos 1 asistente.")
    if n > capacity:
        raise CapacityExceeded(f"La sala tiene capacidad para {capacity} personas.")


def validate_not_past(starts_at_utc: dt.datetime, clock: Clock) -> None:
    """Raise `InThePast` if the booking would start at or before now."""
    if starts_at_utc <= clock.now():
        raise InThePast("No se puede reservar en el pasado.")
