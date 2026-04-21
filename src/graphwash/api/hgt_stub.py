"""Deterministic canned-prediction stand-in for the real HGT model."""

from __future__ import annotations

import hashlib
from typing import Literal

from graphwash.api.models import ScoreResponse


class HGTStub:
    """Placeholder for the Phase 2 HGT model.

    Derives a deterministic pseudo-score from the transaction id hash so the
    stub endpoint returns stable output across calls without loading any real
    model weights. Used exclusively by the T-019 deployment smoke test.
    """

    _HASH_PREFIX_BYTES: int = 4
    _UINT32_MAX: int = 0xFFFFFFFF
    _THRESHOLD: float = 0.5

    def predict(self, transaction_id: str) -> ScoreResponse:
        """Return a canned ScoreResponse derived from the transaction id."""
        digest = hashlib.sha256(transaction_id.encode("utf-8")).digest()
        prefix = digest[: self._HASH_PREFIX_BYTES]
        score = int.from_bytes(prefix, "big") / self._UINT32_MAX
        label: Literal["benign", "suspicious"] = (
            "suspicious" if score >= self._THRESHOLD else "benign"
        )
        return ScoreResponse(score=score, label=label)
