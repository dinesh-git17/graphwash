"""Tests for loader._encode_relative_timestamps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

from graphwash.data import schema
from graphwash.data.loader import (
    RELATIVE_TIMESTAMP_MARGIN_S,
    _drop_self_loops,
    _encode_relative_timestamps,
    _load_raw_csv,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_encode_relative_timestamps_epoch_is_day_floor_minus_margin(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)

    _, epoch_s = _encode_relative_timestamps(df)

    unix_s = df["timestamp"].astype("int64").to_numpy() // 1_000_000_000
    expected_epoch = (int(unix_s.min()) // 86400) * 86400 - RELATIVE_TIMESTAMP_MARGIN_S
    assert epoch_s == expected_epoch


def test_encode_relative_timestamps_returns_int64_array(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)

    rel_ts, _ = _encode_relative_timestamps(df)

    assert rel_ts.dtype == np.int64
    assert len(rel_ts) == len(df)


def test_encode_relative_timestamps_min_value_is_at_least_margin(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)

    rel_ts, _ = _encode_relative_timestamps(df)

    assert int(rel_ts.min()) >= RELATIVE_TIMESTAMP_MARGIN_S


def test_encode_relative_timestamps_preserves_ordering(
    fixture_csv_dir: Path,
) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)
    df = _drop_self_loops(df)

    rel_ts, _ = _encode_relative_timestamps(df)

    unix_s = df["timestamp"].astype("int64").to_numpy() // 1_000_000_000
    assert np.all(np.argsort(rel_ts) == np.argsort(unix_s))


def test_encode_relative_timestamps_rejects_nat_column() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.Series(
                [pd.NaT, pd.NaT],
                dtype="datetime64[ns]",
            ),
        },
    )
    with pytest.raises(ValueError, match="epoch"):
        _encode_relative_timestamps(df)
