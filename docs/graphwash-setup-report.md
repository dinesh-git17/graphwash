# graphwash — Environment Setup Report

**Date:** 2026-04-18
**Remote host:** `root@79.112.17.186:56372` (Vast.ai)
**Project root:** `/root/graphwash/`

---

## Instance

| Field                | Value                                                        |
| -------------------- | ------------------------------------------------------------ |
| OS                   | Linux `a79086bf542a` 6.8.0-58-lowlatency (Ubuntu 22.04 base) |
| GPU                  | NVIDIA GeForce RTX 5090 (32 GB, reported 33.7 GB)            |
| NVIDIA driver        | 590.48.01                                                    |
| System CUDA (driver) | 13.1                                                         |
| `nvcc`               | 13.1.115 (release 13.1, built 2025-12-16)                    |
| Python               | 3.12.3                                                       |
| `uv`                 | 0.11.1                                                       |
| Disk (`/`)           | 32 GB total, ~32 GB free at setup                            |

The host advertises CUDA 13.1 at the driver/toolkit layer, but PyTorch 2.8.0 ships
with CUDA 12.8 runtime libraries bundled in its wheel. Forward-compat works
because the 590.x driver supports CUDA 12.x runtimes.

---

## Installed stack

Package manager: `uv` with `--no-build` enforced on every install/lock/sync to
block any source compilation.

| Package           | Version          |
| ----------------- | ---------------- |
| `torch`           | 2.8.0+cu128      |
| `torchvision`     | 0.23.0+cu128     |
| `torchaudio`      | 2.11.0+cu128     |
| `torch-geometric` | 2.7.0            |
| `torch-scatter`   | 2.1.2+pt28cu128  |
| `torch-sparse`    | 0.6.18+pt28cu128 |
| `torch-cluster`   | 1.6.3+pt28cu128  |
| `numpy`           | 2.4.4            |
| `scipy`           | 1.17.1           |
| `kaggle`          | 2.0.1            |
| `kagglesdk`       | 0.1.19           |

Bundled NVIDIA runtime wheels (pulled automatically by torch):
`nvidia-cublas-cu12==12.8.4.1`, `nvidia-cudnn-cu12==9.10.2.21`,
`nvidia-nccl-cu12==2.27.3`, `nvidia-cusparselt-cu12==0.7.1`, `triton==3.4.0`,
plus the usual cuFFT / cuSOLVER / cuSPARSE / NVRTC / cuRAND / cuPTI / NVJITLINK /
NVTX / cuFILE cu12 packages.

---

## CUDA version alignment

Requirement: the CUDA tag used for the PyG wheel URL must exactly match
`torch.version.cuda` at runtime.

| Source               | Value                                             |
| -------------------- | ------------------------------------------------- |
| `torch.version.cuda` | `12.8`                                            |
| PyG wheel index URL  | `https://data.pyg.org/whl/torch-2.8.0+cu128.html` |
| Extension wheel tag  | `+pt28cu128`                                      |

`12.8` collapsed to `cu128` matches the URL suffix and the wheel local-version
tag on all three extensions. Verified before the PyG extensions were installed.

---

## `pyproject.toml`

```toml
[project]
name = "graphwash"
version = "0.1.0"
description = "Wire transfer AML detection via Heterogeneous GNNs"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "torch==2.8.0",
    "torchvision>=0.23.0",
    "torchaudio>=2.11.0",
    "torch-geometric>=2.7,<2.8",
    "torch-scatter>=2.1.2",
    "torch-sparse>=0.6.18",
    "torch-cluster>=1.6.3",
    "kaggle>=2.0.1",
]

[tool.uv.sources]
torch         = { index = "pytorch" }
torchvision   = { index = "pytorch" }
torchaudio    = { index = "pytorch" }
torch-scatter = { index = "pyg" }
torch-sparse  = { index = "pyg" }
torch-cluster = { index = "pyg" }

[[tool.uv.index]]
name     = "pytorch"
url      = "https://download.pytorch.org/whl/cu128"
explicit = true

[[tool.uv.index]]
name     = "pyg"
url      = "https://data.pyg.org/whl/torch-2.8.0+cu128.html"
format   = "flat"
explicit = true
```

`explicit = true` on both indexes plus the `[tool.uv.sources]` routing means the
torch family can only resolve from the PyTorch cu128 index and the three PyG
extensions can only resolve from the PyG cu128 wheel index. Neither set can
silently fall through to PyPI.

---

## Validation output

Ran inside the project with `uv run python validate.py`:

```
PyTorch:          2.8.0+cu128
PyG:              2.7.0
CUDA available:   True
GPU:              NVIDIA GeForce RTX 5090
VRAM:             33.7 GB
GPU tensor op:    torch.Size([1000, 1000]) OK
HGTConv import:   OK
torch_scatter:    2.1.2+pt28cu128
torch_sparse:     0.6.18+pt28cu128
torch_cluster:    1.6.3+pt28cu128
torch.version.cuda: 12.8
```

Kaggle CLI:

```
$ uv run kaggle --version
Kaggle CLI 2.0.1
```

---

## No-source-compilation evidence

- Every `uv add` / `uv lock` / `uv sync` ran with `--no-build`. `uv` raises on
  sdist fallback instead of compiling.
- All three extension wheels carry the `+pt28cu128` local-version tag. That tag
  is stamped by the PyG release automation; a local source build would not
  produce it.
- Install times for the extensions totalled ~400 ms. A from-source CUDA build
  of any of these would take several minutes on this box.
- First attempt to run `uv add kaggle` before the persistent `pyg` index was
  configured in `pyproject.toml` failed with a clear source-build error
  (`ModuleNotFoundError: No module named 'torch'` during a `torch-cluster`
  build). This confirms the `--no-build` guard actually blocks source paths:
  once the `pyg` index was added and pinned, re-locking succeeded without a
  build.

---

## How to use the environment

```bash
ssh -p 56372 root@79.112.17.186 -L 8080:localhost:8080
cd ~/graphwash
uv run python <script.py>
uv run kaggle <command>
```

`uv sync` will re-establish the exact lockfile if the venv is ever wiped.

---

## Open items

- **Kaggle credentials.** `kaggle` CLI is installed but not configured. Drop
  `~/.kaggle/kaggle.json` on the instance (or export `KAGGLE_USERNAME` /
  `KAGGLE_KEY`) before pulling any dataset.
- **Git remote.** `uv init` created a local git repo at `~/graphwash`; no
  remote is wired up yet.
- **Nothing in `~/graphwash`** besides `pyproject.toml`, `uv.lock`, `main.py`
  (stub), `README.md` (empty), `.gitignore`, and `validate.py`. Project code
  has not been added yet.
