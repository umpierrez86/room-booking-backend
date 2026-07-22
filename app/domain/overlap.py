"""Pure overlap detection between a candidate booking and existing ones."""
from app.domain.entities import Booking


def find_overlap(new: Booking, existing: list[Booking]) -> Booking | None:
    """Return the first booking in `existing` that overlaps `new`, or None.

    Two bookings overlap when one starts before the other ends and ends
    after the other starts; touching edges (e.g. 10:00-11:00 vs 11:00-12:00)
    do not count as an overlap.
    """
    return next((e for e in existing if new.starts_at < e.ends_at and new.ends_at > e.starts_at), None)
