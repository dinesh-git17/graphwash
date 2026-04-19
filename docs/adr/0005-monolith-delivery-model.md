# ADR 0005 — Single-process FastAPI monolith serving API and frontend

**Status:** Accepted (2026-04-18)

## Context

graphwash has two runtime-visible surfaces: the inference API and the D3 static frontend. Training is offline and ephemeral on Vast.ai.

Deployment options considered:

1. **Split services** — frontend on Vercel / a CDN, API on Hetzner. Standard modern-stack pattern.
2. **Single-process monolith** — one FastAPI process serves both, packaged as one Docker container on Hetzner. Static files served via `StaticFiles` mount.
3. **Separate containers behind a reverse proxy** — nginx container + api container on the same host.

## Decision

Single-process FastAPI monolith. One Docker image. Static files mounted from FastAPI (REQ-016). Reverse proxy (Caddy or Nginx) terminates TLS and routes to Uvicorn.

## Consequences

Positive:

- One `Dockerfile`, one image tag, one deploy, one rollback path — matches §17 Phase 5 rollback procedure exactly.
- No CORS — frontend and API share the origin.
- No Vercel / CDN account required — lowers infra surface for a prototype.
- Aligns with §5 non-goal 8 (no Kubernetes / orchestration).

Negative:

- Uvicorn serves static files; minor perf hit versus a CDN, negligible at demo load.
- If v2 ever needs separate scaling for the frontend or a SPA framework with a build step, this ADR is superseded.

Neutral:

- The reverse-proxy choice (Caddy vs. Nginx) is flexible and tracked in §9a as non-locked.
