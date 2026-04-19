# graphwash — Product Requirements Document

**Title:** graphwash
**Version:** v1.1
**Author:** Dinesh
**Status:** In Review
**Created:** 2026-04-18
**Last updated:** 2026-04-18
**Stakeholders:** Dinesh (sole engineer, product owner)
**Target repo:** `/Users/Dinesh/dev/graphwash`
**Trusted systems:** N/A (v1 uses no persistent probe-eligible systems)
**Release posture:** Prototype — portfolio/demo artefact on synthetic data. Not production-ready for real financial institutions (see §6). No SLA, no authentication, manual restart on failure (see §9, §17).
**Linked docs:**

- `docs/graphwash-setup-report.md` — Phase 0 environment validation (Vast.ai / CUDA / PyG spike)
- `docs/graphwash-diagrams.md` — system / deployment / UC1 sequence Mermaid diagrams
- `docs/adr/` — Architecture Decision Records (0001-0005)
- `docs/dev-guide.md` — local setup, running, testing, project-specific conventions

**Supersedes:** N/A
**Superseded by:** N/A

**Change log:**

- 2026-04-18 — Phase 0 environment validation complete. Stack verified on Vast.ai RTX 5090. CUDA open question closed.
- 2026-04-18 — Cycle 1 of prd-review applied (status Draft → In Review).
- 2026-04-18 — Cycle 2 of prd-review applied (2 residual P1s closed; rolling-window inconsistency resolved).
- 2026-04-18 — Phase 01 triage gaps closed: v1 deadline pinned to 2026-05-31 (§10); REQ-013 payload shape pinned to raw edge list (§8); §18 open question retired.
- 2026-04-18 — Phase 02 triage gaps closed: release posture declared Prototype (header); §4 V1 minimum viable scope (four-pillar) statement added; §13a Break-question review subsection appended.
- 2026-04-18 — Phase 03 technical-shape gaps closed: §9a Architecture and Technical Shape section added, pinning delivery model (monolith), storage (no DB), environment model (3 envs, no preview), config/secrets policy, logging (structlog JSON) + no tracing, CI (GitHub Actions full), testing (pytest + 70% branch coverage), rollback posture cross-ref, top-level repo structure, and locked-vs-flexible decision table.
- 2026-04-18 — Phase 04 artefact pack assembled: `docs/graphwash-diagrams.md` (system / deployment / UC1 sequence Mermaid); `docs/adr/` index + ADR-0001..0005 (Nygard minimal); `docs/dev-guide.md` (local setup + project-specific conventions); REQ-013a response schemas + error envelope added (§8); §9a preamble declares the PRD doubles as v1 TDD.
- 2026-04-18 — Phase 05 spike plan added as §11a (S-00 DONE; S-01 CPU latency micro-spike, S-02 IT-AML schema validation, S-03 Hetzner + Docker smoke test, S-04 Caddy rate-limit + UptimeRobot — all MUST RUN before Phase 06 with kill signals and target dates; R-01 HGT-beats-baseline and R-02 attention-non-degeneracy marked ACCEPTED RISK with fallback ladders); §18 Q2 and Q5 absorbed into spike plan, Q8 annotated with feasibility cross-ref.
- 2026-04-18 — §19 phase budgets renegotiated to match the granular task list (`docs/graphwash-task-list.md`). Added Pilot Phase row (~7d), updated Phase 0/1/3 budgets to reflect honest per-PR atomic estimates. Focused total raised from 13-20d to ~26d. Deadline feasibility note added (gap vs. 2026-05-31 is ~2d; mitigation enumerated in §19).

---

## 1. Executive Summary

`graphwash` is a wire transfer Anti-Money Laundering (AML) detection system built on Heterogeneous Graph Attention Networks (HGT), trained on IBM's IT-AML NeurIPS 2023 dataset. It classifies individual wire transfer transactions as illicit or legitimate by modeling the full account-transaction graph, then surfaces an attention-based explanation of _which_ accounts and transfers drove each prediction. The system ships as a FastAPI inference service with a high-fidelity D3.js visualization frontend. The primary goal is a production-credible, portfolio-grade ML engineering project demonstrating graph ML depth, end-to-end system thinking, and explainability — targeting fintech and ML engineering roles. Success is defined by outperforming IBM's published Multi-GNN baseline on minority class F1, achieving sub-200ms inference latency on CPU, and shipping a live demo deployable on a Hetzner VPS.

---

## 2. Background and Context

Financial institutions are legally required to monitor and report suspicious transactions under AML regulations (BSA, FATF, EU AMLD). Existing rule-based systems are brittle — they fail to generalize across laundering patterns, require constant manual rule updates, and generate excessive false positives (industry estimates put false positive rates at 95-99%), creating significant compliance overhead.

Graph Neural Networks have emerged as the state-of-the-art approach for AML because money laundering is fundamentally a network phenomenon — individual transactions look clean in isolation, but the graph topology reveals coordinated behavior. The NeurIPS 2023 paper from IBM (_Realistic Synthetic Financial Transactions for Anti-Money Laundering Models_) established the IT-AML dataset as the canonical public benchmark and published a Multi-GNN baseline. This gives `graphwash` a concrete, published comparison point — a rarity in portfolio ML projects.

The ML engineering job market in 2026 specifically demands candidates with end-to-end graph ML experience, MLOps fluency, and production deployment evidence. Most AML portfolio projects on GitHub are either tabular XGBoost classifiers or simple GCNs trained on the Elliptic Bitcoin dataset. `graphwash` targets the gap above that ceiling: heterogeneous graphs, attention-based explainability, and a live served system.

---

## 3. Problem Statement

### Business problem

Financial institutions cannot efficiently detect wire transfer money laundering because: (1) rule-based systems can't generalize to novel laundering patterns, and (2) most ML approaches treat transactions as independent rows, discarding the relational structure that defines laundering behavior. The result is either high false negative rates (missed laundering) or high false positive rates (unnecessary investigation overhead).

### Technical problem

The IT-AML dataset exhibits extreme class imbalance — approximately 2% illicit transactions. A naive classifier that predicts "legitimate" for every transaction achieves ~98% accuracy while providing zero utility. The only meaningful metric is **minority class F1** (illicit class). IBM's Multi-GNN baseline achieves a published minority class F1 of approximately 0.67 on the IT-AML Medium dataset. Beating this with a heterogeneous architecture that also provides transaction-level explanations is the specific technical challenge.

### Portfolio problem

A trained model with no deployment surface and no explanation layer is a Jupyter notebook, not an engineering artifact. The project must demonstrate the full production arc: data pipeline → model training → evaluation → serving API → frontend visualization.

---

## 4. Goals

**V1 minimum viable scope.** V1 rests on four load-bearing pillars: (1) an HGT model that beats the IBM Multi-GNN minority-class F1 baseline on IT-AML Medium, (2) attention-based per-edge explainability returned inline with predictions, (3) a CPU-only FastAPI inference service with sub-200ms p95 latency, and (4) a live public demo on a Hetzner VPS. Removing any one pillar breaks the portfolio claim of "graph ML depth + end-to-end system thinking + explainability." Everything in §5 Non-Goals is explicitly outside this minimum.

| Priority | Goal                                  | Metric                                                         | Baseline                              | Target                                                         | Timeframe              |
| -------- | ------------------------------------- | -------------------------------------------------------------- | ------------------------------------- | -------------------------------------------------------------- | ---------------------- |
| P0       | Exceed IBM's published baseline       | Minority class F1 on IT-AML Medium test set                    | IBM Multi-GNN: ~0.67 F1               | ≥ 0.72 F1                                                      | At training completion |
| P0       | Fast CPU inference for demo viability | p95 prediction latency for a single-transaction subgraph query | Not established                       | < 200ms on Hetzner 16GB RAM VPS                                | At deployment          |
| P0       | Explainable predictions               | Attention subgraph returned per flagged edge                   | None (baseline has no explainability) | Top-10 attention edges returned with every positive prediction | At API completion      |
| P1       | Reproducible training                 | Full training run reproducible from seed and config            | N/A                                   | Random seed locked, W&B run logged, config YAML committed      | At training completion |
| P1       | Portfolio-ready demo                  | Live URL serving inference and visualization                   | N/A                                   | Demo accessible at public Hetzner VPS URL                      | At deployment          |

