"""Prometheus instrumentation: request counter + `/metrics` endpoint."""
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "path"])

_Handler = Callable[[Request], Awaitable[Response]]


def register(app: FastAPI) -> None:
    """Count every request and expose Prometheus metrics at GET /metrics."""

    @app.middleware("http")
    async def _count_requests(request: Request, call_next: _Handler) -> Response:
        response = await call_next(request)
        REQUESTS.labels(request.method, _route_template(request)).inc()
        return response

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _route_template(request: Request) -> str:
    """Return the matched route's path template (e.g. `/bookings/{id}`).

    Routing populates `scope["route"]` while handling the request, so this must
    run *after* `call_next`. Using the template instead of `request.url.path`
    keeps the metric's label cardinality bounded: concrete UUIDs/codes in the
    path collapse to a single series. Unmatched requests (404s) fall back to the
    raw path.
    """
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)
