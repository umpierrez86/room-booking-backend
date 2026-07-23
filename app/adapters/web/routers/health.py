"""Liveness endpoint, kept out of the application factory."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report that the process is up and serving requests."""
    return {"status": "ok"}
