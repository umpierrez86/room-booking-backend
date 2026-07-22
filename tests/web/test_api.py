"""End-to-end tests of the REST web adapter, with services faked via
`dependency_overrides` so no real database is involved.
"""
import datetime as dt
import uuid

from fastapi.testclient import TestClient

from app.adapters.web import deps
from app.adapters.web.main import create_app
from app.core.security import hash_password
from app.domain.entities import Room, User
from app.domain.services.auth_service import AuthService
from app.domain.services.booking_service import BookingService
from tests.fakes import (
    FixedClock,
    InMemoryBookingRepository,
    InMemoryRoomCatalog,
    InMemoryUserRepository,
)

TZ = "America/Montevideo"
OPEN_TIME, CLOSE_TIME = dt.time(8, 0), dt.time(20, 0)
ROOMS = [Room("A", 4), Room("B", 6), Room("C", 6), Room("D", 8), Room("E", 10)]
NOW = dt.datetime(2026, 7, 20, 12, tzinfo=dt.timezone.utc)
USER = User(uuid.uuid4(), "User1", hash_password("demo1234"))


def client_with_fakes() -> tuple[TestClient, User]:
    """Build a `TestClient` wired to in-memory fakes via dependency overrides."""
    app = create_app()
    bookings = InMemoryBookingRepository()
    booking_service = BookingService(
        bookings, InMemoryRoomCatalog(ROOMS), FixedClock(NOW), TZ, OPEN_TIME, CLOSE_TIME
    )
    auth_service = AuthService(InMemoryUserRepository([USER]))
    app.dependency_overrides[deps.get_booking_service] = lambda: booking_service
    app.dependency_overrides[deps.get_auth_service] = lambda: auth_service
    return TestClient(app), USER


def login(client: TestClient) -> str:
    """Log in as `USER` and return the issued access token."""
    resp = client.post("/auth/login", json={"username": "User1", "password": "demo1234"})
    return str(resp.json()["access_token"])


def test_login_and_create_booking() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    resp = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "room": "C",
            "date": "2026-07-21",
            "start": "10:00",
            "end": "11:30",
            "title": "Sprint",
            "attendees": 6,
        },
    )
    assert resp.status_code == 201


def test_overlap_returns_409() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"room": "C", "date": "2026-07-21", "start": "10:00", "end": "11:00", "title": "x", "attendees": 2}
    client.post("/bookings", headers=headers, json=body)
    overlapping = {**body, "start": "10:30", "end": "11:30"}
    resp = client.post("/bookings", headers=headers, json=overlapping)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "OVERLAP"


def test_requires_auth() -> None:
    client, _ = client_with_fakes()
    assert client.get("/bookings/me").status_code == 401


def test_invalid_credentials_returns_401() -> None:
    client, _ = client_with_fakes()
    resp = client.post("/auth/login", json={"username": "User1", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_capacity_exceeded_returns_400() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    resp = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {token}"},
        json={"room": "A", "date": "2026-07-21", "start": "10:00", "end": "11:00", "title": "x", "attendees": 5},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CAPACITY_EXCEEDED"


def test_list_rooms() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    resp = client.get("/rooms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert {r["code"] for r in resp.json()} == {"A", "B", "C", "D", "E"}


def test_availability() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/bookings",
        headers=headers,
        json={"room": "C", "date": "2026-07-21", "start": "10:00", "end": "11:00", "title": "x", "attendees": 2},
    )
    resp = client.get(
        "/availability",
        headers=headers,
        params={"date": "2026-07-21", "start": "10:00", "end": "11:00", "attendees": 6},
    )
    assert resp.status_code == 200
    codes = {r["code"] for r in resp.json()}
    assert "C" not in codes
    assert "A" not in codes
    assert {"B", "D", "E"} <= codes


def test_room_schedule() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/bookings",
        headers=headers,
        json={"room": "C", "date": "2026-07-21", "start": "10:00", "end": "11:30", "title": "x", "attendees": 2},
    )
    resp = client.get("/rooms/C/schedule", headers=headers, params={"date": "2026-07-21"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["occupied"]) == 1
    assert {"start": "08:00", "end": "10:00"} in body["free"]


def test_all_rooms_schedule() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    resp = client.get("/schedule", headers={"Authorization": f"Bearer {token}"}, params={"date": "2026-07-21"})
    assert resp.status_code == 200
    assert {r["room"] for r in resp.json()["rooms"]} == {"A", "B", "C", "D", "E"}


def test_cancel_booking() -> None:
    client, _ = client_with_fakes()
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/bookings",
        headers=headers,
        json={"room": "C", "date": "2026-07-21", "start": "10:00", "end": "11:00", "title": "x", "attendees": 2},
    ).json()
    resp = client.delete(f"/bookings/{created['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/bookings/me", headers=headers).json() == []
