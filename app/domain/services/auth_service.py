"""Authentication service: verifies credentials against the user repository."""
from app.core.security import verify_password
from app.domain.errors import DomainError
from app.domain.entities import User
from app.domain.ports import UserRepository

HTTP_UNAUTHORIZED = 401


class InvalidCredentials(DomainError):
    """Username does not exist or the password does not match."""

    code, status = "INVALID_CREDENTIALS", HTTP_UNAUTHORIZED


class AuthService:
    """Authenticates users by username and password."""

    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def authenticate(self, username: str, password: str) -> User:
        """Return the matching `User`, or raise `InvalidCredentials`."""
        user = self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials("Usuario o contraseña inválidos.")
        return user
