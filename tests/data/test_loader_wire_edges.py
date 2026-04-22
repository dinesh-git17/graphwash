"""Tests for loader._build_wire_transfer_edges."""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from graphwash.data import schema
from graphwash.data.loader import (
    NodeIndexBundle,
    WireTransferEdgeBundle,
    _build_account_node_index,
    _build_bank_index,
    _build_wire_transfer_edges,
    _drop_self_loops,
    _encode_relative_timestamps,
    _load_raw_csv,
)

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from numpy.typing import NDArray


def _pipeline_to_wire_edges(
    fixture_csv_dir: Path,
) -> tuple[
    dict[tuple[str, str, str], WireTransferEdgeBundle],
    NodeIndexBundle,
    pd.DataFrame,
    NDArray[np.int64],
]:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)
    bundle = _build_bank_index(df, bundle)
    rel_ts, _ = _encode_relative_timestamps(df)
    edges = _build_wire_transfer_edges(df, bundle, rel_ts)
    return edges, bundle, df, rel_ts


def test_wire_edges_sum_to_non_self_loop_row_count(
    fixture_csv_dir: Path,
) -> None:
    edges, _, df, _ = _pipeline_to_wire_edges(fixture_csv_dir)

    total = sum(eb.edge_index.shape[1] for eb in edges.values())
    assert total == len(df)


def test_wire_edges_cover_expected_triplets(
    fixture_csv_dir: Path,
) -> None:
    edges, _, _, _ = _pipeline_to_wire_edges(fixture_csv_dir)

    expected_combos = {
        ("individual", "wire_transfer", "individual"),
        ("individual", "wire_transfer", "business"),
        ("business", "wire_transfer", "individual"),
        ("business", "wire_transfer", "business"),
    }
    assert set(edges.keys()) == expected_combos


def test_wire_edge_attribute_dtypes(fixture_csv_dir: Path) -> None:
    edges, _, _, _ = _pipeline_to_wire_edges(fixture_csv_dir)

    for eb in edges.values():
        assert eb.edge_index.dtype == torch.int64
        assert eb.amount_paid.dtype == torch.float32
        assert eb.timestamp.dtype == torch.int64
        assert eb.cross_currency.dtype == torch.int8
        assert eb.y.dtype in {torch.int8, torch.int16, torch.int32, torch.int64}


def test_wire_edge_attribute_alignment(fixture_csv_dir: Path) -> None:
    edges, _, _, _ = _pipeline_to_wire_edges(fixture_csv_dir)

    for eb in edges.values():
        e = eb.edge_index.shape[1]
        assert eb.amount_paid.shape[0] == e
        assert eb.timestamp.shape[0] == e
        assert eb.cross_currency.shape[0] == e
        assert eb.y.shape[0] == e


def test_wire_edge_y_values_are_binary(fixture_csv_dir: Path) -> None:
    edges, _, _, _ = _pipeline_to_wire_edges(fixture_csv_dir)

    for eb in edges.values():
        unique = set(torch.unique(eb.y).tolist())
        assert unique <= {0, 1}


def test_wire_edge_cross_currency_matches_raw(
    fixture_csv_dir: Path,
) -> None:
    edges, _, df, _ = _pipeline_to_wire_edges(fixture_csv_dir)

    recv = df["receiving_currency"].astype(str)
    paid = df["payment_currency"].astype(str)
    expected_total = int((recv != paid).sum())
    observed_total = sum(int(eb.cross_currency.sum().item()) for eb in edges.values())
    assert expected_total == observed_total
