"""Shared fixtures for data-layer tests."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path

from graphwash.data.node_types import assign_account_node_type
from graphwash.data.schema import (
    HI_MEDIUM_RAW_COLUMNS,
    RAW_FILENAME,
    TIMESTAMP_FORMAT,
)

_FIXTURE_ROW_COUNT = 1_000
_FIXTURE_BANK_COUNT = 3
_FIXTURE_ACCOUNT_COUNT = 80
_FIXTURE_CURRENCIES = ("USD", "EUR", "GBP", "JPY")
_FIXTURE_CROSS_CURRENCY_RATE = 0.2
_FIXTURE_LAUNDERING_RATE = 0.01
_FIXTURE_SEED = 42


def _build_fixture_dataframe() -> pd.DataFrame:
    rng = random.Random(_FIXTURE_SEED)  # noqa: S311

    banks = list(range(100, 100 + _FIXTURE_BANK_COUNT))
    accounts = [f"ACC{idx:08X}" for idx in range(_FIXTURE_ACCOUNT_COUNT)]

    individual_count = sum(
        1 for a in accounts if assign_account_node_type(a) == "individual"
    )
    business_count = len(accounts) - individual_count
    assert individual_count > 0
    assert business_count > 0

    rows: list[tuple[object, ...]] = []
    base_ts = pd.Timestamp("2022-09-01 00:00")
    for idx in range(_FIXTURE_ROW_COUNT):
        src = rng.choice(accounts)
        dst = rng.choice([a for a in accounts if a != src])
        from_bank = rng.choice(banks)
        to_bank = rng.choice(banks)
        pay_currency = rng.choice(_FIXTURE_CURRENCIES)
        if rng.random() < _FIXTURE_CROSS_CURRENCY_RATE:
            recv_currency = rng.choice(
                [c for c in _FIXTURE_CURRENCIES if c != pay_currency]
            )
        else:
            recv_currency = pay_currency
        amount_paid = round(rng.uniform(10.0, 50_000.0), 2)
        amount_received = (
            amount_paid
            if recv_currency == pay_currency
            else round(amount_paid * rng.uniform(0.8, 1.2), 2)
        )
        ts = (base_ts + pd.Timedelta(minutes=idx)).strftime(TIMESTAMP_FORMAT)
        payment_format = rng.choice(("ACH", "Cheque", "Credit Card", "Wire"))
        is_laundering = 1 if rng.random() < _FIXTURE_LAUNDERING_RATE else 0

        rows.append(
            (
                ts,
                from_bank,
                src,
                to_bank,
                dst,
                amount_received,
                recv_currency,
                amount_paid,
                pay_currency,
                payment_format,
                is_laundering,
            )
        )

    frame = pd.DataFrame.from_records(rows, columns=list(HI_MEDIUM_RAW_COLUMNS))
    assert len(frame) == _FIXTURE_ROW_COUNT
    return frame


@pytest.fixture(scope="session")
def fixture_csv_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write a deterministic 1k-row HI-Medium CSV to a session tmp dir.

    Args:
        tmp_path_factory: Pytest's built-in session-scoped temp path factory.

    Returns:
        Path to the directory containing ``HI-Medium_Trans.csv``.
    """
    target_dir = tmp_path_factory.mktemp("raw")
    frame = _build_fixture_dataframe()
    frame.to_csv(target_dir / RAW_FILENAME, index=False)
    return target_dir
