"""Booking endpoints: create, list own, cancel."""
import uuid

from fastapi import APIRouter, Depends, Response, status

from app.adapters.web.deps import get_booking_service, get_current_user
from app.adapters.web.schemas import BookingCreate, BookingOut
from app.core.config import settings
from app.domain import timeutils as tu
from app.domain.entities import Booking
from app.domain.services.booking_service import BookingService

router = APIRouter(tags=["bookings"])


def _to_out(booking: Booking, tz: str) -> BookingOut:
    """Render a `Booking` (UTC-aware) as a `BookingOut` in local time."""
    local_start = tu.to_local(booking.starts_at, tz)
    local_end = tu.to_local(booking.ends_at, tz)
    return BookingOut(
        id=booking.id,
        room=booking.room_code,
        date=local_start.date(),
        start=tu.format_hhmm(local_start.time()),
        end=tu.format_hhmm(local_end.time()),
        title=booking.title,
        attendees=booking.attendees,
    )


@router.post("/bookings", status_code=status.HTTP_201_CREATED, response_model=BookingOut)
def create(
    body: BookingCreate,
    owner_id: uuid.UUID = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> BookingOut:
    """Create a booking owned by the authenticated user."""
    booking = svc.create(
        owner_id,
        body.room,
        body.date,
        tu.parse_hhmm(body.start),
        tu.parse_hhmm(body.end),
        body.title,
        body.attendees,
    )
    return _to_out(booking, settings.app_timezone)


@router.get("/bookings/me", response_model=list[BookingOut])
def mine(
    owner_id: uuid.UUID = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> list[BookingOut]:
    """List every booking owned by the authenticated user."""
    return [_to_out(b, settings.app_timezone) for b in svc.list_by_owner(owner_id)]


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel(
    booking_id: uuid.UUID,
    owner_id: uuid.UUID = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> Response:
    """Cancel a booking owned by the authenticated user."""
    svc.cancel(owner_id, booking_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