**Guardrail metric (P0 block):** Precision on the illicit class must not fall below 0.50. A model that recalls everything but flags half the dataset is useless operationally.

---

## 5. Non-Goals

The following are explicitly out of scope for v1, with rationale:

1. **Pattern type detection (fan-out, cycle, scatter-gather classification)** — Deferred to v1.1. The IT-AML dataset labels pattern types, making this feasible, but it adds 3-5 days of graph topology work on top of an already significant v1 scope. The attention subgraph visualization provides sufficient explainability for v1.

2. **Real-time streaming inference** — Not needed for the demo use case. Batch or on-demand subgraph inference is sufficient. Streaming would require Kafka or similar, adding infrastructure complexity with no portfolio return at this stage.

3. **Continual / online learning** — v1 trains once and freezes weights. Laundering pattern drift is a real production concern but is a research-grade problem (see arXiv 2503.24259) beyond v1 scope.

4. **API authentication** — The demo API is unauthenticated. Adding OAuth2 or API key auth adds engineering time without demonstrating ML skills. To be revisited if the project is ever used in a real context.

5. **Retraining pipeline** — No automated retraining trigger, drift detector, or CI/CD for models. v1 is train-once, deploy the `.pt` artifact. Retraining requires spinning up Vast.ai again and re-running the training script manually.

6. **Multi-bank or federated setup** — The IT-AML dataset models a single-institution transaction graph. Cross-institution or federated learning is out of scope and would require a fundamentally different data model.

7. **Mobile frontend** — The D3.js frontend targets desktop browsers only. The visualization requires sufficient screen real estate to be useful.

8. **Kubernetes or container orchestration** — The Hetzner deployment uses a single Docker container with Uvicorn. No orchestration needed at this scale.

9. **Frontend design specification** — Visual design details (color palette, typography, SVG iconography) are a separate deliverable, produced after the model and API are functional.

---

## 6. Users and Jobs-to-be-done

### Segment: Reviewer — hiring manager or technical interviewer (P0)

- **J1 — Benchmark scan.** When I open the GitHub README, I want to see the benchmark delta vs. the IBM Multi-GNN baseline within 30 seconds, so I can judge the project against a published bar.
- **J2 — End-to-end demo.** When I open the live demo URL, I want to submit a pre-loaded illicit subgraph and see a risk score plus an attention-based explanation in under 1 second, so I can evaluate end-to-end behaviour.
- **J3 — Explanation drill-down.** When I click a flagged edge, I want the k-hop neighbourhood that justified the flag, so I can judge explanation quality, not just the score.
- **J4 — Evidence audit.** When I skim `BENCHMARKS.md` and the W&B report, I want a per-metric breakdown (F1 / precision / recall / latency) across GraphSAGE → HGT → IBM, so I can audit the two-act narrative on evidence rather than claims.

### Segment: Operator — Dinesh as engineer (P1)

- **J5 — Reproducible resume.** When I resume work after a gap, I want `uv sync && python scripts/train.py --config configs/hgt-v1.yaml` to reproduce the trained model bit-for-bit, so I can iterate without reconstructing the environment from scratch.
- **J6 — Recovery path.** When the live demo breaks, I want `GET /api/v1/health` and a documented rollback command, so recovery does not require debugging under pressure.

### Out of scope

Compliance officers, bank employees, or any real-money AML use. This is a research/portfolio artefact trained on synthetic data and must not be presented as production-ready for real financial institutions.

---

## 7. Use Cases

**Permission model (applies to all use cases below):** unauthenticated public demo. No user session, no per-user rate limit in v1. IP-level rate limit is TBD — see S12 Open Questions.

### Risk tiers and suspicious-edge thresholds

Used by UC1 step 6-7, REQ-013, REQ-018. Defaults below are v1; calibration revisit is tracked in S12.

**Risk tier mapping (illicit probability `p`):**

- **LOW**: `p < 0.30`
- **MEDIUM**: `0.30 ≤ p < 0.70`
- **HIGH**: `p ≥ 0.70`

**Suspicious edge** (for UI red highlighting in UC1 step 6): an edge is "suspicious" if **either** (a) its attention weight is in the top-10 for the queried subgraph (aligned with REQ-011), **or** (b) its attention weight is ≥ 2× the subgraph mean attention.

---

### Use Case 1: Inference — Flag a suspicious wire transfer

**Actor:** Reviewer (see S6 Segment: Reviewer — J2, J3)
**Goal:** Submit a transaction subgraph and receive a risk score with explanation
**Permission:** unauth public demo.

Happy path:

1. User opens the frontend visualization
2. A pre-loaded transaction subgraph from the IT-AML test set is displayed as a D3 force-directed graph
3. User clicks "Analyze" or selects a specific edge (wire transfer)
4. Frontend POSTs the subgraph to `POST /api/v1/predict`
5. API returns per-edge illicit probability, per-edge risk tier, and the top-10 attention subgraph for flagged edges
6. Frontend highlights suspicious edges in red (per thresholds above), proportional to attention weight
7. A sidebar panel shows: risk level (HIGH/MEDIUM/LOW), illicit probability, and which node types (individual/business/bank) appear in the flagged subgraph

Wireframe (placeholder — Figma link to follow per S12):

```
+-------------------------------------------------------+
| graphwash                          [?]  [Load sample] |
+-------------------------------------------------------+
| Canvas (D3 force-directed, pan/zoom)          Sidebar |
|                                               +-----+ |
|      (o)----[edge]----(o)                     | HIGH| |
|       |               |                       |0.84 | |
|       +------(o)------+                       | ... | |
|                                               +-----+ |
+-------------------------------------------------------+
```

Edge cases:

- Subgraph with zero edges → API returns HTTP 422 "subgraph must contain at least one edge"
- All-legitimate subgraph → API returns risk tier LOW for every edge; no edges highlighted
- Very large subgraph (> 1000 edges) → API returns warning recommending subgraph sampling; frontend auto-samples 2-hop neighbourhood (per §15)
- API unreachable → frontend banner "Inference service offline — see /api/v1/health"

---

### Use Case 2: Benchmark inspection — Compare model performance

**Actor:** Reviewer (see S6 Segment: Reviewer — J1, J4)
**Goal:** Understand how graphwash performs vs. the IBM baseline
**Permission:** unauth public demo.

Happy path:

1. User navigates to the README or the frontend's "Model Performance" section
2. A results table shows: GraphSAGE baseline F1, HGT v1 F1, IBM Multi-GNN F1 (published), with precision and recall breakdowns
3. A W&B report link is embedded showing training curves, hyperparameter sweeps, and experiment history
4. Architecture diagram shows the two-act model story: GraphSAGE → HGT

Edge cases:

- README unreachable (GitHub outage) → live demo URL remains functional as fallback viewer
- W&B report link 404 → fallback to `BENCHMARKS.md` in-repo table
- Empty: HGT training not yet complete → table shows GraphSAGE row only with "HGT: pending" marker

---

### Use Case 3: Explanation inspection — Understand a flagged transaction

**Actor:** Reviewer (see S6 Segment: Reviewer — J3)
**Goal:** Understand which accounts and transfers explain a flagged prediction
**Permission:** unauth public demo.

Happy path:

1. User has an edge flagged as HIGH risk from Use Case 1
2. User clicks the flagged edge
3. Frontend calls `GET /api/v1/explain/{edge_id}`
4. API returns the extracted k-hop subgraph with per-edge attention weights
5. Frontend renders: highlighted subgraph, attention weight heatmap on edges, list of involved account node types
6. Sidebar shows: "Why this was flagged: 3 accounts receiving funds from a single source within a 24-hour window"

Edge cases:

- `edge_id` expired from prediction cache → HTTP 404 "edge not found — run predict first" (cross-ref §15)
- Empty signal: attention weights approximately uniform across edges → sidebar banner "Explanation signal weak for this prediction"
- `edge_id` malformed → HTTP 422 with Pydantic error detail

---

### Use Case 4: Health check — Verify system is live

**Actor:** Operator (see S6 Segment: Operator — J6) or automated monitor
**Goal:** Confirm the API is running and the model is loaded
**Permission:** unauth public demo; used by UptimeRobot probe and manual SSH checks.

Happy path:

1. `GET /api/v1/health` returns `{"status": "ok", "model_loaded": true, "model_version": "hgt-v1"}`
2. Response time < 50ms

