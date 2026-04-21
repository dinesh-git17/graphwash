"""FastAPI application factory for the T-019 stub deployment."""

from __future__ import annotations

from fastapi import FastAPI

from graphwash.api.hgt_stub import HGTStub
from graphwash.api.models import ScoreRequest, ScoreResponse


def create_app() -> FastAPI:
    """Build the FastAPI app with stub score + health endpoints."""
    app = FastAPI(title="graphwash", version="0.1.0-t-019")
    model = HGTStub()

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/score", response_model=ScoreResponse)
    def score(payload: ScoreRequest) -> ScoreResponse:
        return model.predict(transaction_id=payload.transaction_id)

    return app


app = create_app()
