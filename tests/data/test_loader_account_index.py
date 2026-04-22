"""Tests for loader._build_account_node_index."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from graphwash.data import schema
from graphwash.data.loader import (
    BUSINESS_CODE,
    INDIVIDUAL_CODE,
    NodeIndexBundle,
    _build_account_node_index,
    _drop_self_loops,
    _load_raw_csv,
)
from graphwash.data.node_types import assign_account_type

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd


def _run_pipeline_through_account_index(
    fixture_csv_dir: Path,
) -> tuple[NodeIndexBundle, pd.DataFrame]:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    return _build_account_node_index(df)


def test_account_index_produces_composite_ids_matching_union(
    fixture_csv_dir: Path,
) -> None:
    bundle, df_with_idx = _run_pipeline_through_account_index(fixture_csv_dir)

    expected_composites = set()
    for row in df_with_idx.itertuples(index=False):
        expected_composites.add(f"{row.from_bank}|{row.from_account}")
        expected_composites.add(f"{row.to_bank}|{row.to_account}")
    assert set(bundle.composite_ids) == expected_composites


def test_account_index_deduplicates_composite_pairs(
    fixture_csv_dir: Path,
) -> None:
    """Distinct (bank, account) pairs land in distinct global indices.

    This is the PR #37 regression guard: bare-account keying would
    collapse these.
    """
    bundle, _ = _run_pipeline_through_account_index(fixture_csv_dir)

    assert len(bundle.composite_ids) == len(set(bundle.composite_ids))
    assert len(bundle.composite_ids) == len(bundle.bank_id_per_composite)
    assert len(bundle.composite_ids) == len(bundle.account_type_per_composite)


def test_account_index_types_match_hash_policy(fixture_csv_dir: Path) -> None:
    bundle, _ = _run_pipeline_through_account_index(fixture_csv_dir)

    for i, composite in enumerate(bundle.composite_ids):
        expected_type = assign_account_type(composite)
        expected_code = (
            INDIVIDUAL_CODE if expected_type == "individual" else BUSINESS_CODE
        )
        assert bundle.account_type_per_composite[i] == expected_code


def test_account_index_local_indices_match_per_type_order(
    fixture_csv_dir: Path,
) -> None:
    bundle, _ = _run_pipeline_through_account_index(fixture_csv_dir)

    individual_global = np.where(bundle.account_type_per_composite == INDIVIDUAL_CODE)[
        0
    ]
    business_global = np.where(bundle.account_type_per_composite == BUSINESS_CODE)[0]

    for local_pos, global_idx in enumerate(individual_global):
        assert bundle.individual_local_idx[global_idx] == local_pos
    for local_pos, global_idx in enumerate(business_global):
        assert bundle.business_local_idx[global_idx] == local_pos

    assert np.all(bundle.individual_local_idx[business_global] == -1)
    assert np.all(bundle.business_local_idx[individual_global] == -1)


def test_account_index_attaches_composite_idx_columns(
    fixture_csv_dir: Path,
) -> None:
    _, df_with_idx = _run_pipeline_through_account_index(fixture_csv_dir)

    assert "from_composite_idx" in df_with_idx.columns
    assert "to_composite_idx" in df_with_idx.columns
    assert df_with_idx["from_composite_idx"].dtype == "int64"
    assert df_with_idx["to_composite_idx"].dtype == "int64"


def test_account_index_bank_id_recovered_from_composite_prefix(
    fixture_csv_dir: Path,
) -> None:
    bundle, _ = _run_pipeline_through_account_index(fixture_csv_dir)

    for i, composite in enumerate(bundle.composite_ids):
        bank_prefix = int(composite.split("|", 1)[0])
        assert bundle.bank_id_per_composite[i] == bank_prefix
