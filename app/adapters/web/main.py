"""FastAPI application factory (driving web adapter)."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.agent import runtime
from app.adapters.agent.router import router as chat_router
from app.adapters.web import errors_handler
from app.adapters.web.routers import auth, bookings, health, rooms
from app.core.config import settings
from app.core.startup import run_startup


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize schema/seed data and compile the reused, checkpointed agent
    graph on startup; both are skipped in tests (fixtures build their own)."""
    if settings.testing:
        yield
        return
    run_startup()
    async with runtime.lifespan_graph():
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
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(rooms.router)
    app.include_router(bookings.router)
    app.include_router(chat_router)

    return app


app = create_app()
