# graphwash — Developer Guide

Local setup, running the app, testing, and project-specific conventions.

Pairs with:

- Workspace governance: `/Users/Dinesh/dev/CLAUDE.md` (Protocol Zero, git workflow, language-wide standards)
- Python standards skill: `python-writing-standards` (3.12+, Ruff, mypy strict, pydantic v2, uv)
- PRD: `docs/graphwash-prd.md` — §9a Architecture and Technical Shape pins all tooling choices

This guide covers project-specific additions on top of those baselines.

---

## 1. Prerequisites

| Tool | Version | Why |
| ---- | ------- | --- |
| Python | 3.12+ | Runtime (PRD §10) |
| `uv` | 0.11.1+ | Dependency manager (PRD §10) |
| Docker | 24+ | Local container smoke test; Hetzner deploy parity |
| Git | any | Source control |
| Kaggle CLI | 2.0.1+ | Dataset download (only needed on training hosts) |

Recommended but optional:

- Ruff (installed via `uv sync` — no global install needed)
- VS Code or Cursor with Pylance + Ruff extensions

---

## 2. First-time setup

```bash
git clone git@github.com:<org>/graphwash.git
cd graphwash

# Install dependencies (creates .venv, resolves from uv.lock)
uv sync

# Copy the env template and fill in secrets
cp .env.example .env
# Edit .env — set WANDB_API_KEY, KAGGLE_USERNAME, KAGGLE_KEY if training locally

# Download the test fixture subset (small, checked into tests/fixtures)
# No download needed — fixtures are committed.

# Verify the tooling chain before first commit
uv run ruff check
uv run ruff format --check
uv run mypy --strict src
uv run pytest
```

---

## 3. Running the API locally

```bash
uv run uvicorn src.api:app --reload --port 8000
```

- Open `http://localhost:8000/` for the frontend.
- Health check: `curl http://localhost:8000/api/v1/health` → `{"status": "ok", "model_loaded": true, ...}`.
- API docs: `http://localhost:8000/docs` (FastAPI auto-generated OpenAPI UI).

Model weights are expected at the path specified in `configs/hgt-v1.yaml`. For local dev without a trained model, point the config at a stub or use the `GW_USE_STUB_MODEL=true` env var (returns deterministic dummy predictions).

---

## 4. Running tests

```bash
# Full test suite, with branch coverage (must be ≥70%)
uv run pytest

# Only fast tests (default) — skips @pytest.mark.slow
uv run pytest

# Include the slow full-dataset tests (requires the IT-AML Medium dataset)
uv run pytest -m "slow or not slow"

# Integration tests only
uv run pytest tests/integration/

# Single file, verbose
uv run pytest tests/integration/test_predict.py -v
```

Coverage reports write to `htmlcov/` — open `htmlcov/index.html` to explore.

---

## 5. Training the model

Training runs on Vast.ai, not locally. See `docs/graphwash-setup-report.md` for instance bootstrap steps.

```bash
# On a fresh Vast.ai instance (Python 3.12, CUDA 13.1)
uv sync
export WANDB_API_KEY=...
export KAGGLE_USERNAME=... KAGGLE_KEY=...

uv run python scripts/download_data.py --size medium
uv run python scripts/train.py --config configs/hgt-v1.yaml

# Before destroying the instance
git add -A && git commit -m "chore(training): run <run-id>" && git push
```

**First action on every fresh instance:** push the repo before doing anything destructive (PRD §13 risk 6).

---

## 6. Deployment (Hetzner)

```bash
# Build
docker build -t graphwash:$(git rev-parse --short HEAD) .

# Run locally to smoke-test
docker run --rm -p 8000:8000 graphwash:$(git rev-parse --short HEAD)

# Push to registry and deploy (per PRD §17 Phase 5)
```

Full deploy + rollback procedure: PRD §17.

---

## 7. Project conventions

Project-specific additions on top of workspace `dev/CLAUDE.md` and the `python-writing-standards` skill.

### Layout

Top-level repo shape is **locked** per PRD §9a. Do not add new top-level directories without updating the PRD.

### Dependency and lockfile policy

- `uv.lock` is source of truth for the environment and is committed.
- Regenerate only via `uv lock --upgrade-package PKG` for a targeted bump, or `uv add PKG` / `uv remove PKG` when the dep set changes.
- Never hand-edit `uv.lock`.
- CI and training hosts run `uv sync --frozen`; drift from the lockfile is a build failure, not a warning.
- PyTorch and PyG extension indexes are pinned `explicit = true` in `pyproject.toml`. Do not remove the routing; source builds on Vast.ai wasted time in Phase 0.
- The lockfile resolves for two platforms (`tool.uv.required-environments`): Linux x86_64 (cu128 wheels for training and Hetzner deploy) and Darwin arm64 (PyPI CPU wheels for local dev). PyG extensions are Linux-only via `sys_platform == 'linux'` markers.

### Imports

- Use absolute imports rooted at `src.` (e.g. `from src.models.hgt import HGTModel`).
- No relative imports across package boundaries.

### Config access

- Never read env vars directly outside `src/config.py`. All config goes through `pydantic-settings`.
- Config keys use the `GW_` prefix (e.g. `GW_MODEL_PATH`, `GW_LOG_LEVEL`).

### Logging

- `structlog.get_logger()` only. No direct `logging.getLogger` calls in application code.
- Every log line must include `request_id` (auto-bound via middleware) and the endpoint name for API-path logs.
- Never log user-supplied payloads in full at INFO; redact at the field level or log at DEBUG.

### Tests

