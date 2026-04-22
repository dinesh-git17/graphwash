"""End-to-end tests for loader.build_hetero_data.

Covers every acceptance bullet from T-024 including PRD s15
self-loop and isolated-account compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
import torch
from torch_geometric.nn import HGTConv

from graphwash.data import schema
from graphwash.data.loader import (
    RELATIVE_TIMESTAMP_MARGIN_S,
    build_hetero_data,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_build_returns_three_node_types(fixture_csv_dir: Path) -> None:
    data = build_hetero_data(fixture_csv_dir)
    assert set(data.metadata()[0]) == {"individual", "business", "bank"}


def test_build_has_both_edge_types(fixture_csv_dir: Path) -> None:
    data = build_hetero_data(fixture_csv_dir)
    rel_names = {triplet[1] for triplet in data.metadata()[1]}
    assert rel_names == {"wire_transfer", "at_bank"}


def test_build_composite_dedup_regression(fixture_csv_dir: Path) -> None:
    """Distinct (bank, account) pairs in the raw CSV (post self-loop drop)
    land in distinct account-type nodes."""
    data = build_hetero_data(fixture_csv_dir)
    raw = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    self_loop_mask = (raw["from_bank"] == raw["to_bank"]) & (
        raw["from_account"] == raw["to_account"]
    )
    raw = raw.loc[~self_loop_mask]

    unique_pairs = set(zip(raw["from_bank"], raw["from_account"], strict=True)) | set(
        zip(raw["to_bank"], raw["to_account"], strict=True)
    )
    total_account_nodes = data["individual"].x.shape[0] + data["business"].x.shape[0]
    assert total_account_nodes == len(unique_pairs)

    bare_counts: dict[str, set[int]] = {}
    for bank, account in unique_pairs:
        bare_counts.setdefault(str(account), set()).add(int(bank))
    collisions = [b for b, banks in bare_counts.items() if len(banks) >= 2]
    assert len(collisions) >= 1


def test_build_at_bank_invariant_via_public_metadata(
    fixture_csv_dir: Path,
) -> None:
    data = build_hetero_data(fixture_csv_dir)

    for src_type in ("individual", "business"):
        store = data[(src_type, "at_bank", "bank")]
        composite_ids = getattr(data, f"graphwash_{src_type}_composite_ids")
        assert store.edge_index.shape[1] == len(composite_ids)
        for i in range(store.edge_index.shape[1]):
            src_local = int(store.edge_index[0, i])
            dst_local = int(store.edge_index[1, i])
            declared_bank = int(composite_ids[src_local].split("|")[0])
            actual_bank = int(data.graphwash_bank_ids[dst_local])
            assert declared_bank == actual_bank


def test_build_wire_transfer_dtypes(fixture_csv_dir: Path) -> None:
    data = build_hetero_data(fixture_csv_dir)
    for triplet in data.metadata()[1]:
        if triplet[1] != "wire_transfer":
            continue
        store = data[triplet]
        assert store.amount_paid.dtype == torch.float32
        assert store.timestamp.dtype == torch.int64
        assert store.cross_currency.dtype == torch.int8
        assert set(torch.unique(store.y).tolist()) <= {0, 1}


def test_build_wire_transfer_alignment(fixture_csv_dir: Path) -> None:
    data = build_hetero_data(fixture_csv_dir)
    for triplet in data.metadata()[1]:
        if triplet[1] != "wire_transfer":
            continue
        store = data[triplet]
        e = store.edge_index.shape[1]
        assert store.amount_paid.shape[0] == e
        assert store.timestamp.shape[0] == e
        assert store.cross_currency.shape[0] == e
        assert store.y.shape[0] == e


def test_build_timestamp_epoch_contract(fixture_csv_dir: Path) -> None:
    data = build_hetero_data(fixture_csv_dir)
    assert hasattr(data, "graphwash_timestamp_epoch_s")

    raw = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    raw["timestamp"] = pd.to_datetime(
        raw["timestamp"],
        format=schema.TIMESTAMP_FORMAT,
    )
    self_loop_mask = (raw["from_bank"] == raw["to_bank"]) & (
        raw["from_account"] == raw["to_account"]
    )
    raw = raw.loc[~self_loop_mask]
    min_unix = int(raw["timestamp"].astype("int64").min() // 1_000_000_000)
    expected_epoch = (min_unix // 86400) * 86400 - RELATIVE_TIMESTAMP_MARGIN_S
    assert data.graphwash_timestamp_epoch_s == expected_epoch


def test_build_node_features_shape_and_dtype(fixture_csv_dir: Path) -> None:
    data = build_hetero_data(fixture_csv_dir)
    for node_type in ("individual", "business", "bank"):
        x = data[node_type].x
        assert x.ndim == 2
        assert x.shape[1] == 7
        assert x.dtype == torch.float32


def test_build_hgtconv_smoke_embeds_all_three_types(
    fixture_csv_dir: Path,
) -> None:
    data = build_hetero_data(fixture_csv_dir)
    conv = HGTConv(
        in_channels=-1,
        out_channels=8,
        metadata=data.metadata(),
        heads=1,
    )
    out = conv(data.x_dict, data.edge_index_dict)
    assert set(out) == {"individual", "business", "bank"}
    for node_type, emb in out.items():
        assert emb.shape == (data[node_type].x.shape[0], 8)
        assert torch.isfinite(emb).all()


def test_build_is_deterministic(fixture_csv_dir: Path) -> None:
    a = build_hetero_data(fixture_csv_dir)
    b = build_hetero_data(fixture_csv_dir)
    for node_type in ("individual", "business", "bank"):
        assert torch.equal(a[node_type].x, b[node_type].x)
    for triplet in a.metadata()[1]:
        assert torch.equal(a[triplet].edge_index, b[triplet].edge_index)


def test_build_fails_fast_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_hetero_data(tmp_path)


def test_build_self_loop_total_matches(fixture_csv_dir: Path) -> None:
    """Total wire_transfer edges == raw rows - self-loop rows (PRD s15)."""
    data = build_hetero_data(fixture_csv_dir)
    raw = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    self_loop_count = int(
        (
            (raw["from_bank"] == raw["to_bank"])
            & (raw["from_account"] == raw["to_account"])
        ).sum(),
    )
    total_wire_edges = sum(
        data[triplet].edge_index.shape[1]
        for triplet in data.metadata()[1]
        if triplet[1] == "wire_transfer"
    )
    assert total_wire_edges == len(raw) - self_loop_count


def test_build_isolated_accounts_excluded(fixture_csv_dir: Path) -> None:
    """An account whose only raw activity is a self-loop does not appear
    in either individual or business composite ids (PRD s15)."""
    data = build_hetero_data(fixture_csv_dir)
    raw = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    self_loop_mask = (raw["from_bank"] == raw["to_bank"]) & (
        raw["from_account"] == raw["to_account"]
    )
    self_loop_composites = set(
        zip(
            raw.loc[self_loop_mask, "from_bank"],
            raw.loc[self_loop_mask, "from_account"],
            strict=True,
        )
    )
    non_loop = raw.loc[~self_loop_mask]
    non_loop_composites = set(
        zip(non_loop["from_bank"], non_loop["from_account"], strict=True),
    ) | set(
        zip(non_loop["to_bank"], non_loop["to_account"], strict=True),
    )
    isolated = self_loop_composites - non_loop_composites
    assert len(isolated) >= 1

    all_graph_composites = set(
        data.graphwash_individual_composite_ids,
    ) | set(data.graphwash_business_composite_ids)
    for bank, account in isolated:
        assert f"{bank}|{account}" not in all_graph_composites
