# ADR 0002 — Use native HGT attention weights over GNNExplainer

**Status:** Accepted (2026-04-18)

## Context

Explainability is a §4 P0 goal and a differentiator for the project — every positive prediction must surface the accounts and transfers that drove it.

Two approaches were considered:

1. **GNNExplainer** — a post-hoc technique that perturbs the input graph and measures feature importance. Produces a theoretically rigorous explanation but requires a separate optimization loop per prediction.
2. **Native attention weights** — use the final-layer attention coefficients from HGT's forward pass directly as the explanation signal.

## Decision

Use HGT's native final-layer attention weights. Top-10 highest-attention edges are returned alongside every positive prediction (REQ-010, REQ-011).

## Consequences

Positive:

- Zero additional inference cost — attention is a byproduct of the forward pass. Preserves the §9 <200 ms p95 latency target.
- Simpler API surface — no second endpoint, no explanation job queue.
- Aligns the explanation story with the architecture story (the whole pitch is "attention reveals laundering structure").

Negative:

- Attention weights are a **proxy** for feature importance, not a theoretically rigorous explanation. Documented as a known limitation in §14.
- If a v2 needs audit-grade explanations (e.g. for regulatory defensibility), this ADR is superseded by adding GNNExplainer as a second endpoint.

Neutral:

- Edge cases (uniform attention across a subgraph → "explanation signal weak" banner) are handled at the frontend layer (§7 UC3 edge cases) rather than at the model.