Edge cases:

- Model weights missing at startup → container fails to boot with explicit error (cross-ref §15); UptimeRobot logs outage
- Health returns 200 but `model_loaded=false` → operator-side P0 alert (see §17 Monitoring plan)
- Upstream VPS network blip → UptimeRobot retries after 2 minutes per §17 thresholds

---

## 8. Functional Requirements

### P0 — Launch Blockers

Data pipeline

- REQ-001: The system must download and preprocess the IBM IT-AML Medium dataset from Kaggle, constructing a `HeteroData` object with three node types (`individual`, `business`, `bank`) and one edge type (`wire_transfer`) with per-edge features: amount, timestamp, currency flag.
- REQ-002: The system must apply stratified train/validation/test splits preserving the ~2% illicit class ratio across splits.
- REQ-003: The system must handle class imbalance explicitly via weighted cross-entropy loss, with the positive class weight computed from the training split label distribution.

GraphSAGE baseline

- REQ-004: The system must train a 2-layer homogeneous GraphSAGE model (collapsing node types into a unified feature vector) as a baseline, logging minority class F1, precision, recall, and AUC to W&B.
- REQ-005: The GraphSAGE baseline must be evaluated on the held-out test set and results committed to the repository as a reproducible artifact.

HGT model

- REQ-006: The system must train a Heterogeneous Graph Transformer (HGT) using `HGTConv` from PyG 2.7, with type-aware attention heads for each node-type pair. Minimum architecture: 2 layers, 4 attention heads, hidden dimension 64. Hyperparameters tuned via W&B Sweeps.
- REQ-007: The HGT model must be trained with early stopping based on validation minority class F1, with patience of 10 epochs.
- REQ-008: The trained HGT model must be serialized as a `.pt` weights file and a `config.yaml` capturing all hyperparameters, random seed, and dataset split configuration sufficient for full reproduction.
- REQ-009: The HGT model must achieve minority class F1 ≥ 0.72 on the IT-AML Medium test set before being considered v1-ready.

Explainability

- REQ-010: For every edge classified as illicit (probability > 0.5), the system must extract the k-hop neighborhood (default k=2) and return per-edge attention weights from the final HGT layer.
- REQ-011: The API response for flagged edges must include a ranked list of top-10 highest-attention edges, identifying source node type, destination node type, and attention score.

API

- REQ-012: The system must expose a FastAPI application with the following endpoints: `POST /api/v1/predict`, `GET /api/v1/explain/{edge_id}`, `GET /api/v1/health`, `GET /api/v1/metrics`.
- REQ-013: `POST /api/v1/predict` must accept a JSON payload shaped as a **raw edge list with an accompanying node list** — `{"nodes": [{"id": str, "type": "individual" | "business" | "bank"}], "edges": [{"src": str, "dst": str, "amount": float, "timestamp": ISO-8601 str, "currency": str}]}` — and return, per edge: (a) illicit probability in `[0.0, 1.0]`, (b) risk tier (`LOW` / `MEDIUM` / `HIGH`, per the thresholds in §7), and (c) for edges with probability > 0.5, the top-10 attention subgraph ordered by attention weight descending (aligned with REQ-011). The API is responsible for lifting the edge/node list into the internal PyG `HeteroData` representation; the client MUST NOT send pre-built adjacency structures.
- REQ-013a: API response schemas MUST conform to the following shapes. All 4xx / 5xx responses MUST use the envelope `{"error": {"code": str, "message": str, "detail": object \| null}}`; Pydantic 422 responses wrap FastAPI's stock `detail` array inside `error.detail`.
  - `POST /api/v1/predict` success (200):
    ```json
    {
      "latency_ms": 134,
      "model_version": "hgt-v1",
      "per_edge": [
        {
          "edge_id": "e_0001",
          "src": "n_42",
          "dst": "n_99",
          "illicit_prob": 0.84,
          "risk_tier": "HIGH",
          "top_attention": [
            {
              "edge_id": "e_0007",
              "src_type": "individual",
              "dst_type": "bank",
              "weight": 0.31
            }
          ]
        }
      ]
    }
    ```
    `top_attention` is `null` when `illicit_prob <= 0.5`.
  - `GET /api/v1/explain/{edge_id}` success (200):
    ```json
    {
      "edge_id": "e_0001",
      "k": 2,
      "subgraph": {
        "nodes": [{ "id": "n_42", "type": "individual" }],
        "edges": [
          {
            "edge_id": "e_0007",
            "src": "n_42",
            "dst": "n_99",
            "attention": 0.31
          }
        ]
      },
      "node_type_summary": { "individual": 3, "business": 1, "bank": 1 },
      "explanation_signal": "strong"
    }
    ```
    `explanation_signal` is `"weak"` when attention weights are approximately uniform (§7 UC3 edge case).
  - `GET /api/v1/health` (200): `{"status": "ok" \| "degraded", "model_loaded": bool, "model_version": str}`.
  - `GET /api/v1/metrics` (200): per REQ-042.
- REQ-014: The API must validate all inputs via Pydantic v2 models, returning HTTP 422 with descriptive error messages for invalid payloads.
- REQ-015: The API must load the trained model weights at startup and serve all inference requests from the in-memory loaded model — no per-request disk reads.
- REQ-016: The API must serve the static frontend files from the same FastAPI application, eliminating the need for a separate web server.

Frontend

- REQ-017: The frontend must render transaction subgraphs as D3.js force-directed graphs with node color coding by type (individual, business, bank) and edge color/thickness driven by attention weights. Supported interactions:
  - Node click → opens side panel with node metadata
  - Edge click → calls `GET /api/v1/explain/{edge_id}` and renders k-hop neighbourhood inline
  - Node hover → tooltip with `node_id` and type
  - Pan → drag on canvas background (D3 zoom behavior)
  - Zoom → mouse wheel / pinch
  - Double-click → reset view to fit-to-viewport
  - Keyboard `Esc` → close side panel
- REQ-018: The frontend must visually distinguish flagged edges (red, pulsing) from clean edges (neutral) using attention weight thresholds.
- REQ-019: The frontend must include a model performance panel displaying GraphSAGE baseline vs. HGT F1 scores with the IBM Multi-GNN published benchmark as a reference line.

Deployment

- REQ-020: The system must be containerized via Docker, with a production `Dockerfile` that: installs Python 3.12 dependencies via `uv`, copies model weights, and starts Uvicorn on port 8000.
- REQ-021: The deployed container must serve the full application (API + static frontend) from a Hetzner VPS with ≥ 16GB RAM, without requiring GPU at inference time.

---

### P1 — Important

- REQ-030: W&B experiment tracking must log: per-epoch train/val loss, minority class F1, precision, recall, AUC, learning rate, attention weight distribution histograms.
- REQ-031: A W&B Sweep must be configured for at minimum: learning rate (log-uniform 1e-4 to 1e-2), number of attention heads (2, 4, 8), and hidden dimension (32, 64, 128).
- REQ-032: The repository must include a `BENCHMARKS.md` file with a results table comparing GraphSAGE, HGT, and IBM Multi-GNN on minority class F1, precision, and recall.
- REQ-033: The frontend must display an architecture diagram (as an inline SVG) showing the graph construction → HGT → explainability → API serving pipeline.
- REQ-034: The API response for `POST /api/v1/predict` must include an inference latency field in milliseconds, measured server-side.

---

### P2 — Nice to Have

- REQ-040: The frontend should include a "load demo subgraph" button pre-populated with a known-illicit subgraph from the IT-AML test set, so reviewers can demo without constructing inputs.
- REQ-041: The API should expose a `GET /api/v1/sample/{pattern}` endpoint returning a pre-loaded example subgraph for each canonical laundering pattern type (fan-out, fan-in, cycle), for demo purposes.
- REQ-042: The `GET /api/v1/metrics` endpoint should return current model metadata: version, training date, test set F1, number of parameters, and average inference latency.

---

## 9. Non-Functional Requirements

### Systems touched

