# Architecture Decision Records

Michael Nygard minimal format. Each ADR captures one irreversible
(or costly-to-reverse) decision.

## Index

| #                                          | Title                                                  | Status   |
| ------------------------------------------ | ------------------------------------------------------ | -------- |
| [0001](0001-hgt-over-gat.md)               | Use HGT over GAT for heterogeneous modeling            | Accepted |
| [0002](0002-native-attention-explainer.md) | Use native attention weights over GNNExplainer         | Accepted |
| [0003](0003-it-aml-medium-dataset.md)      | Train on IT-AML Medium, not Small or Large             | Accepted |
| [0004](0004-vanilla-d3-over-react.md)      | Vanilla HTML/CSS/JS + D3 over React                    | Accepted |
| [0005](0005-monolith-delivery-model.md)    | Single-process FastAPI monolith serving API + frontend | Accepted |
| [0006](0006-hetzner-instance-choice.md)    | Hetzner instance choice (hel1-dc2 8 GB reuse)          | Accepted |
| [0007](0007-hi-medium-over-li-medium.md)   | Use IT-AML HI-Medium over LI-Medium                    | Accepted |

## Format

Each ADR contains:

- **Status**: Proposed / Accepted / Superseded / Deprecated, with date.
- **Context**: the forces and constraints that made this decision
  necessary.
- **Decision**: the choice made.
- **Consequences**: positive, negative, and neutral outcomes of the
  decision.

## Lifecycle

- New ADRs are numbered sequentially and never renumbered.
- A decision that replaces an existing ADR supersedes it: the old ADR's
  status becomes `Superseded by NNNN` and the new ADR notes what it
  supersedes.
- Deprecated decisions stay in the repo. History is preserved.
