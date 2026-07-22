"""Tests for the domain error hierarchy: code, status and message."""
from app.domain.errors import CapacityExceeded, DomainError, Overlap


def test_error_carries_code_and_status() -> None:
    e = Overlap("La sala ya está ocupada de 10:00 a 11:00")
    assert isinstance(e, DomainError)
    assert e.code == "OVERLAP" and e.status == 409
    assert "ocupada" in e.message


def test_capacity_error() -> None:
    assert CapacityExceeded("...").status == 400