| System                        | Type                | Interaction                        | Phase              |
| ----------------------------- | ------------------- | ---------------------------------- | ------------------ |
| IBM IT-AML dataset (Kaggle)   | External dataset    | Read once (download)               | Phase 0            |
| Vast.ai RTX 5090              | Compute (ephemeral) | Read + write (training)            | Phase 1-2          |
| W&B                           | SaaS tracking       | Write (log), Read (report)         | Phase 1-2          |
| GitHub                        | Source control      | Write (push), Read (clone)         | All                |
| Docker Hub / ghcr             | Container registry  | Write (push), Read (pull)          | Phase 5            |
| Hetzner VPS                   | Runtime host        | Write (deploy), Read (logs)        | Phase 5            |
| Reviewer browser              | Demo client         | Read-only over HTTP                | Runtime            |
| UptimeRobot                   | SaaS uptime monitor | Read (HTTP probe), email alert     | Phase 5+ (runtime) |
| Caddy / Nginx (reverse proxy) | Runtime infra       | Write (config), Read (access logs) | Phase 5 onwards    |

Performance

- p95 inference latency for a single subgraph query (≤ 500 edges): < 200ms on Hetzner 16GB RAM VPS (CPU-only)
- API startup time (model load): < 10 seconds
- `GET /api/v1/health` response time: < 50ms

Reliability

- No formal uptime SLA — this is a demo deployment. Acceptable to restart manually on failure.
- The API must not crash on malformed input — all errors must return structured JSON error responses with HTTP 4xx codes.

Scalability

- Single-user demo serving. No concurrency requirements beyond Uvicorn's default async handling.

Security

- No authentication on the API (documented non-goal). The Hetzner VPS must have SSH key-only access. No secrets committed to the repository — W&B API key managed via environment variable.

Privacy

- IT-AML is fully synthetic data. No real PII is present. No GDPR or data residency concerns apply.

Reproducibility

- Random seeds must be fixed for PyTorch, NumPy, and Python's random module. Full reproduction must be possible from a single `config.yaml` and the committed training script.

Platform

- Training: Ubuntu 24.04 on Vast.ai (CUDA 13.1, PyTorch 2.8.0+cu128, Python 3.12.3)
- Inference: Hetzner VPS (Linux, CPU-only, Docker)
- Frontend: Desktop browsers — Chrome, Firefox, Safari. No mobile support required.

Accessibility

- Not applicable for v1 — this is a technical demo, not a consumer product.

---

## 9a. Architecture and Technical Shape

Hard-to-reverse technical decisions for v1. Items here are **locked** unless explicitly reopened via a new PRD cycle (see "Locked vs. flexible" subsection below).

**This PRD doubles as the v1 technical design document.** §8 pins functional API behavior, §9 pins non-functional constraints, §9a pins architecture and tooling, and §17 pins rollout mechanics. A separate TDD would be pure duplication at this scope. If v2 grows past a solo prototype, split the TDD into its own doc and cross-link.

### Delivery model

**Single-process monolith.** One FastAPI application serves the inference API and the static D3.js frontend from the same Uvicorn worker, packaged as one Docker image (REQ-016, REQ-020, REQ-021). No separate frontend build step, no worker queue, no microservices. Training is offline and ephemeral — it does not run as a service.

### Storage model

**No database.** The service is stateless at the runtime layer:

- Model weights — single `.pt` file baked into the Docker image at build time (REQ-008, REQ-015).
- Configuration — `configs/*.yaml` committed to the repo, loaded at startup.
- No user data, no session state, no per-request persistence. Request/response is transient in memory.
- Logs — written to stdout, captured via `docker logs`.

### Environment model

Three environments for v1. **No preview env** — no per-PR ephemeral deploys.

| Env     | Host                                            | Purpose                                              | Entry point                                                                                |
| ------- | ----------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Local   | Dev laptop (API work) + Vast.ai (training only) | Implementation, model training, notebook exploration | `uv run uvicorn src.api:app --reload` locally; `uv run python scripts/train.py` on Vast.ai |
| Staging | Hetzner VPS, `/beta` path                       | Phase 5a soak (≥24h per §17) before promotion        | `https://<host>/beta`                                                                      |
| Prod    | Hetzner VPS, root path                          | Public demo                                          | `https://<host>/`                                                                          |

### Config and secrets

- **Config** (non-secret): `configs/*.yaml` committed to the repo. Loaded via `pydantic-settings` at startup. Overridable via env vars with a `GW_` prefix.
- **Secrets**: env vars only, never committed. `WANDB_API_KEY`, `KAGGLE_USERNAME`, `KAGGLE_KEY`. On Vast.ai: set per-instance before each session. On Hetzner: injected via a chmod-600 env file outside the repo.
- **Rotation**: manual, low frequency. Documented in the README.

### Logging, metrics, tracing

- **Logging**: `structlog` with JSON renderer to stdout. INFO default, DEBUG via `GW_LOG_LEVEL=debug`. Every request log includes `request_id`, `latency_ms`, `endpoint`, `status`. Captured via `docker logs` on Hetzner.
- **Metrics**: `GET /api/v1/metrics` returns model metadata + latency stats (REQ-042). No Prometheus endpoint in v1 — see §18 upgrade question.
- **Tracing**: **none** in v1. Single-process monolith — distributed tracing has no value. Revisit if/when a worker or second service is added.

### CI baseline

**GitHub Actions, full pipeline on every PR to `main`:**

| Step         | Tool                            | Gate                        |
| ------------ | ------------------------------- | --------------------------- |
| Lint         | `ruff check`                    | Zero warnings               |
| Format check | `ruff format --check`           | Must be clean               |
| Type check   | `mypy --strict`                 | Zero errors                 |
| Tests        | `pytest --cov=src --cov-branch` | Pass + ≥70% branch coverage |

Failing CI blocks merge. No auto-deploy on merge (v1 deploys are manual per §17). Workflow lives at `.github/workflows/ci.yml`.

### Testing baseline

- **Framework**: `pytest` + `pytest-cov`.
- **Layout**: `tests/` mirrors `src/`. Integration tests in `tests/integration/` cover every UC1-UC4 happy path and every §15 edge case.
- **Coverage target**: ≥70% branch coverage, enforced in CI. API/serving code should sit well above 70%; ML training code is lower-bar (science code).
- **Fixtures**: a small IT-AML subset (10-20 transactions, ~5 accounts) checked into `tests/fixtures/` for deterministic API tests. Full-dataset tests gated behind `@pytest.mark.slow` and excluded from default runs.

### Rollback and recovery posture

Declared in §17 "Rollback procedure" — cross-referenced here for completeness. Trigger: any §17 P0 alert. Command: `docker stop && docker run` the previous image tag. Duration: <5 min. Image retention: 3 most recent tags.

### Repo structure (top-level)

Canonical layout. Subdirectories may be added as needed; top-level shape is locked.

```
graphwash/
├── src/
│   ├── api/              # FastAPI app, Pydantic models, endpoints
│   ├── data/             # Dataset loader, preprocessing, graph construction
│   ├── models/           # GraphSAGE baseline, HGT
│   ├── training/         # Training loop, eval, W&B integration
│   ├── explainability/   # Attention subgraph extraction
│   └── config.py         # pydantic-settings
├── static/               # D3.js frontend (HTML, CSS, JS, SVG)
├── configs/              # YAML configs (hgt-v1.yaml, sage-baseline.yaml)
├── scripts/              # train.py, evaluate.py, download_data.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/                 # PRD, setup report, benchmarks
├── .github/workflows/    # ci.yml
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── README.md
```

### Locked vs. flexible

| Locked (new PRD cycle to change)    | Flexible (may evolve in v1)                                     |
| ----------------------------------- | --------------------------------------------------------------- |
| Python 3.12+ runtime                | Hetzner instance type (shared vs. dedicated CPU, §18)           |
| `uv` package manager                | Monitoring vendor (UptimeRobot → Grafana/Prometheus later, §18) |
| FastAPI + Pydantic v2               | Log sampling rate                                               |
| PyTorch 2.8.0+cu128 training stack  | Coverage threshold (may tighten above 70%)                      |
| PyG 2.7.0 + `HGTConv` architecture  | Exact W&B Sweep ranges                                          |
| D3.js v7 (no React)                 | Frontend color palette, typography (§5 non-goal 9)              |
| Single Docker monolith              | CI workflow steps (can add stages)                              |
| Synthetic-data-only (IT-AML Medium) | Kaggle CLI version (forward compatible)                         |
| Unauthenticated public API (v1)     | IP-level rate limit decision (§18)                              |

