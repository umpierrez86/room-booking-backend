from fastapi.testclient import TestClient

from app.adapters.web.main import create_app


def test_metrics_endpoint() -> None:
    r = TestClient(create_app()).get("/metrics")
    assert r.status_code == 200 and "http_requests_total" in r.text
