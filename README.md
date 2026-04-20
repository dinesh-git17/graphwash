# graphwash

`graphwash` is wire-transfer Anti-Money Laundering (AML) detection with
Heterogeneous Graph Attention Networks (HGT), trained on IBM's IT-AML
NeurIPS 2023 synthetic dataset.

> Portfolio demo on synthetic data. Not production-ready for real
> financial institutions. No SLA, no authentication, manual restart on
> failure.

[![CI][c]][a] [![Licence][m]][l] ![Python][p] ![Status][s]

## Demo

`https://graphwash.dineshd.dev/beta` (pending Phase 5b deploy; not live
until 2026-05-31 cutover).

## Benchmarks

Minority-class F1 on the IT-AML Medium test split; full table lives in
`BENCHMARKS.md` once Phase 2 completes (REQ-032, T-036).

| Model                        | Minority F1  | p95 latency (CPU) | W&B run |
| ---------------------------- | ------------ | ----------------- | ------- |
| IBM Multi-GNN (NeurIPS 2023) | 0.67 (paper) | n/a               | n/a     |
| GraphSAGE baseline           | pending      | pending           | pending |
| HGT v1                       | pending      | pending           | pending |

## Architecture

See [`docs/graphwash-diagrams.md`](docs/graphwash-diagrams.md) for the
system, deployment, and UC1 sequence Mermaid diagrams.

## Setup

Prerequisites: Python 3.12+, `uv`, git.

```bash
uv sync
uv run ruff check .
uv run mypy --strict src
uv run pytest
```

See [`docs/dev-guide.md`](docs/dev-guide.md) for full local setup,
training notes, and troubleshooting.

## Documentation

- [Product Requirements (PRD)](docs/graphwash-prd.md).
- [Developer Guide](docs/dev-guide.md).
- [Architecture Decision Records](docs/adr/README.md).
- [Task List](docs/graphwash-task-list.md).
- [System Diagrams](docs/graphwash-diagrams.md).
- [Phase 0 Setup Report](docs/graphwash-setup-report.md).

## Licence

MIT. See [`LICENSE`](LICENSE).

[c]:https://github.com/dinesh-git17/graphwash/actions/workflows/ci.yml/badge.svg
[a]:https://github.com/dinesh-git17/graphwash/actions/workflows/ci.yml
[m]:https://img.shields.io/badge/license-MIT-blue.svg
[l]:LICENSE
[p]:https://img.shields.io/badge/python-3.12%2B-blue.svg
[s]:https://img.shields.io/badge/status-pre--v1-orange.svg