---

## 10. Constraints

- **Deadline:** v1 demo live on the Hetzner VPS with all §16 exit conditions satisfied by **2026-05-31**. Phase 5b promotion must occur on or before this date; the Phase 5a `/beta` soak must therefore start no later than 2026-05-29 to preserve the ≥24h soak window.
- **Compute budget:** Training must complete within a reasonable Vast.ai session. At $0.406/hr, the target is completing the full training run (baseline + HGT + sweeps) within ~8-12 hours of GPU time (~$4-5). Architecture choices should respect this constraint — the IT-AML Medium dataset, not Large.
- **CUDA compatibility:** ✅ Resolved. System CUDA 13.1 (driver 590.48.01) is forward-compatible with PyTorch 2.8.0+cu128 wheels. PyG extensions (torch-scatter, torch-sparse, torch-cluster) must be installed from `https://data.pyg.org/whl/torch-2.8.0+cu128.html` — not PyPI and not source. Verified on Vast.ai RTX 5090 instance on 2026-04-18.
- **Inference hardware:** Model must run on CPU-only at inference time. Architecture must not rely on CUDA-specific ops that have no CPU fallback in PyTorch 2.8.0.
- **Repository structure:** Single public GitHub repository. All training code, serving code, and frontend must live in the same repo.
- **Dependency management:** `uv 0.11.1` with explicit index routing in `pyproject.toml`. No conda, no raw pip without lockfile. PyTorch and PyG extension indexes must be declared as `explicit = true` with `[tool.uv.sources]` routing to prevent silent PyPI fallback and source compilation.

---

## 11. Assumptions

- **IT-AML Medium is publicly accessible on Kaggle** with the same schema documented in the NeurIPS 2023 paper. If the schema has changed, the data pipeline must be updated before training begins.
- **IBM Multi-GNN baseline F1 of ~0.67** is the published figure from the NeurIPS 2023 paper on the Medium dataset. If this number is on a different split or subset, the comparison table must note the discrepancy.
- **PyTorch 2.8.0+cu128 wheels are compatible with CUDA 13.1.** ✅ Verified on 2026-04-18 on Vast.ai RTX 5090 instance. `torch.cuda.is_available()` returned `True`, GPU tensor ops executed correctly, all PyG extensions loaded cleanly.
- **HGT with attention explainability is feasible on IT-AML Medium in CPU inference.** The 2-layer, hidden-dim-64 architecture is expected to produce a model ≤ 50MB. Larger architectures may require quantization for acceptable CPU latency.
- **The Hetzner VPS has sufficient RAM to load the model and serve requests.** A 16GB RAM instance is assumed to be sufficient for a model in the 10-50MB range with PyG/PyTorch dependencies.

---

## 11a. Spike Plan and Unknowns Retirement

Formal register of load-bearing unknowns. Each entry is either DONE, MUST RUN (with target date + kill signal), or ACCEPTED RISK (with rationale). No critical technical question is allowed to hide behind "we'll figure it out in code."

### Summary

| ID   | Unknown                                                                | Status        | Target                |
| ---- | ---------------------------------------------------------------------- | ------------- | --------------------- |
| S-00 | CUDA 13.1 + PyTorch 2.8.0+cu128 + PyG 2.7.0 compat on Vast.ai RTX 5090 | ✅ DONE       | — (closed 2026-04-18) |
| S-01 | CPU p95 latency feasibility (<200 ms on 500-edge subgraph)             | MUST RUN      | 2026-04-22            |
| S-02 | IT-AML Medium schema matches NeurIPS 2023 paper                        | MUST RUN      | 2026-04-22            |
| S-03 | Hetzner 16 GB instance + Docker + Caddy viability                      | MUST RUN      | 2026-05-05            |
| S-04 | Caddy per-IP rate-limit config + UptimeRobot 2-min probe cadence       | MUST RUN      | 2026-05-06            |
| R-01 | HGT beats IBM Multi-GNN baseline (F1 ≥ 0.72)                           | ACCEPTED RISK | End of Phase 2        |
| R-02 | HGT attention weights are non-degenerate (signal for explainability)   | ACCEPTED RISK | End of Phase 2        |

### S-00 — CUDA / PyTorch / PyG compatibility (DONE)

Closed 2026-04-18 on Vast.ai RTX 5090. `torch.cuda.is_available()` returned true; all PyG extensions (torch-scatter, torch-sparse, torch-cluster) loaded; `HGTConv` smoke test passed. Captured in `docs/graphwash-setup-report.md`. Index routing committed to `pyproject.toml`.

### S-01 — CPU latency micro-spike

- **Unknown:** Can an HGT-class architecture hit <200 ms p95 CPU forward-pass on a 500-edge subgraph? Answering yes-or-no BEFORE Phase 2 full training is the point — a no means we change architecture, not deploy strategy.
- **Method:** Train a tiny HGT (1 layer, 16 hidden dim, 2 heads) on a 1 k-edge subset of IT-AML Medium for ~5 epochs on Vast.ai. Export weights. On a laptop CPU, run a forward pass over a 500-edge random subgraph 100 times; record p50, p95, p99.
- **Success criteria:** Tiny model p95 < 100 ms. (Full model is ~4× the compute of tiny; 100 ms headroom leaves room for the 4× scale-up to still fit under 200 ms.)
- **Kill signal:** Tiny model p95 > 200 ms → full HGT is dead on arrival on CPU. Triggers pre-Phase-2 architecture revision: smaller hidden dim, fewer heads, or INT8 quantization plan.
- **Owner:** Dinesh.
- **Cross-refs:** §4 pillar 3, §9 Performance, §11 assumption 4, §13 risk 4.

### S-02 — IT-AML schema validation

- **Unknown:** Does the Kaggle IT-AML Medium download match the schema documented in the NeurIPS 2023 paper? Closes §11 assumption 1 and §18 Q2.
- **Method:** On a fresh Vast.ai instance, `kaggle datasets download`, unzip, load the first 1 k rows of each CSV with pandas. Record column names, dtypes, null rate, illicit-label distribution. Diff against the paper's Appendix.
- **Success criteria:** Schema matches paper ± trivial column renames (rename map captured in `src/data/schema.py`). Illicit label rate within [1 %, 3 %] of the paper.
- **Kill signal:** Structural divergence (missing columns, different label encoding, different file structure) → REQ-001 data pipeline is rewritten before Phase 1, not discovered mid-Phase-1.
- **Owner:** Dinesh.
- **Cross-refs:** REQ-001, §11 assumption 1, §18 Q2.

### S-03 — Hetzner provision + stub Docker smoke test

- **Unknown:** Does a 16 GB Hetzner instance actually run the stack with sub-30 s cold-start and idle RAM headroom? Subsumes §18 Q5 (instance type choice).
- **Method:** Provision a Hetzner CPX31 (or closest ≥16 GB equivalent). Build a stub Docker image: FastAPI + Pydantic v2 models + a dummy `HGTModel` class returning canned predictions. Deploy behind Caddy with TLS on a throwaway subdomain. Measure container cold-start with `time docker run`, idle RAM via `docker stats`, `/api/v1/health` latency via `curl -w`.
- **Success criteria:** Cold-start < 30 s; idle RAM < 2 GB; health endpoint p95 < 50 ms; Caddy TLS certificate issued by Let's Encrypt within 2 min of first request.
- **Kill signal:** Cold-start > 60 s (indicates model-load pattern needs changes) or idle RAM approaching 16 GB (invalidates §10 Constraint "≥16 GB" — need larger instance or architecture changes). Either outcome forces a Phase 3 / §9a amendment before full implementation.
- **Owner:** Dinesh.
- **Cost:** ~€10/mo ongoing. Accepted as the cost of retiring the deployment unknown early.
- **Cross-refs:** §11 assumption 5, §17 Phase 5, §18 Q5.

### S-04 — Caddy rate-limit + UptimeRobot probe cadence

