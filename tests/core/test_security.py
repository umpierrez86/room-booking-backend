"""Tests for password hashing and JWT encode/decode helpers."""
import uuid

from app.core.security import create_token, decode_token, hash_password, verify_password

PASSWORD = "demo1234"
SECRET = "s3cret"
EXPIRE_HOURS = 8


def test_hash_verify() -> None:
    hashed = hash_password(PASSWORD)
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("x", hashed)


def test_jwt_roundtrip() -> None:
    user_id = uuid.uuid4()
    token = create_token(user_id, "User1", SECRET, EXPIRE_HOURS)
    claims = decode_token(token, SECRET)
    assert claims["sub"] == str(user_id)
    assert claims["username"] == "User1"