- Integration tests live under `tests/integration/`. They MUST use the committed fixtures, not live Kaggle data.
- Tests requiring the full IT-AML Medium dataset must be marked `@pytest.mark.slow` and excluded from the default run.
- Test names describe the scenario in full sentences (workspace rule): `test_predict_returns_high_tier_for_known_illicit_subgraph`.

### Branching and commits

- Follows workspace governance (`dev/CLAUDE.md` — conventional commits, never commit without permission, never push to `main`).
- Training-run commits use `chore(training): run <wandb-run-id>` so W&B run IDs are searchable from `git log`.

### Pre-commit hooks

#### Setup

```bash
uv sync --extra dev
uv run pre-commit install
```

`uv run pre-commit install` wires both the `pre-commit` and `commit-msg`
git hooks in one command because `.pre-commit-config.yaml` sets
`default_install_hook_types: [pre-commit, commit-msg]`.

Pre-push stage installs separately because `default_install_hook_types`
only covers commit and commit-msg. After the initial
`uv run pre-commit install`, run once per clone:

```bash
uv run pre-commit install --hook-type pre-push
```

Both installs are idempotent. First pre-push invocation downloads no
new repos (the pre-push hooks are `repo: local`) but does warm
`.mypy_cache/`, which makes the first push on a fresh clone
noticeably slower than subsequent pushes. The cache is gitignored, so
this repeats on every new clone (including Vast.ai instances).

#### Hook inventory

**`pre-commit/pre-commit-hooks`** (pre-commit stage)

- `trailing-whitespace`: strips trailing spaces. Markdown hard-break
  double-spaces are preserved via `--markdown-linebreak-ext=md`.
- `end-of-file-fixer`: ensures files end with a newline.
- `check-yaml`: parses YAML files for syntax errors.
- `check-toml`: parses TOML files for syntax errors.
- `check-merge-conflict`: rejects files containing conflict markers.
- `check-added-large-files`: blocks files over 500 KB. `docs/figures/`
  is excluded to allow screenshots and histogram exports.
- `check-case-conflict`: catches case-only filename collisions.

**`astral-sh/ruff-pre-commit`** (pre-commit stage)

- `ruff-format`: applies the Ruff formatter.
- `ruff-check --fix`: applies auto-fixable lint rules.

Both read `[tool.ruff]` from `pyproject.toml`.

**`compilerla/conventional-pre-commit`** (commit-msg stage)

Validates that the commit subject matches `type(scope): description`
shape.

**`repo: local` `enforce-scope`** (commit-msg stage)

A local shell hook (`scripts/check-commit-scope.sh`) that regex-validates
the scope field. Valid scopes are a `t-NNN` task ID or the literal
`training`. The scope is mandatory; the `!` breaking-change marker is
optional.

**`repo: local` pre-push hooks** (pre-push stage)

- `mypy-strict`: runs `uv run mypy --strict src` project-wide against
  `[tool.mypy] strict = true`. Catches type regressions before push;
  CI (T-009) re-runs it as the hard gate.
- `pytest-full`: runs `uv run pytest -q --no-cov` over the full
  `tests/` suite. The `--no-cov` flag is hook-specific: bare
  `uv run pytest` inherits `addopts = "... --cov=src --cov-branch ..."`
  from `[tool.pytest.ini_options]` and enforces the 70% floor from
  `[tool.coverage.report]`, which is what CI (T-009) runs and what a
  developer gets locally when they invoke pytest directly. The hook
  opts out so a mid-feature push (new module, tests not yet written)
  is not blocked by a coverage drop the CI gate will still catch at
  PR time.

#### Commit message format

Full convention in `CLAUDE.md` §8. Summary:

- **Types:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `infra`,
  `ops`, `spike`.
- **Scope:** `t-NNN` task ID, or `training` for Vast.ai run commits.
  Scope is not optional.
- **Subject:** imperative mood, under 72 characters.

Examples:

```text
infra(t-007): wire pre-commit hooks
feat(t-024): construct HeteroData from IT-AML edges
chore(training): run lucid-sweep-42
```

#### Version bumping

Run `uv run pre-commit autoupdate` on demand or quarterly to pull the
latest pinned revs. Never land an autoupdate in the same PR as code
changes: it goes in its own PR so the rev diff is reviewable in
isolation.

#### Bypass policy

`--no-verify` is prohibited per `CLAUDE.md` §8. If a hook fails, fix the
hook or the code at root. Hook regressions are tracked as a follow-up
`t-NNN` task, not worked around.

### Model versioning

- Trained models are tagged `hgt-v<semver>` (e.g. `hgt-v1.0`). The current production tag is surfaced in `GET /api/v1/health` as `model_version`.
- Never overwrite a tagged model's `.pt` file. New version → new tag.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| `ModuleNotFoundError: torch_scatter` on local dev | PyG extensions not installed (expected locally — CPU-only dev uses the non-extension code path) | Set `GW_SKIP_PYG_EXTENSIONS=true` in `.env` or install matching CPU wheels |
| `KaggleApiHTTPError: 403` | Kaggle creds not set | `export KAGGLE_USERNAME=... KAGGLE_KEY=...` |
| `/api/v1/health` returns `model_loaded: false` | Weights file missing at config path | Check `configs/hgt-v1.yaml` → `model_path`; download or train |
| Uvicorn serves frontend 404 | Static files mount path wrong | Verify `static/` exists and `src/api/__init__.py` mounts it |
| Pre-commit fails on a clean checkout | Stale hook install | `uv run pre-commit clean && uv run pre-commit install` |

---