- **Unknown:** Does the auth-adjacent fallback (per-IP rate limit at the proxy) work with a 5-line Caddy config, and does UptimeRobot's free tier actually support the 2-min probe cadence assumed by §17 monitoring?
- **Method:** (a) Add a `rate_limit` block to the S-03 Caddy config; confirm with `hey -n 100 -c 10` that bursts beyond the threshold are 429'd. (b) Create a UptimeRobot monitor on the stub `/api/v1/health`; deliberately stop the container; confirm alert email lands within 5 min.
- **Success criteria:** Both work as advertised. Rate limit blocks >10 req/s sustained from a single IP; UptimeRobot email reaches `dind.dev@gmail.com` within the §17 response window.
- **Kill signal:** Rate-limit config more complex than 5 lines → rethink §18 Q8 ("is a rate limit even worth it for a demo?"). UptimeRobot free tier doesn't support 2-min → fall back to 5-min cadence and update §17 monitoring thresholds (minor) or switch vendor (larger amendment).
- **Owner:** Dinesh.
- **Cross-refs:** §17 Monitoring plan, §18 Q8.

### R-01 — HGT beats IBM Multi-GNN baseline (ACCEPTED RISK)

- **Status:** ACCEPTED RISK.
- **Rationale:** Not spikeable — **Phase 2 training is the spike.** Running a smoke training on IT-AML Small would consume ~1-2 h of Vast.ai and still wouldn't tell us anything trustworthy about Medium performance (the dataset shifts matter).
- **Mitigation already documented:** §13 risk 2 enumerates the fallback ladder — focal loss, deeper layers, more attention heads, migrate to Large dataset. §17 Phase 2 gate is F1 ≥ 0.72 — if missed, the fallback ladder kicks in before moving to Phase 3.
- **Expected resolution:** End of Phase 2 (~2026-05-10 at the latest given the §10 deadline).

### R-02 — HGT attention weights are non-degenerate (ACCEPTED RISK)

- **Status:** ACCEPTED RISK / emerges from training.
- **Rationale:** Attention tensors exist by HGT construction; whether they carry meaningful signal depends on training dynamics. No pre-training spike can answer this.
- **Mitigation:** §17 Phase 2 gate explicitly requires "attention weights are non-degenerate (not approximately uniform across edges)." If degenerate, §7 UC3 already handles the "explanation signal weak" edge case and the attention-based explainability claim is downgraded in the README rather than blocking the other three pillars.
- **Expected resolution:** End of Phase 2.

---

## 12. Dependencies

| Dependency                  | Type                | Owner  | Availability          | Fallback                          | Notes                                                                                                                                                                                                                                 | Risk                                         |
| --------------------------- | ------------------- | ------ | --------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| IBM IT-AML dataset (Kaggle) | External data       | Dinesh | available             | none — core                       | NeurIPS 2023 paper dataset. Must be downloaded via Kaggle CLI 2.0.1. Schema must match paper documentation.                                                                                                                           | Low — dataset is stable                      |
| PyTorch 2.8.0+cu128         | Core framework      | Dinesh | available             | none — core                       | ✅ Verified. Python 3.12.3 compatible. Installed via `https://download.pytorch.org/whl/cu128` index.                                                                                                                                  | None — verified                              |
| PyG 2.7.0                   | Graph ML            | Dinesh | available             | none — core                       | ✅ Verified. `HGTConv`, `NeighborLoader` confirmed working. Extensions (torch-scatter 2.1.2+pt28cu128, torch-sparse 0.6.18+pt28cu128, torch-cluster 1.6.3+pt28cu128) installed via `https://data.pyg.org/whl/torch-2.8.0+cu128.html`. | None — verified                              |
| uv 0.11.1                   | Dependency mgmt     | Dinesh | available             | pip + `requirements.txt` snapshot | ✅ Verified. `pyproject.toml` with explicit index routing committed. Reproduces environment via `uv sync` on fresh instance.                                                                                                          | None — verified                              |
| Vast.ai RTX 5090            | Compute             | Dinesh | available on demand   | Lambda Labs / RunPod (same cu128) | Training only. CUDA 13.1 / PyTorch cu128 compatibility confirmed. Spin up per training session, destroy after.                                                                                                                        | Low — environment reproducible from lockfile |
| Hetzner VPS                 | Deployment          | Dinesh | not provisioned (S12) | any CPU VPS ≥ 16GB RAM            | CPU-only inference. 16GB RAM assumed sufficient.                                                                                                                                                                                      | Low                                          |
| W&B                         | Experiment tracking | Dinesh | available             | local CSV log + matplotlib        | Free tier sufficient for solo project. API key via env var.                                                                                                                                                                           | Low                                          |
| Kaggle CLI 2.0.1            | Dataset access      | Dinesh | available             | manual download from Kaggle UI    | ✅ Verified installed. Credentials (`~/.kaggle/kaggle.json`) must be configured on each fresh Vast.ai instance before dataset download.                                                                                               | Low                                          |
| D3.js (v7)                  | Frontend            | Dinesh | available (CDN)       | vendored copy in `/static`        | CDN import. No build step required.                                                                                                                                                                                                   | Low                                          |

---

## 13. Risks

| Risk                                                                   | Likelihood | Impact                                  | Mitigation                                                                                                                                                                                                                                                                                     |
| ---------------------------------------------------------------------- | ---------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ~~CUDA 13.0 incompatibility with PyTorch 2.11 cu129 wheels~~           | ~~Medium~~ | ~~High~~                                | ✅ **Resolved 2026-04-18.** PyTorch 2.8.0+cu128 runs cleanly on CUDA 13.1. Use `pyproject.toml` explicit index routing — do not use cu129 wheels.                                                                                                                                              |
| HGT fails to beat IBM Multi-GNN baseline                               | Medium     | Medium — reduces portfolio story impact | The two-act narrative still holds value. Document delta honestly, investigate architectural adjustments (more heads, deeper, focal loss instead of weighted CE). The explainability layer differentiates the project regardless of F1.                                                         |
| IT-AML Medium dataset too large to process on single GPU in memory     | Low        | High — blocks training                  | Use PyG `NeighborLoader` for mini-batch training. Standard approach for large graphs, supported by HGTConv.                                                                                                                                                                                    |
| CPU inference latency exceeds 200ms target                             | Medium     | Low — demo still works, just slower     | Profile bottleneck. Options: model quantization (INT8), reduce k-hop neighborhood size for inference, cache frequent subgraph queries.                                                                                                                                                         |
| Class imbalance causes model to collapse to predicting all-legitimate  | Medium     | High — makes the project useless        | Use weighted cross-entropy with imbalance ratio from training set. Monitor minority class F1, not accuracy, at every validation step. Add focal loss as a fallback.                                                                                                                            |
| Lost environment state from destroyed Vast.ai instance before git push | Low        | Low — recoverable                       | First incident 2026-04-18; since mitigated by committing `pyproject.toml` to `docs/graphwash-setup-report.md`. Recovery procedure: fresh instance → copy `pyproject.toml` from report → `uv sync` → re-download dataset. **First action on every new instance: `git push` before destroying.** |

### Break-question review

Answers to the five scope-clarification break questions, cross-referenced to the sections where the underlying detail lives.

| #   | Break question                                   | Answer                                                                                                                                                                                                                                                  | Cross-ref                                                                     |
| --- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1   | What could make this late?                       | HGT W&B sweeps stalling or NaN-looping; Vast.ai instance loss before `git push`; CUDA/PyG compat drift on a fresh instance; Hetzner VPS provisioning delay cutting into the Phase 5a soak window before the 2026-05-31 deadline.                        | §10 Deadline; §13 rows 2, 6; §15 Model training; §17 Phase 0 "git push first" |
| 2   | What could make this expensive?                  | Training sweeps exceeding the ~8-12h GPU budget (~$4-5); being forced to migrate from IT-AML Medium to Large; needing post-deploy quantization or a second Vast.ai run to recover from a failed training cycle.                                         | §10 Compute budget; §13 row 3; §14 Tradeoff 3                                 |
| 3   | What could make this unsafe?                     | Misrepresenting a synthetic-data portfolio model as production-ready for real AML use; unauthenticated public API abused for scraping or resource exhaustion (rate limit still TBD).                                                                    | §5 Non-goal 4; §6 "Out of scope"; §9 Security; §18 Q on IP-level rate limit   |
| 4   | What could make this much broader than expected? | Scope creep into any of the §5 non-goals — pattern-type detection, real-time streaming, auth, automated retraining, multi-bank / federated, mobile frontend, K8s orchestration, or frontend visual design. Each has a standing "not v1" ruling.         | §5 Non-Goals items 1-9                                                        |
| 5   | What could force an architectural rewrite later? | CPU inference latency > 200ms forcing quantization or model downsize; Hetzner 16GB RAM insufficient forcing a smaller architecture; HGT failing to beat the GraphSAGE baseline forcing a shift to focal loss, deeper layers, or a different aggregator. | §11 Assumptions 4-5; §13 rows 2, 4; §16 "this is not working"                 |

