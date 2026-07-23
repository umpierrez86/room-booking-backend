"""Authentication endpoints."""
from fastapi import APIRouter, Depends

from app.adapters.web.deps import get_auth_service
from app.adapters.web.schemas import LoginRequest, TokenResponse
from app.core.config import settings
from app.core.security import create_token
from app.domain.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)) -> TokenResponse:
    """Authenticate the user and return a signed JWT.

    Raises `InvalidCredentials` (mapped to 401) on a bad username/password.
    """
    user = auth.authenticate(body.username, body.password)
    token = create_token(user.id, user.username, settings.jwt_secret, settings.jwt_expire_hours)
    return TokenResponse(access_token=token)
