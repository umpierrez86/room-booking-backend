"""Application settings, sourced from environment variables and `.env`."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Room Booking API."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/rooms"
    jwt_secret: str = "dev-secret-change-me"
    app_timezone: str = "America/Montevideo"
    booking_start: str = "08:00"
    booking_end: str = "20:00"
    jwt_expire_hours: int = 8
    google_api_key: str = ""
    llm_model: str = "google_genai:gemini-3.1-flash-lite"
    cors_origins: str = "*"
    seed_demo_users: bool = False
    testing: bool = False

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        """Make Railway's standard Postgres URL explicit for SQLAlchemy."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


settings = Settings()
