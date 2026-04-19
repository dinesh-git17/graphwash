# ADR 0004 — Vanilla HTML/CSS/JS + D3 over React

**Status:** Accepted (2026-04-18)

## Context

The frontend's job is to render force-directed transaction graphs, highlight flagged edges by attention weight, and surface a side panel of explanation metadata (§7 UC1, REQ-017 / REQ-018). The rendering layer is D3.js v7.

Two options were considered for the application layer wrapping D3:

1. **React** — industry default; declarative component model; large ecosystem; requires a build step.
2. **Vanilla HTML/CSS/JS + D3** — no build step; no framework runtime; D3 operates directly on the DOM.

## Decision

Use vanilla HTML / CSS / JS + D3.js v7. Frontend is served as static files from the FastAPI application (REQ-016); no bundler, no `node_modules`, no separate frontend deploy.

## Consequences

Positive:

- D3 is inherently imperative and fights React's declarative rendering model. Staying vanilla removes that friction.
- No build step means the frontend is part of the same Docker image as the API — one deploy, one rollback.
- Keeps the portfolio focus on the ML system. For an ML engineering portfolio, the absence of React is not a weakness.

Negative:

- Recruiters scanning for "React" as a keyword will not find it. Accepted — the project's claim is ML + graph + explainability, not frontend frameworks.
- No component reuse primitives. If the UI grows past the current UC1-UC4 scope, this ADR should be revisited.

Neutral:

- Testing is limited to integration-level (Chrome / Firefox / Safari happy paths per §17 Phase 4 gate). No component-unit test layer.
