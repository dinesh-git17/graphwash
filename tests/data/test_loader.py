"""Tests for `build_hetero_data` and raw-CSV loading helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

from graphwash.data.loader import _load_raw_csv
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
