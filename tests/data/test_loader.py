"""Tests for `build_hetero_data` and raw-CSV loading helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import torch

if TYPE_CHECKING:
    from pathlib import Path

from graphwash.data.loader import (
    _build_node_index_tables,
    _build_wire_transfer_edges,
    _load_raw_csv,
)
from graphwash.data.schema import RENAME_MAP


def test_load_raw_csv_reads_fixture(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    assert len(frame) == 1_000
    assert list(frame.columns) == list(RENAME_MAP.values())


def test_load_raw_csv_parses_timestamp_as_datetime(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    assert pd.api.types.is_datetime64_any_dtype(frame["timestamp"])


def test_load_raw_csv_preserves_label_column_dtype(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    assert frame["is_laundering"].dtype == "int8"


def test_node_index_tables_cover_three_types(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    assert set(tables) == {"individual", "business", "bank"}


def test_node_index_tables_are_contiguous_zero_based(
    fixture_csv_dir: Path,
) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    for node_type, id_to_idx in tables.items():
        values = sorted(id_to_idx.values())
        assert values == list(range(len(id_to_idx))), node_type


def test_account_type_is_consistent_across_src_dst_positions(
    fixture_csv_dir: Path,
) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    individuals = set(tables["individual"])
    businesses = set(tables["business"])
    assert individuals.isdisjoint(businesses)


def test_bank_node_count_matches_fixture(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    expected_banks = set(frame["from_bank"]).union(frame["to_bank"])
    assert len(tables["bank"]) == len(expected_banks)


def test_wire_transfer_edges_cover_account_triplets_only(
    fixture_csv_dir: Path,
) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    edges = _build_wire_transfer_edges(frame, tables)

    allowed = {
        ("individual", "wire_transfer", "individual"),
        ("individual", "wire_transfer", "business"),
        ("business", "wire_transfer", "individual"),
        ("business", "wire_transfer", "business"),
    }
    assert set(edges).issubset(allowed)
    for triplet in edges:
        assert "bank" not in {triplet[0], triplet[2]}


def test_wire_transfer_edges_sum_to_row_count(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    edges = _build_wire_transfer_edges(frame, tables)
    total = sum(bundle.edge_index.shape[1] for bundle in edges.values())
    assert total == len(frame)


def test_wire_transfer_edge_feature_dtypes(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    edges = _build_wire_transfer_edges(frame, tables)

    for bundle in edges.values():
        assert bundle.edge_index.dtype == torch.int64
        assert bundle.amount.dtype == torch.float32
        assert bundle.timestamp.dtype == torch.int64
        assert bundle.currency_flag.dtype == torch.int8
        assert bundle.is_laundering.dtype == torch.int8


def test_currency_flag_matches_cross_currency_rows(fixture_csv_dir: Path) -> None:
    frame = _load_raw_csv(fixture_csv_dir)
    tables = _build_node_index_tables(frame)
    edges = _build_wire_transfer_edges(frame, tables)

    total_cross = sum(
        int(bundle.currency_flag.sum().item()) for bundle in edges.values()
    )
    expected_cross = int(
        (frame["receiving_currency"] != frame["payment_currency"]).sum()
    )
    assert total_cross == expected_cross
