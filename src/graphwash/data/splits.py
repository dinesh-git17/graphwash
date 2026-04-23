"""Deterministic stratified train/val/test splits for the IT-AML HeteroData.

Implements REQ-002: edge-level stratified splits over supervised
wire_transfer edges preserving the observed illicit class ratio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
from torch_geometric.data import HeteroData

if TYPE_CHECKING:
    from torch import Tensor

_RATIO_SUM_TOLERANCE = 1e-6
_RATIO_COUNT = 3
_EDGE_INDEX_ROW_COUNT = 2
_SPLIT_TRAIN = 0
_SPLIT_VAL = 1
_SPLIT_TEST = 2


def _validate_ratios(ratios: tuple[float, float, float]) -> None:
    """Validate ``ratios`` fail-fast."""
    if len(ratios) != _RATIO_COUNT:
        msg = f"ratios must contain exactly three entries, got {len(ratios)}"
        raise ValueError(msg)
    for r in ratios:
        if not (torch.isfinite(torch.tensor(r)).item() and r >= 0):
            msg = f"ratios must be finite and non-negative, got {ratios!r}"
            raise ValueError(msg)
    total = sum(ratios)
    if abs(total - 1.0) > _RATIO_SUM_TOLERANCE:
        msg = f"ratios must sum to 1.0 within 1e-6, got {total!r}"
        raise ValueError(msg)


def _check_cpu_device(data: HeteroData) -> None:
    """Reject non-CPU input at the contract boundary."""
    sample = None
    for edge_type in data.edge_types:
        if edge_type[1] == "wire_transfer":
            sample = data[edge_type].y
            break
    if sample is None:
        for node_type in data.node_types:
            if hasattr(data[node_type], "x"):
                sample = data[node_type].x
                break
    if sample is None:
        return
    device_type = sample.device.type
    if device_type != "cpu":
        msg = f"stratified_split requires CPU tensors; got device {device_type!r}"
        raise ValueError(msg)


def _build_supervision_pool(
    data: HeteroData,
) -> tuple[list[tuple[str, str, str]], Tensor, Tensor, Tensor]:
    """Build the global supervision pool over source-present wire_transfer edges."""
    source_triplets: list[tuple[str, str, str]] = [
        et for et in data.edge_types if et[1] == "wire_transfer"
    ]
    y_parts: list[Tensor] = []
    triplet_parts: list[Tensor] = []
    local_parts: list[Tensor] = []
    for triplet_idx, triplet in enumerate(source_triplets):
        y_t = data[triplet].y
        n_t = int(y_t.numel())
        if n_t == 0:
            continue
        y_parts.append(y_t)
        triplet_parts.append(
            torch.full((n_t,), triplet_idx, dtype=torch.long),
        )
        local_parts.append(torch.arange(n_t, dtype=torch.long))
    if y_parts:
        y_global = torch.cat(y_parts)
        triplet_of = torch.cat(triplet_parts)
        local_of = torch.cat(local_parts)
    else:
        y_global = torch.empty(0, dtype=torch.int8)
        triplet_of = torch.empty(0, dtype=torch.long)
        local_of = torch.empty(0, dtype=torch.long)
    return source_triplets, y_global, triplet_of, local_of


def _validate_binary_labels(y_global: Tensor) -> None:
    """Reject supervision pools containing labels outside ``{0, 1}``."""
    if y_global.numel() == 0:
        return
    non_binary = (y_global != 0) & (y_global != 1)
    n_bad = int(non_binary.sum().item())
    if n_bad > 0:
        msg = (
            f"wire_transfer y must be binary (0 or 1); "
            f"got {n_bad} non-binary value(s) in the supervision pool"
        )
        raise ValueError(msg)


def _compute_assignment(
    y_global: Tensor,
    ratios: tuple[float, float, float],
    gen: torch.Generator,
) -> Tensor:
    """Assign a split id to every edge in the supervision pool, stratified per class."""
    n_total = int(y_global.numel())
    assignment = torch.empty(n_total, dtype=torch.long)
    if n_total == 0:
        return assignment

    r_train, r_val, r_test = ratios
    del r_train

    pos_global = (y_global == 1).nonzero(as_tuple=True)[0]
    neg_global = (y_global == 0).nonzero(as_tuple=True)[0]

    for class_idx_tensor in (
        pos_global[torch.randperm(len(pos_global), generator=gen)],
        neg_global[torch.randperm(len(neg_global), generator=gen)],
    ):
        n = int(class_idx_tensor.numel())
        n_val = int(n * r_val)
        n_test = int(n * r_test)
        n_train = n - n_val - n_test
        train_idx = class_idx_tensor[:n_train]
        val_idx = class_idx_tensor[n_train : n_train + n_val]
        test_idx = class_idx_tensor[n_train + n_val :]
        assignment[train_idx] = _SPLIT_TRAIN
        assignment[val_idx] = _SPLIT_VAL
        assignment[test_idx] = _SPLIT_TEST

    return assignment


def _build_split_graph(  # noqa: PLR0913
    data: HeteroData,
    source_triplets: list[tuple[str, str, str]],
    assignment: Tensor,
    triplet_of: Tensor,
    local_of: Tensor,
    split_id: int,
) -> HeteroData:
    """Dispatch one split back into a fresh HeteroData."""
    out = HeteroData()

    for node_type in data.node_types:
        for key, val in data[node_type].items():
            out[node_type][key] = val

    for edge_type in data.edge_types:
        if edge_type[1] == "at_bank":
            for key, val in data[edge_type].items():
                out[edge_type][key] = val

    out.graphwash_timestamp_epoch_s = data.graphwash_timestamp_epoch_s
    out.graphwash_bank_ids = data.graphwash_bank_ids
    out.graphwash_individual_composite_ids = data.graphwash_individual_composite_ids
    out.graphwash_business_composite_ids = data.graphwash_business_composite_ids

    for triplet_idx, triplet in enumerate(source_triplets):
        mask = (assignment == split_id) & (triplet_of == triplet_idx)
        local_slice = local_of[mask]
        src = data[triplet]
        for key, val in src.items():
            if not isinstance(val, torch.Tensor):
                out[triplet][key] = val
            elif (
                val.dim() == _EDGE_INDEX_ROW_COUNT
                and val.size(0) == _EDGE_INDEX_ROW_COUNT
            ):
                out[triplet][key] = val[:, local_slice]
            else:
                out[triplet][key] = val[local_slice]

    return out


def stratified_split(
    data: HeteroData,
    ratios: tuple[float, float, float],
    seed: int,
) -> tuple[HeteroData, HeteroData, HeteroData]:
    """Deterministic stratified split over supervised wire_transfer edges.

    Preserves the global illicit class ratio of the built supervision
    pool across the three returned splits. See
    ``docs/superpowers/specs/2026-04-23-t-025-stratified-splits-design.md``
    for the full contract.

    Args:
        data: Source HeteroData from ``build_hetero_data()``. CPU-resident.
            Every source-present ``wire_transfer`` edge store must carry a
            binary ``y: Tensor[int8]``.
        ratios: Three non-negative finite floats summing to 1.0 within
            1e-6, in ``(train, val, test)`` order. Zero ratios allowed.
        seed: Integer seed driving a local ``torch.Generator``.

    Returns:
        Three HeteroData objects in ``(train, val, test)`` order.

    Raises:
        ValueError: on invalid ``ratios``, non-CPU input tensors, or
            non-binary ``y`` values (must be 0 or 1).
    """
    _validate_ratios(ratios)
    _check_cpu_device(data)

    source_triplets, y_global, triplet_of, local_of = _build_supervision_pool(
        data,
    )
    _validate_binary_labels(y_global)
    gen = torch.Generator()
    gen.manual_seed(seed)
    assignment = _compute_assignment(y_global, ratios, gen)

    return (
        _build_split_graph(
            data,
            source_triplets,
            assignment,
            triplet_of,
            local_of,
            _SPLIT_TRAIN,
        ),
        _build_split_graph(
            data,
            source_triplets,
            assignment,
            triplet_of,
            local_of,
            _SPLIT_VAL,
        ),
        _build_split_graph(
            data,
            source_triplets,
            assignment,
            triplet_of,
            local_of,
            _SPLIT_TEST,
        ),
    )
