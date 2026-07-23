"""Tests for `AuthService`, exercised through the in-memory user fake."""
import uuid

import pytest

from app.core.security import hash_password
from app.domain.entities import User
from app.domain.services.auth_service import AuthService, InvalidCredentials
from tests.fakes import InMemoryUserRepository

PASSWORD = "demo1234"


def test_authenticate_ok() -> None:
    user = User(uuid.uuid4(), "User1", hash_password(PASSWORD))
    svc = AuthService(InMemoryUserRepository([user]))
    assert svc.authenticate("User1", PASSWORD).username == "User1"


def test_authenticate_bad() -> None:
    user = User(uuid.uuid4(), "User1", hash_password(PASSWORD))
    svc = AuthService(InMemoryUserRepository([user]))
    with pytest.raises(InvalidCredentials):
        svc.authenticate("User1", "wrong")
