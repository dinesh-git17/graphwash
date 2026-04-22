"""Tests for loader._load_raw_csv and its fail-fast boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from graphwash.data import schema
from graphwash.data.loader import _USECOLS, _load_raw_csv

if TYPE_CHECKING:
    from pathlib import Path


def test_load_raw_csv_returns_renamed_columns(fixture_csv_dir: Path) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)

    expected = {schema.RENAME_MAP[column] for column in _USECOLS}
    assert set(df.columns) == expected


def test_load_raw_csv_applies_typed_dtypes(fixture_csv_dir: Path) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)

    assert df["from_bank"].dtype == "int32"
    assert df["to_bank"].dtype == "int32"
    assert df["amount_paid"].dtype == "float32"
    assert df["is_laundering"].dtype == "int8"
    assert str(df["receiving_currency"].dtype) == "category"
    assert str(df["payment_currency"].dtype) == "category"
    assert str(df["timestamp"].dtype).startswith("datetime64")


def test_load_raw_csv_drops_unused_columns(fixture_csv_dir: Path) -> None:
    df = _load_raw_csv(fixture_csv_dir / schema.RAW_FILENAME)

    assert "amount_received" not in df.columns
    assert "payment_format" not in df.columns


def test_load_raw_csv_missing_file_raises_filenotfound(tmp_path: Path) -> None:
    missing = tmp_path / "nope.csv"
    with pytest.raises(FileNotFoundError, match=str(missing)):
        _load_raw_csv(missing)


def test_load_raw_csv_empty_file_raises_valueerror(tmp_path: Path) -> None:
    empty = tmp_path / schema.RAW_FILENAME
    header = ",".join(schema.HI_MEDIUM_RAW_COLUMNS)
    empty.write_text(header + "\n")
    with pytest.raises(ValueError, match="empty"):
        _load_raw_csv(empty)


def test_load_raw_csv_wrong_columns_raises_valueerror(tmp_path: Path) -> None:
    wrong = tmp_path / schema.RAW_FILENAME
    df = pd.DataFrame({"unexpected": [1, 2, 3]})
    df.to_csv(wrong, index=False)
    with pytest.raises(ValueError, match="column"):
        _load_raw_csv(wrong)
