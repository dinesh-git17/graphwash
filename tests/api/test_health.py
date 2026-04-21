"""Health-endpoint smoke coverage."""

from __future__ import annotations

from fastapi.testclient import TestClient

from graphwash.api import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