---

## 14. Tradeoffs

Tradeoff 1: HGT vs. GAT for heterogeneous modeling
We considered standard Graph Attention Networks (GAT) with node-type embeddings concatenated to features as an alternative to HGT. GAT is simpler to implement and has more existing AML literature. We chose HGT because it has type-aware attention heads natively — different attention mechanisms for `individual→bank` vs. `business→individual` edge types — which maps directly to the heterogeneous nature of wire transfer networks. The cost is a slightly more complex implementation. The benefit is a cleaner architecture story and a more defensible design choice in interviews.

Tradeoff 2: AttentionExplainer (native) vs. GNNExplainer (post-hoc)
We considered GNNExplainer, which perturbs the graph to measure feature importance. We chose to use the HGT's native attention weights as the explainability signal instead. GNNExplainer adds a separate optimization loop per prediction, significantly increasing inference latency. Attention weights are available as a byproduct of the forward pass at zero additional cost. The tradeoff is that attention weights are not guaranteed to be a theoretically rigorous explanation — they are a proxy. For a demo system, this is an acceptable tradeoff. Documented as a known limitation.

Tradeoff 3: IT-AML Medium vs. Large dataset
IBM provides Small, Medium, and Large variants. The Large dataset would produce a more robust model but requires significantly more training time and GPU memory. Given the $0.406/hr compute constraint and the goal of iterating through hyperparameter sweeps (not just one training run), Medium is the correct choice. The delta in F1 between Medium and Large training sets diminishes with model capacity, and our architecture is 2-layer with hidden dim 64 — not capacity-constrained.

Tradeoff 4: Vanilla HTML/CSS/JS vs. React frontend
We considered React for the frontend. We chose vanilla HTML/CSS/JS + D3.js because: (1) D3 is inherently imperative and fights React's declarative rendering model, (2) no build step means the frontend can be served directly as static files from FastAPI without a bundler, and (3) for an ML engineering portfolio, the absence of React is not a weakness — it's a deliberate choice that keeps the focus on the ML system.

---

## 15. Edge Cases

Data pipeline

- Nodes with no edges (isolated accounts): exclude from the graph. The IT-AML dataset may contain isolated nodes that provide no relational signal.
- Self-loop edges (account transfers to itself): drop. These are artifacts of the simulator and are not meaningful for AML detection.
- Timestamps beyond the simulation window: clamp to the valid range. Do not drop — clamped values are still informative for temporal ordering.

Model training

- If validation F1 does not improve after 10 epochs (early stopping): save the best checkpoint and terminate. Do not continue training on a stalled model.
- If a W&B Sweep trial crashes: log the failure, skip to next trial. Do not halt the sweep.
- NaN loss during training: log and terminate the run. This indicates a learning rate that is too high — the sweep range should be narrowed.

API

- Subgraph with only one node and no edges: return HTTP 422 — minimum subgraph is one edge.
- Edge ID requested in `GET /api/v1/explain/{edge_id}` not found in the most recent prediction cache: return HTTP 404 with message "edge not found — run predict first."
- Model weights file missing at startup: FastAPI must fail to start with a clear error message, not start successfully and fail on first request.

Frontend

- D3 rendering with > 500 nodes: apply automatic subgraph sampling to the nearest 2-hop neighborhood of the selected edge. Display a banner: "Showing 2-hop neighborhood for clarity."
- Disconnected graph components: lay out each component separately in the force simulation. Do not let disconnected components collapse to the origin.

---

## 16. Success Metrics and Measurement Plan

**Primary metric:** Minority class F1 on IT-AML Medium test set ≥ 0.72  
**Guardrail metric:** Illicit class precision ≥ 0.50  
Secondary metrics:

- p95 inference latency < 200ms (measured via FastAPI middleware, logged in `GET /api/v1/metrics`)
- W&B training run reproducible from committed config (verified manually)
- Live demo URL returns HTTP 200 on `GET /api/v1/health`

Definition of "this is working":

- HGT F1 > GraphSAGE baseline F1 > 0.67 (IBM benchmark) on the same test split
- Live demo running on Hetzner VPS, reachable at public URL
- README contains benchmark table, architecture diagram, W&B report link, and demo URL

Definition of "this is not working":

- HGT F1 ≤ GraphSAGE baseline — indicates the heterogeneous architecture is not providing signal over a simpler model. Investigate: node feature quality, type-aware edge features, number of HGT layers.
- Inference latency consistently > 500ms on Hetzner — investigate: model size, subgraph size caps, quantization.

### Sign-off

**Sign-off owner:** Dinesh.

**Exit conditions (all must hold before the PRD closes):**

1. HGT minority-class F1 ≥ 0.72 on the IT-AML Medium test split, sustained across 2 consecutive retraining runs.
2. Live demo URL returns HTTP 200 on `GET /api/v1/health` with p95 latency < 200 ms measured over a 5-minute rolling window (same window used by the §17 Monitoring plan).
3. At least one external reviewer has submitted a successful prediction via the live UI and received an explainability response.

**Status transitions:**

- `Draft` → `In Review` — once cycle 1 of `prd-review` edits apply.
- `In Review` → `Approved` — when `prd-review` issues verdict `APPROVED`.
- `Approved` → `Shipped` — when all three exit conditions above hold.
- `Shipped` → `Deprecated` — if superseded by a v2 PRD.

---

## 17. Rollout and Implementation Considerations

### Phase 0 — Environment and data setup

- ✅ CUDA 13.1 / PyTorch 2.8.0+cu128 compatibility verified on Vast.ai RTX 5090
- ✅ `uv 0.11.1` environment configured with explicit index routing in `pyproject.toml`
- ✅ PyG 2.7.0 + extensions (torch-scatter, torch-sparse, torch-cluster) verified
- ✅ Kaggle CLI 2.0.1 installed
- ⬜ **Next session:** Spin up fresh Vast.ai instance, `uv sync` from committed `pyproject.toml`, configure Kaggle credentials, download IT-AML Medium dataset
- ⬜ Validate dataset schema against NeurIPS 2023 paper
- ⬜ Construct `HeteroData` object, verify graph statistics match paper
- ⬜ **Commit and push before destroying instance**
- **Gate to Phase 1:** `HeteroData` object constructed and graph statistics match paper documentation within ±5%.

### Phase 1 — GraphSAGE baseline

- Implement data pipeline: node/edge feature extraction, stratified splits, class weight computation
- Train 2-layer GraphSAGE baseline with W&B logging
- Evaluate on test set, commit results to `BENCHMARKS.md`
- This phase is the gate before touching HGT — baseline must run cleanly end-to-end
- **Gate to Phase 2:** GraphSAGE minority-class F1 > 0.60 on test split. Below this the baseline has no signal and HGT is moot — stop and investigate features / splits.

### Phase 2 — HGT model

- Implement HGT with `HGTConv`, type-aware attention heads
- Run W&B Sweep over learning rate, heads, hidden dim
- Evaluate best checkpoint on test set
- Extract attention weights, verify explainability output is structurally correct
- **Gate to Phase 3:** HGT minority-class F1 ≥ 0.72 (REQ-009) AND attention weights are non-degenerate (not approximately uniform across edges).

### Phase 3 — API

- Implement FastAPI application: predict, explain, health, metrics endpoints
- Pydantic v2 request/response models
- Model load at startup, inference on CPU
- Local integration test: end-to-end from raw JSON payload to response
- **Gate to Phase 4:** local integration test passes end-to-end (JSON in → JSON out) for every UC1-UC4 happy path and every §15 edge case.

### Phase 4 — Frontend

- Implement D3.js force-directed graph visualization
- Wire up to API endpoints
- Performance panel with benchmark comparison table
- Architecture SVG diagram
- **Gate to Phase 5:** every UC1-UC4 happy path renders correctly in Chrome, Firefox, and Safari on desktop.

### Phase 5 — Deployment (two sub-phases)

#### Phase 5a — Staging behind `/beta`

