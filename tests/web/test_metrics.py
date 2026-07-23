from fastapi.testclient import TestClient

from app.adapters.web.main import create_app
from app.core.config import settings


def test_metrics_endpoint_is_unavailable_without_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_bearer_token", "")
    r = TestClient(create_app()).get("/metrics")
    assert r.status_code == 503


def test_metrics_endpoint_requires_bearer_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_bearer_token", "metrics-secret")
    r = TestClient(create_app()).get("/metrics")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_metrics_endpoint_rejects_invalid_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_bearer_token", "metrics-secret")
    r = TestClient(create_app()).get(
        "/metrics",
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert r.status_code == 401


def test_metrics_endpoint_accepts_valid_credentials(monkeypatch) -> None:
    monkeypatch.setattr(settings, "metrics_bearer_token", "metrics-secret")
    r = TestClient(create_app()).get(
        "/metrics",
        headers={"Authorization": "Bearer metrics-secret"},
    )
    assert r.status_code == 200 and "http_requests_total" in r.text
