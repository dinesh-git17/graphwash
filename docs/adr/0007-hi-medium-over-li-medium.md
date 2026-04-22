# ADR 0007 - Use IT-AML HI-Medium over LI-Medium

**Status:** Accepted (2026-04-22)

## Context

ADR-0003 locks "Medium" as the training size but does not disambiguate
HI vs LI. Altman et al. (arXiv:2306.16424) ship six variants on Kaggle:
Small, Medium, and Large, each in a HI (higher illicit ratio) and LI
(lower illicit ratio) flavour. T-022's schema spike surfaces the gap.

Relevant numbers from paper Tables 2 and 4:

| Variant   | Transactions | Laundering | Rate (1 per N) | Best published F1 (%) |
| --------- | ------------ | ---------- | -------------- | --------------------- |
| HI-Medium | 32M          | 35K        | 905            | 65.70 (GFP+XGBoost)   |
| LI-Medium | 31M          | 16K        | 1,948          | 28.16 (GFP+XGBoost)   |

REQ-009's Phase 2 gate is F1 >= 0.72. On HI-Medium that is +6 percentage
points over the best published; on LI-Medium it is +44, unreachable for
any architecture in the paper.

## Decision

Train, sweep, and benchmark on HI-Medium.

## Consequences

Positive:

- Phase 2 F1 gate is reachable with HGT plus type-aware attention plus
  class-weighted cross-entropy. On LI-Medium the gate is aspirational
  by a margin no architectural change closes.
- Baseline clarity: one comparator (GFP+XGBoost 65.70 on HI-Medium) for
  BENCHMARKS.md. Pure-GNN comparator (PNA 59.71) is available for
  apples-to-apples "HGT beats Multi-GNN" framing.
- Compute budget per §10 (~8-12h Vast.ai, ~$4-5) fits. The harder LI
  signal would demand more sweeps and risk overrun with no compensating
  upside.

Negative:

- The "beats the harder LI variant" portfolio narrative is unavailable.
  Mitigation: BENCHMARKS.md cites paper Table 2 explicitly, naming
  HI-Medium and the baseline row.
- §13 risk 2's fallback ladder (focal loss, deeper layers, more heads,
  migrate to Large) applies within the HI family only. LI-Medium is no
  longer a fallback.

Neutral:

- The "migrate to Large" fallback now points at HI-Large (180M
  transactions, 1 per 807 illicit rate), not LI-Large. Compute cost
  jumps roughly 5x vs HI-Medium.
- ADR-0003 stays Accepted. This ADR extends, does not replace.

## References

- Altman et al., NeurIPS 2023, arXiv:2306.16424, Tables 2 and 4.
- `src/graphwash/data/schema.py` for captured constants.
- ADR-0003 for the orthogonal size decision (Medium over Small/Large).
