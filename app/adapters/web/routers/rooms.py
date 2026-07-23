"""Room catalog, availability and schedule endpoints."""
import datetime as dt

from fastapi import APIRouter, Depends, Query

from app.adapters.web.deps import get_booking_service, get_current_user
from app.adapters.web.schemas import (
    DaySchedule,
    FreeBlockOut,
    OccupiedBlock,
    OperatingHours,
    RoomOut,
    RoomScheduleOut,
)
from app.core.config import settings
from app.domain import timeutils as tu
from app.domain.services.booking_service import BookingService, RoomSchedule

MIN_ATTENDEES = 1

router = APIRouter(tags=["rooms"])


def _to_schedule_out(sch: RoomSchedule, code: str, d: dt.date) -> RoomScheduleOut:
    """Render a `RoomSchedule` (UTC-aware bookings) in local `HH:MM` strings."""
    tz = settings.app_timezone
    occupied = [
        OccupiedBlock(
            id=b.id,
            start=tu.format_hhmm(tu.to_local(b.starts_at, tz).time()),
            end=tu.format_hhmm(tu.to_local(b.ends_at, tz).time()),
            title=b.title,
        )
        for b in sch["occupied"]
    ]
    free = [FreeBlockOut(start=tu.format_hhmm(s), end=tu.format_hhmm(e)) for s, e in sch["free"]]
    return RoomScheduleOut(
        room=code,
        date=d,
        capacity=sch["capacity"],
        operating=OperatingHours(start=settings.booking_start, end=settings.booking_end),
        occupied=occupied,
        free=free,
    )


@router.get("/rooms", response_model=list[RoomOut])
def rooms(
    _: object = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> list[RoomOut]:
    """List every bookable room and its capacity."""
    return [RoomOut(code=r.code, capacity=r.capacity) for r in svc.rooms.all()]


@router.get("/availability", response_model=list[RoomOut])
def availability(
    date: dt.date,
    start: dt.time,
    end: dt.time,
    attendees: int = Query(ge=MIN_ATTENDEES),
    _: object = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> list[RoomOut]:
    """List rooms with enough capacity and no overlap for the given slot."""
    free_rooms = svc.availability(date, start, end, attendees)
    return [RoomOut(code=r.code, capacity=r.capacity) for r in free_rooms]


@router.get("/rooms/{code}/schedule", response_model=RoomScheduleOut)
def room_schedule(
    code: str,
    date: dt.date,
    _: object = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> RoomScheduleOut:
    """Return one room's occupied/free blocks for a day."""
    return _to_schedule_out(svc.schedule(code, date), code, date)


@router.get("/schedule", response_model=DaySchedule)
def all_schedule(
    date: dt.date,
    _: object = Depends(get_current_user),
    svc: BookingService = Depends(get_booking_service),
) -> DaySchedule:
    """Return every room's schedule for a day, feeding the calendar grid."""
    schedules = [_to_schedule_out(svc.schedule(r.code, date), r.code, date) for r in svc.rooms.all()]
    return DaySchedule(date=date, rooms=schedules)
