"""Global exception handler mapping `DomainError` to the API's error shape.

Registering this handler is what lets routers stay free of `try/except`:
any raised `DomainError` is translated here into
`{"error": {"code", "message"}}` with the status carried by the exception.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError


def register(app: FastAPI) -> None:
    """Register the `DomainError` exception handler on `app`."""

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
