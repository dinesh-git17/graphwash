# ADR 0008: Composite (bank, account) node IDs and `at_bank` relation

**Status:** Accepted (2026-04-22)

## Context

Post-merge review of PR #37 (T-024 HeteroData construction, closed
without merging) surfaced three coupled defects in the data pipeline
shape originally locked by REQ-001 and the 2026-04-22 T-024 design
session:

1. **Account identity.** The raw IT-AML HI-Medium CSV contains
   `Account` strings that are bank-local, not globally unique. IBM's
   reference preprocessor `format_kaggle_files.py` constructs node IDs
   as `Bank + Account`; graphwash's first loader keyed nodes by bare
   `Account`, silently merging distinct accounts that shared a string
   under different banks. On the T-024 1,000-row synthetic fixture,
   80 unique account strings collapsed 240 unique `(bank, account)`
   pairs into 80 nodes. On real IT-AML (31.9M rows) the collision
   rate is material.

2. **Bank attachment.** REQ-001 originally declared one edge type
   (`wire_transfer`) between accounts. The 2026-04-22 design session
   locked banks as isolated nodes, intending to revisit in Phase 2.
   This contradicted ADR-0001 §Context ("three node types [...] and
   one edge type whose semantics differ depending on endpoint
   combinations like `individual → bank`") and REQ-013a's response
   example (`"dst_type": "bank"` in `top_attention`). A smoke test of
   `HGTConv` on the PR #37 loader confirmed bank nodes received no
   embeddings under the isolated-node design. The declared third
   node type was structurally dead.

3. **Timestamp contract.** IBM's reference preprocessor encodes
   timestamps as seconds relative to `floor(min(timestamp), day) -
   10s`. The PR #37 loader stored absolute unix int64 seconds.
   T-024's task-list acceptance said "datetime64". Three disagreeing
   contracts.

## Decision

1. **Node identity is `(bank, account)`.** The loader constructs node
   keys by concatenating the raw `bank` integer with the raw
   `account` string, matching IBM's convention.
   `(from_bank, from_account)` and `(to_bank, to_account)` are
   deduplicated globally across the dataset before indexing.

2. **Two edge types: `wire_transfer` and `at_bank`.** `wire_transfer`
   carries account ↔ account transactions with per-edge features
   (amount, relative timestamp, cross-currency flag). `at_bank` is a
   static membership relation connecting each account to its declared
   bank; it has no per-edge features. REQ-001 is amended from
   "one edge type" to "two edge types". HGT messages flow across both
   relations, so bank nodes receive learned embeddings during
   training.

3. **Timestamps follow IBM convention.** Relative seconds from
   `floor(min(timestamp), day) − RELATIVE_TIMESTAMP_MARGIN_S`,
   stored as int64 on each `wire_transfer` edge. The
   `RELATIVE_TIMESTAMP_MARGIN_S = 10` value is a module-level
   constant in the loader; the dataset epoch is a property of the
   input CSV, computed per load, and attached to the returned
   `HeteroData` as `graphwash_timestamp_epoch_s`. A canonical
   HI-Medium reference value MAY be captured in
   `src/graphwash/data/schema.py` for documentation and
   full-dataset assertions; it is not the runtime source of truth.

4. **Individual/business split stays synthetic, for training data
   only.** The deterministic SHA-256 hash policy applied to composite
   `(bank, account)` ids classifies training-time account nodes into
   `individual` (~70%) and `business` (~30%). REQ-013 accepts
   client-declared node types at inference time, so the synthetic
   policy governs training-data construction only. It does not govern
   the API contract, and it does not claim anything about the
   underlying real-world population.

## Consequences

Positive:

- Topology matches IBM reference preprocessing; downstream statistics
  and embeddings are directly comparable to Multi-GNN baseline
  artefacts.
- Banks become learnable. `HGTConv` emits embeddings for all three
  node types. ADR-0001's type-aware attention rationale holds on the
  actual training graph.
- T-027's "±5%" gate becomes measurable: aggregate node count, edge
  count, and illicit rate all have corresponding `schema.py`
  reference values captured during S-02.

Negative:

- REQ-001 grows from one edge type to two, adding modest loader
  complexity and one more `HGTConv` metadata triplet to sweep.
- The `at_bank` relation is static and dense (one edge per account);
  it inflates the edge count of the training graph by roughly one
  edge per unique composite account, negligible against the
  ~31.9M `wire_transfer` base.
- The synthetic individual/business split cannot be validated against
  paper statistics. T-027's acceptance narrows to aggregate counts.

Neutral:

- ADR-0001 stays Accepted. An Amendment note on ADR-0001
  cross-references this ADR for the updated graph-shape context; the
  HGT-over-GAT decision itself is unaffected.
- REQ-013 and REQ-013a API contracts are unchanged. Clients continue
  to supply `{"type": "individual" | "business" | "bank"}` on the
  node list; the server-side synthetic policy only governs training
  data construction.
- The original "module-level constant" phrasing conflated the truly
  constant `-10s` margin with the dataset-dependent epoch. Section 1
  of the T-024 design surfaced the imprecision; Decision 3 above now
  matches what the loader implementation does.

## References

- IBM Multi-GNN `format_kaggle_files.py`:
  [format_kaggle_files.py on IBM/Multi-GNN](https://raw.githubusercontent.com/IBM/Multi-GNN/main/format_kaggle_files.py)
  (accessed 2026-04-22).
- PR #37 (closed without merge): the implementation that surfaced
  the defects; close-comment archives the finding evidence.
- ADR-0001 (HGT over GAT): architecture decision; Amendment note
  added in the same PR as this ADR.
- ADR-0007 (HI-Medium over LI-Medium): dataset choice; unaffected.
- PRD §8 REQ-001, REQ-002: functional requirements amended in the
  same PR as this ADR.
- PRD §11a S-02: schema validation spike; closed 2026-04-22.
