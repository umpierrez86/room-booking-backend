"""Driven adapter for the `Clock` port, backed by the system clock."""
import datetime as dt


class SystemClock:
    """`Clock` implementation returning the real, current UTC instant."""

    def now(self) -> dt.datetime:
        """Return the current instant as a UTC-aware datetime."""
        return dt.datetime.now(dt.timezone.utc)
