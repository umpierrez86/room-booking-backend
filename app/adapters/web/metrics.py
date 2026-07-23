"""Prometheus instrumentation: request counter, business `Metrics` + `/metrics`."""
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "path"])
BOOKINGS_CREATED = Counter("bookings_created_total", "Bookings successfully created")
BOOKINGS_CANCELLED = Counter("bookings_cancelled_total", "Bookings cancelled")
OVERLAPS_REJECTED = Counter("overlaps_rejected_total", "Bookings rejected due to overlap")

_Handler = Callable[[Request], Awaitable[Response]]


class PrometheusMetrics:
    """`Metrics` adapter backed by process-wide Prometheus counters."""

    def booking_created(self) -> None:
        """Increment the created-bookings counter."""
        BOOKINGS_CREATED.inc()

    def booking_cancelled(self) -> None:
        """Increment the cancelled-bookings counter."""
        BOOKINGS_CANCELLED.inc()

    def overlap_rejected(self) -> None:
        """Increment the rejected-overlaps counter."""
        OVERLAPS_REJECTED.inc()


class NoOpMetrics:
    """`Metrics` implementation that records nothing; the default for tests/fakes."""

    def booking_created(self) -> None:
        """Do nothing."""

    def booking_cancelled(self) -> None:
        """Do nothing."""

    def overlap_rejected(self) -> None:
        """Do nothing."""


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
