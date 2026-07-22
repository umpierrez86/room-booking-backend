"""Pure time-grid and timezone-conversion helpers for domain rules.

No I/O, no DB: everything here is a deterministic function of its inputs.
"""
import datetime as dt
from zoneinfo import ZoneInfo

GRID_MINUTES = (0, 30)
WEEKEND_WEEKDAY_THRESHOLD = 5


def is_on_grid(t: dt.time) -> bool:
    """Return True if `t` falls on the 30-minute booking grid."""
    return t.minute in GRID_MINUTES and t.second == 0


def is_weekday(d: dt.date) -> bool:
    """Return True if `d` is Monday through Friday."""
    return d.weekday() < WEEKEND_WEEKDAY_THRESHOLD


def within_hours(t: dt.time, start: dt.time, end: dt.time) -> bool:
    """Return True if `t` is within the inclusive [start, end] range."""
    return start <= t <= end


def local_naive_to_utc(d: dt.date, t: dt.time, tz: str) -> dt.datetime:
    """Combine a local date/time in `tz` and convert it to UTC-aware."""
    local = dt.datetime.combine(d, t, tzinfo=ZoneInfo(tz))
    return local.astimezone(dt.timezone.utc)


def to_local(instant: dt.datetime, tz: str) -> dt.datetime:
    """Convert a UTC-aware instant to a timezone-aware datetime in `tz`."""
    return instant.astimezone(ZoneInfo(tz))


def parse_hhmm(value: str) -> dt.time:
    """Parse an `HH:MM` string into a `time`."""
    hours, minutes = value.split(":")
    return dt.time(int(hours), int(minutes))


def format_hhmm(t: dt.time) -> str:
    """Format a `time` as an `HH:MM` string."""
    return t.strftime("%H:%M")
