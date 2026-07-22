"""FastAPI application factory (driving web adapter)."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.agent.router import router as chat_router
from app.adapters.web import errors_handler
from app.adapters.web.routers import auth, bookings, rooms
from app.core.config import settings
from app.core.startup import run_startup


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize the schema and seed demo data on startup, skipped in tests."""
    if not settings.testing:
        run_startup()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(title="Room Booking API", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    errors_handler.register(app)
    app.include_router(auth.router)
    app.include_router(rooms.router)
    app.include_router(bookings.router)
    app.include_router(chat_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
