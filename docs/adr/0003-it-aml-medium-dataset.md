# ADR 0003 — Train on IT-AML Medium, not Small or Large

**Status:** Accepted (2026-04-18)

## Context

IBM's IT-AML dataset ships in three sizes:

- **Small** — good for smoke tests, too small for credible F1 claims.
- **Medium** — the variant IBM reports their published Multi-GNN baseline (~0.67 F1) on.
- **Large** — stronger training signal but dramatically more GPU memory and wall-clock time.

Compute budget is ~8-12 hours of Vast.ai GPU time (~$4-5 at $0.406/hr — §10 Constraints), and the plan includes multiple W&B hyperparameter sweeps, not just a single training run.

## Decision

Train and benchmark on IT-AML Medium for v1.

## Consequences

Positive:

- Directly comparable to IBM's published Multi-GNN baseline — same dataset variant, apples-to-apples comparison in `BENCHMARKS.md`.
- Fits the compute budget with room for W&B sweeps over learning rate, heads, and hidden dimension (REQ-031).
- The 2-layer, hidden-dim-64 architecture is not capacity-constrained — the F1 gap between Medium and Large training sets diminishes past this capacity.

Negative:

- A reviewer might ask about Large-dataset behavior. The fallback answer is: the two-act narrative (GraphSAGE → HGT) is about architecture, not scale; a v1.1 training run on Large is cheap to add later.

Neutral:

- If HGT fails to beat the baseline on Medium (§13 risk 2), migrating to Large would be a ~2-3× budget increase rather than a new ADR.
