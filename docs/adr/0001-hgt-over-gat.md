# ADR 0001 — Use HGT over GAT for heterogeneous modeling

**Status:** Accepted (2026-04-18)

## Context

The IT-AML transaction graph is heterogeneous: three node types (`individual`, `business`, `bank`) and one edge type (`wire_transfer`) whose semantics differ depending on the endpoint combinations (e.g. `individual → bank` is structurally different from `business → individual`).

Two viable architectures were considered:

1. **GAT with node-type embeddings** — a homogeneous Graph Attention Network where node type is concatenated into the feature vector. Simpler to implement. More existing AML literature.
2. **HGT (Heterogeneous Graph Transformer)** via PyG's `HGTConv` — type-aware attention heads trained per node-type pair.

## Decision

Adopt HGT as the primary architecture for v1. GraphSAGE remains as a homogeneous baseline (the first act of the "two-act" narrative); HGT is the second act.

## Consequences

Positive:

- Native type-aware attention heads — different attention mechanisms for each `(src_type, dst_type, edge_type)` combination.
- Cleaner architecture story for portfolio reviewers.
- Aligns with the "heterogeneous graph depth" claim in §4 Goals.

Negative:

- More complex implementation than GAT + concatenated embeddings.
- Slightly less AML-specific literature to cite; HGT literature skews toward academic graphs (OGB, Open Academic Graph).

Neutral:

- Forces the dataset pipeline to produce a typed `HeteroData` object from the start — this is desirable regardless.