- Write production `Dockerfile`
- Build image tagged `graphwash:beta-<git-sha>` and deploy behind `/beta` path on Hetzner VPS
- Soak for ≥ 24h of self-directed smoke testing covering UC1-UC4 happy paths + every §15 edge case
- **Gate to Phase 5b:** all S4 P0 metrics hold over the soak window (F1 ≥ 0.72 on offline eval, p95 latency < 200ms, `/api/v1/health` returns 200) AND zero 5xx responses in the staging request log.

#### Phase 5b — Promote to root

- Re-tag image as `graphwash:v1.0` (kept immutable)
- Switch the reverse proxy (Caddy/Nginx) upstream from `/beta` to root
- Keep the previous running container as `graphwash:v<prev>` for rollback
- README finalisation: benchmark table, W&B report link, demo URL, architecture diagram, setup instructions

#### Rollback procedure

- **Trigger:** any P0 alert from the Monitoring Plan below, OR a manual decision.
- **Command:** `docker stop graphwash && docker run -d --name graphwash -p 8000:8000 graphwash:v<prev>`
- **Expected duration:** < 5 minutes end-to-end.
- **Rollback window:** indefinite while v1 is the canonical demo.
- **Data migration:** none — inference is stateless, there is no DB.
- **Image retention:** keep the 3 most recent tagged images on the VPS to support rollback across two versions.

#### Monitoring plan

| Signal                           | Threshold                   | Response              |
| -------------------------------- | --------------------------- | --------------------- |
| `GET /api/v1/health` HTTP status | ≠ 200 for > 2 minutes       | Rollback (P0 alert)   |
| p95 latency (5-minute window)    | > 500 ms                    | Investigate (P1)      |
| p95 latency (5-minute window)    | > 200 ms for > 1 hour       | Rollback (P0)         |
| 5xx response rate                | > 1% of requests            | Rollback (P0)         |
| Periodic F1 re-eval (weekly)     | < 0.68 (below IBM baseline) | Investigate (P1)      |
| Disk usage                       | > 80% of VPS disk           | Prune old images (P2) |

Tooling (v1): UptimeRobot monitors `/api/v1/health`; `docker logs` tailed via SSH; a weekly manual F1 eval script re-runs evaluation against the held-out test split. Alerting: email to `dind.dev@gmail.com` on any UptimeRobot P0.

### Phase 6 — v1.1 (post-launch)

- Pattern type detection: graph topology classifier for fan-out, fan-in, cycle, scatter-gather
- Evaluate pattern detector against IT-AML ground truth pattern labels

---

## 18. Open Questions

| Question                                                                                                                       | Why it matters                                                                                                                                                                               | Owner      | Target resolution                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| ~~Is PyTorch 2.11 cu129 backward-compatible with CUDA 13.0 on the RTX 5090?~~                                                  | ~~Blocks all training.~~                                                                                                                                                                     | ~~Dinesh~~ | ✅ **Resolved 2026-04-18.** Use PyTorch 2.8.0+cu128. Verified clean on RTX 5090 / CUDA 13.1.              |
| ~~What is the exact schema of the IT-AML Medium dataset files as downloaded from Kaggle?~~                                     | ~~Determines data pipeline implementation — column names, dtypes, file structure.~~                                                                                                          | ~~Dinesh~~ | Absorbed into §11a spike S-02 (MUST RUN by 2026-04-22).                                                   |
| What is the exact published IBM Multi-GNN F1 on IT-AML Medium vs. Small?                                                       | Determines the comparison baseline in `BENCHMARKS.md`. Must compare on the same dataset variant.                                                                                             | Dinesh     | 2026-04-30                                                                                                |
| ~~Should `POST /api/v1/predict` accept a raw edge list or a pre-built adjacency structure?~~                                   | ~~Affects API ergonomics and frontend integration complexity.~~                                                                                                                              | ~~Dinesh~~ | ✅ **Resolved 2026-04-18.** Pinned to raw edge list + node list in REQ-013; server lifts to `HeteroData`. |
| ~~What is the Hetzner instance type (shared CPU vs. dedicated)?~~                                                              | ~~Affects inference latency baseline. Shared CPU introduces variance against the 200 ms p95 target.~~                                                                                        | ~~Dinesh~~ | Absorbed into §11a spike S-03 (MUST RUN by 2026-05-05) — instance selection is the spike's output.        |
| Should the risk-tier thresholds (LOW/MEDIUM/HIGH) be re-calibrated against test-set distribution after HGT training completes? | v1 thresholds (0.30, 0.70) are defensible defaults but may need calibration to match the real illicit probability distribution.                                                              | Dinesh     | 2026-05-02                                                                                                |
| When is the Figma wireframe review for the D3 frontend complete and the Figma link added to S1 `linked docs`?                  | Confirms UC1-UC4 UI flows against a designed artefact before Phase 5a staging.                                                                                                               | Dinesh     | 2026-05-10                                                                                                |
| Is an IP-level rate limit required on the public demo to prevent abuse?                                                        | Permission model in §7 notes rate limit TBD. A public unauth endpoint without limits risks abuse. Feasibility validated by §11a spike S-04; "should we enable it in v1?" remains a decision. | Dinesh     | 2026-05-15                                                                                                |
| Should monitoring upgrade from UptimeRobot + manual logs to Grafana/Prometheus post-launch?                                    | v1 monitoring is deliberately minimal. Upgrade only if demo load or downtime sensitivity warrants.                                                                                           | Dinesh     | 2026-06-01                                                                                                |

---

## 19. Phase / Epic Breakdown

Per-phase budgets updated 2026-04-18 to match the granular task list (`docs/graphwash-task-list.md`). Task-list figures are raw per-phase sums in 0.25d buckets; focused-total absorbs ~2.75d via the parallelism rules in the task-list design spec §4.3.

| Phase                                       | Budget (raw) | REQs / scope                                                                                         |
| ------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------- |
| Pilot — Repo & Infrastructure               | ~7d          | Repo, branch protection, CI, pre-commit/pre-push, labels, templates, Docker stub, S-03, S-04         |
| Phase 0 — Environment & Data                | ~3d          | REQ-001, REQ-002, REQ-003, S-02, S-01                                                                |
| Phase 1 — GraphSAGE Baseline                | ~3.5d        | REQ-004, REQ-005, REQ-030, Q-03                                                                      |
| Phase 2 — HGT Model                         | ~5.5d        | REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-031, Q-04, R-01, R-02                      |
| Phase 3 — API                               | ~4d          | REQ-012, REQ-013, REQ-013a, REQ-014, REQ-015, REQ-016, REQ-034, REQ-042                              |
| Phase 4 — Frontend                          | ~4d          | REQ-017, REQ-018, REQ-019, REQ-033, REQ-040 (deferred to v1.0.1), REQ-041 (deferred to v1.0.1), Q-05 |
| Phase 5a — Staging /beta                    | ~2.5d        | REQ-020, REQ-021, Q-06, soak ≥24h                                                                    |
| Phase 5b — Promote to root                  | ~1.5d        | REQ-032, Q-07 (deferred), v1.0 ship gate                                                             |
| **Raw total**                               | **~29d**     | —                                                                                                    |
| **Focused total (after ~2.75d absorption)** | **~26d**     | —                                                                                                    |

**Timeline feasibility.** From 2026-04-18 to the PRD §10 deadline of 2026-05-31 is 43 calendar days → ~24 focused engineering days at 4 focused days/week. The focused total of ~26d is **~2d over the window**. Mitigation:

1. Phases with compressible slack (T-070 soak wall-clock runs in background; spike runs on Vast.ai can overlap with frontend work on local machine) recover ~1-2d in practice.
2. If the gap widens during execution, the further-trim candidates are T-045 attention ADR (0.25d), T-062 performance panel (0.25d), and simplification of Phase 2 sweep tooling (~0.5d).
3. The Task 14 trim pass in the task list already deferred REQ-040 and REQ-041 (T-064) and reduced T-040 sweep runs from ≥12 to ≥6 and dropped Safari from T-065.

**Phase 6 — v1.1 (post-launch).** Pattern Type Detection (graph topology classifier for fan-out / fan-in / cycle / scatter-gather patterns) — ~3-5d. Scheduled post-2026-05-31; tasks allocated in a dedicated v1.1 planning cycle (see task list Phase 6 stub).
