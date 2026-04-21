"""Score endpoint accepts valid payload and returns stub prediction."""

from __future__ import annotations

from fastapi.testclient import TestClient

from graphwash.api import create_app


def test_score_returns_prediction_shape() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/score",
        json={"transaction_id": "tx-001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "score" in body
    assert "label" in body
    assert 0.0 <= body["score"] <= 1.0
    assert body["label"] in {"benign", "suspicious"}


def test_score_rejects_missing_transaction_id() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/score", json={})
    assert response.status_code == 422


def test_score_rejects_empty_transaction_id() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/score", json={"transaction_id": ""})
    assert response.status_code == 422
