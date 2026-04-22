"""Tests for loader._build_bank_index."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from graphwash.data import schema
from graphwash.data.loader import (
    _build_account_node_index,
    _build_bank_index,
    _drop_self_loops,
    _load_raw_csv,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_bank_index_is_sorted_unique_union_of_from_and_to(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)

    bundle = _build_bank_index(df, bundle)

    expected = np.unique(
        np.concatenate(
            [df["from_bank"].to_numpy(), df["to_bank"].to_numpy()],
        ),
    )
    np.testing.assert_array_equal(bundle.bank_ordered, expected)
    assert np.all(bundle.bank_ordered[:-1] <= bundle.bank_ordered[1:])


def test_bank_index_supports_searchsorted_lookup(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)

    bundle = _build_bank_index(df, bundle)

    positions = np.searchsorted(bundle.bank_ordered, bundle.bank_ordered)
    np.testing.assert_array_equal(positions, np.arange(len(bundle.bank_ordered)))


def test_bank_index_covers_every_composite(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)

    bundle = _build_bank_index(df, bundle)

    for bank_id in bundle.bank_id_per_composite:
        assert bank_id in bundle.bank_ordered
