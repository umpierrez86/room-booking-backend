"""Request/response DTOs for the REST web adapter."""
from pydantic import BaseModel

TOKEN_TYPE = "bearer"


class LoginRequest(BaseModel):
    """Credentials submitted to `POST /auth/login`."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """A freshly issued JWT access token."""

    access_token: str
    token_type: str = TOKEN_TYPE
