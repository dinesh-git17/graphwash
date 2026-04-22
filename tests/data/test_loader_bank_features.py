"""Tests for loader._compute_bank_features."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import torch

from graphwash.data import schema
from graphwash.data.loader import (
    NodeIndexBundle,
    _build_account_node_index,
    _build_bank_index,
    _compute_bank_features,
    _drop_self_loops,
    _load_raw_csv,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd


def _pipeline_to_bank_features(
    fixture_csv_dir: Path,
) -> tuple[torch.Tensor, NodeIndexBundle, pd.DataFrame]:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)
    bundle, df = _build_account_node_index(df)
    bundle = _build_bank_index(df, bundle)
    features = _compute_bank_features(df, bundle)
    return features, bundle, df


def test_bank_features_shape_and_dtype(fixture_csv_dir: Path) -> None:
    features, bundle, _ = _pipeline_to_bank_features(fixture_csv_dir)

    assert features.shape == (len(bundle.bank_ordered), 7)
    assert features.dtype == torch.float32


def test_bank_feature_spot_check_member_and_counts(
    fixture_csv_dir: Path,
) -> None:
    features, bundle, df = _pipeline_to_bank_features(fixture_csv_dir)

    bank_id = int(bundle.bank_ordered[0])

    expected_members = int((bundle.bank_id_per_composite == bank_id).sum())
    expected_out = int((df["from_bank"] == bank_id).sum())
    expected_in = int((df["to_bank"] == bank_id).sum())
    expected_internal = int(
        ((df["from_bank"] == bank_id) & (df["to_bank"] == bank_id)).sum(),
    )
    expected_external = int(
        ((df["from_bank"] == bank_id) & (df["to_bank"] != bank_id)).sum()
        + ((df["to_bank"] == bank_id) & (df["from_bank"] != bank_id)).sum(),
    )

    assert features[0, 0].item() == float(expected_members)
    assert features[0, 1].item() == float(expected_out)
    assert features[0, 2].item() == float(expected_in)
    assert features[0, 5].item() == float(expected_internal)
    assert features[0, 6].item() == float(expected_external)


def test_bank_feature_amount_sums(fixture_csv_dir: Path) -> None:
    features, bundle, df = _pipeline_to_bank_features(fixture_csv_dir)

    bank_id = int(bundle.bank_ordered[0])
    expected_out_amount = float(
        df.loc[df["from_bank"] == bank_id, "amount_paid"].sum(),
    )
    expected_in_amount = float(
        df.loc[df["to_bank"] == bank_id, "amount_paid"].sum(),
    )

    assert features[0, 3].item() == pytest.approx(expected_out_amount, rel=1e-5)
    assert features[0, 4].item() == pytest.approx(expected_in_amount, rel=1e-5)
