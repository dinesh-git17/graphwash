"""Regression lock for schema.HI_MEDIUM_EPOCH_S."""

from __future__ import annotations

import numpy as np
import pandas as pd

from graphwash.data import schema
from graphwash.data.loader import (
    RELATIVE_TIMESTAMP_MARGIN_S,
    _encode_relative_timestamps,
)


def test_hi_medium_epoch_s_exact_value() -> None:
    """Captured 2026-04-22 on the full 31.9M-row HI-Medium CSV."""
    assert schema.HI_MEDIUM_EPOCH_S == 1_661_990_390


def test_hi_medium_epoch_s_matches_derivation() -> None:
    """Earliest CSV timestamp 2022/09/01 00:00 UTC yields the constant."""
    ts = pd.to_datetime(
        pd.Series(["2022/09/01 00:00", "2022/09/28 15:58"]),
        format=schema.TIMESTAMP_FORMAT,
    ).astype(np.dtype("datetime64[us]"))
    df = pd.DataFrame({"timestamp": ts})

    _, epoch_s = _encode_relative_timestamps(df)

    assert epoch_s == schema.HI_MEDIUM_EPOCH_S


def test_hi_medium_epoch_s_is_day_aligned_minus_margin() -> None:
    """Epoch equals a midnight-UTC boundary minus RELATIVE_TIMESTAMP_MARGIN_S."""
    day_boundary = schema.HI_MEDIUM_EPOCH_S + RELATIVE_TIMESTAMP_MARGIN_S
    assert day_boundary % 86400 == 0
