"""FastAPI dependencies: service factories and the current-user extractor.

The user's identity always comes from the verified JWT, never from request
bodies, so `get_current_user` is the single source of truth for `owner_id`.
"""
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.adapters.persistence.sql_user_repo import SqlUserRepository
from app.core.config import settings
from app.core.db import get_session
from app.core.security import decode_token
from app.domain.services.auth_service import AuthService

BEARER_PREFIX = "Bearer "
HTTP_UNAUTHORIZED = 401


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    """Build an `AuthService` wired to the SQL-backed user repository."""
    return AuthService(SqlUserRepository(session))


def get_current_user(authorization: Annotated[str, Header()] = "") -> uuid.UUID:
    """Decode the `Authorization: Bearer <jwt>` header into the caller's user id."""
    if not authorization.startswith(BEARER_PREFIX):
        raise HTTPException(HTTP_UNAUTHORIZED, "No autenticado")
    token = authorization.removeprefix(BEARER_PREFIX)
    try:
        claims = decode_token(token, settings.jwt_secret)
    except jwt.PyJWTError as exc:
        raise HTTPException(HTTP_UNAUTHORIZED, "Token inválido") from exc
    return uuid.UUID(claims["sub"])
