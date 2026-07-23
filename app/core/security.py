"""Password hashing and JWT issuing/verification helpers."""
import datetime as dt
import uuid
from typing import Any

import jwt
from passlib.context import CryptContext

JWT_ALGORITHM = "HS256"
SUBJECT_CLAIM = "sub"
USERNAME_CLAIM = "username"
EXPIRY_CLAIM = "exp"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return the bcrypt hash of `password`."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if `password` matches `password_hash`."""
    return _pwd_context.verify(password, password_hash)


def create_token(user_id: uuid.UUID, username: str, secret: str, hours: int) -> str:
    """Return a signed JWT carrying the user's id and username, expiring in `hours`."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        SUBJECT_CLAIM: str(user_id),
        USERNAME_CLAIM: username,
        EXPIRY_CLAIM: now + dt.timedelta(hours=hours),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Decode and verify `token`, returning its claims. Raises `jwt.PyJWTError`."""
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
