"""HGTStub returns canned predictions deterministically."""

from __future__ import annotations

from graphwash.api.hgt_stub import HGTStub


def test_predict_returns_probability_and_label() -> None:
    stub = HGTStub()
    result = stub.predict(transaction_id="tx-001")
    assert 0.0 <= result.score <= 1.0
    assert result.label in {"benign", "suspicious"}


def test_predict_is_deterministic_for_same_id() -> None:
    stub = HGTStub()
    first = stub.predict(transaction_id="tx-042")
    second = stub.predict(transaction_id="tx-042")
    assert first.score == second.score
    assert first.label == second.label
