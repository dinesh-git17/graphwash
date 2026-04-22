"""Tests for loader._compute_account_features (seven-feature schema)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import torch

from graphwash.data import schema
from graphwash.data.loader import (
    BUSINESS_CODE,
    INDIVIDUAL_CODE,
    NodeIndexBundle,
    _build_account_node_index,
    _build_bank_index,
    _compute_account_features,
    _drop_self_loops,
    _load_raw_csv,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd


def _pipeline_to_account_features(
    fixture_csv_dir: Path,
) -> tuple[dict[str, torch.Tensor], NodeIndexBundle, pd.DataFrame]:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)
    bundle = _build_bank_index(df, bundle)
    features = _compute_account_features(df, bundle)
    return features, bundle, df


def test_account_features_shape_and_dtype(fixture_csv_dir: Path) -> None:
    features, bundle, _ = _pipeline_to_account_features(fixture_csv_dir)

    n_ind = int((bundle.account_type_per_composite == INDIVIDUAL_CODE).sum())
    n_biz = int((bundle.account_type_per_composite == BUSINESS_CODE).sum())

    assert features["individual"].shape == (n_ind, 7)
    assert features["business"].shape == (n_biz, 7)
    assert features["individual"].dtype == torch.float32
    assert features["business"].dtype == torch.float32


def test_account_feature_spot_check_out_and_in_counts(
    fixture_csv_dir: Path,
) -> None:
    """Manually compute out_count / in_count for one composite, compare."""
    features, bundle, df = _pipeline_to_account_features(fixture_csv_dir)

    global_idx = int(
        (bundle.account_type_per_composite == INDIVIDUAL_CODE).argmax(),
    )
    local = int(bundle.individual_local_idx[global_idx])

    expected_out = int((df["from_composite_idx"] == global_idx).sum())
    expected_in = int((df["to_composite_idx"] == global_idx).sum())

    assert features["individual"][local, 0].item() == float(expected_out)
    assert features["individual"][local, 1].item() == float(expected_in)


def test_account_feature_unique_counterparty_count_is_undirected(
    fixture_csv_dir: Path,
) -> None:
    features, bundle, df = _pipeline_to_account_features(fixture_csv_dir)

    global_idx = int(
        (bundle.account_type_per_composite == INDIVIDUAL_CODE).argmax(),
    )
    local = int(bundle.individual_local_idx[global_idx])

    outgoing = set(
        df.loc[df["from_composite_idx"] == global_idx, "to_composite_idx"],
    )
    incoming = set(
        df.loc[df["to_composite_idx"] == global_idx, "from_composite_idx"],
    )
    expected = len(outgoing | incoming)

    assert features["individual"][local, 4].item() == float(expected)


def test_account_feature_amount_sums_use_amount_paid(
    fixture_csv_dir: Path,
) -> None:
    features, bundle, df = _pipeline_to_account_features(fixture_csv_dir)

    global_idx = int(
        (bundle.account_type_per_composite == BUSINESS_CODE).argmax(),
    )
    local = int(bundle.business_local_idx[global_idx])

    expected_out = float(
        df.loc[df["from_composite_idx"] == global_idx, "amount_paid"].sum(),
    )
    expected_in = float(
        df.loc[df["to_composite_idx"] == global_idx, "amount_paid"].sum(),
    )

    assert features["business"][local, 2].item() == pytest.approx(
        expected_out,
        rel=1e-5,
    )
    assert features["business"][local, 3].item() == pytest.approx(
        expected_in,
        rel=1e-5,
    )
