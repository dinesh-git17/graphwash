"""Tests for loader._build_at_bank_edges."""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from graphwash.data import schema
from graphwash.data.loader import (
    BUSINESS_CODE,
    INDIVIDUAL_CODE,
    AtBankEdgeBundle,
    NodeIndexBundle,
    _build_account_node_index,
    _build_at_bank_edges,
    _build_bank_index,
    _drop_self_loops,
    _load_raw_csv,
)

if TYPE_CHECKING:
    from pathlib import Path


def _pipeline_to_at_bank(
    fixture_csv_dir: Path,
) -> tuple[dict[tuple[str, str, str], AtBankEdgeBundle], NodeIndexBundle]:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)
    bundle = _build_bank_index(df, bundle)
    edges = _build_at_bank_edges(bundle)
    return edges, bundle


def test_at_bank_triplets_are_per_account_type(
    fixture_csv_dir: Path,
) -> None:
    edges, _ = _pipeline_to_at_bank(fixture_csv_dir)

    expected = {
        ("individual", "at_bank", "bank"),
        ("business", "at_bank", "bank"),
    }
    assert set(edges.keys()) == expected


def test_at_bank_edge_count_equals_account_count_per_type(
    fixture_csv_dir: Path,
) -> None:
    edges, bundle = _pipeline_to_at_bank(fixture_csv_dir)

    n_ind = int((bundle.account_type_per_composite == INDIVIDUAL_CODE).sum())
    n_biz = int((bundle.account_type_per_composite == BUSINESS_CODE).sum())

    assert edges[("individual", "at_bank", "bank")].edge_index.shape[1] == n_ind
    assert edges[("business", "at_bank", "bank")].edge_index.shape[1] == n_biz


def test_at_bank_edges_point_to_declared_bank(
    fixture_csv_dir: Path,
) -> None:
    """Each at_bank edge's dst bank matches the src account's declared bank."""
    edges, bundle = _pipeline_to_at_bank(fixture_csv_dir)

    for account_type, code, local_idx_arr in (
        ("individual", INDIVIDUAL_CODE, bundle.individual_local_idx),
        ("business", BUSINESS_CODE, bundle.business_local_idx),
    ):
        store = edges[(account_type, "at_bank", "bank")]
        for i in range(store.edge_index.shape[1]):
            src_local = int(store.edge_index[0, i])
            dst_local = int(store.edge_index[1, i])
            global_idx = int(
                next(
                    g
                    for g in range(len(bundle.composite_ids))
                    if (
                        bundle.account_type_per_composite[g] == code
                        and local_idx_arr[g] == src_local
                    )
                ),
            )
            declared_bank = int(bundle.bank_id_per_composite[global_idx])
            actual_bank = int(bundle.bank_ordered[dst_local])
            assert declared_bank == actual_bank


def test_at_bank_edge_index_dtype(fixture_csv_dir: Path) -> None:
    edges, _ = _pipeline_to_at_bank(fixture_csv_dir)

    for eb in edges.values():
        assert eb.edge_index.dtype == torch.int64
