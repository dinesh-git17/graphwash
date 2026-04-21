"""Pydantic v2 request/response schemas for the stub score endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    """Incoming payload for /api/v1/score."""

    transaction_id: str = Field(..., min_length=1, max_length=128)


class ScoreResponse(BaseModel):
    """Stub prediction envelope."""

    score: float = Field(..., ge=0.0, le=1.0)
    label: Literal["benign", "suspicious"]
    model_version: str = Field(default="stub-t-019")
