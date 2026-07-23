"""Configuration normalization tests."""
import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("input_url", "expected_url"),
    [
        ("postgres://user:pass@host:5432/db", "postgresql+psycopg://user:pass@host:5432/db"),
        ("postgresql://user:pass@host:5432/db", "postgresql+psycopg://user:pass@host:5432/db"),
        (
            "postgresql+psycopg://user:pass@host:5432/db",
            "postgresql+psycopg://user:pass@host:5432/db",
        ),
    ],
)
def test_database_url_uses_psycopg_driver(input_url: str, expected_url: str) -> None:
    assert Settings(database_url=input_url).database_url == expected_url
