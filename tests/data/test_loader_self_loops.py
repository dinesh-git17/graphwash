"""Tests for loader._drop_self_loops."""

from __future__ import annotations

import pandas as pd

from graphwash.data.loader import _drop_self_loops


def test_drop_self_loops_removes_matched_rows() -> None:
    df = pd.DataFrame(
        {
            "from_bank": [1, 1, 2, 3],
            "from_account": ["a", "b", "c", "d"],
            "to_bank": [1, 2, 2, 3],
            "to_account": ["a", "b", "c", "d"],
        },
    )
    out = _drop_self_loops(df)
    assert len(out) == 1
    assert out.iloc[0]["from_account"] == "b"


def test_drop_self_loops_preserves_dtypes() -> None:
    df = pd.DataFrame(
        {
            "from_bank": pd.Series([1, 2], dtype="int32"),
            "from_account": pd.Series(["a", "b"], dtype="string"),
            "to_bank": pd.Series([1, 3], dtype="int32"),
            "to_account": pd.Series(["a", "b"], dtype="string"),
        },
    )
    out = _drop_self_loops(df)
    assert out["from_bank"].dtype == "int32"
    assert str(out["from_account"].dtype) == "string"


def test_drop_self_loops_resets_index() -> None:
    df = pd.DataFrame(
        {
            "from_bank": [1, 1, 2],
            "from_account": ["a", "b", "c"],
            "to_bank": [1, 2, 2],
            "to_account": ["a", "b", "c"],
        },
    )
    out = _drop_self_loops(df)
    assert list(out.index) == [0]


def test_drop_self_loops_returns_empty_on_all_loops() -> None:
    df = pd.DataFrame(
        {
            "from_bank": [1, 2],
            "from_account": ["a", "b"],
            "to_bank": [1, 2],
            "to_account": ["a", "b"],
        },
    )
    out = _drop_self_loops(df)
    assert len(out) == 0
