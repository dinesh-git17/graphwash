"""Session-scoped synthetic fixture for tests/data.

Builds a ~1000-row CSV mirroring the IT-AML HI-Medium header layout
captured in src/graphwash/data/schema.py. Deterministic (seed 42).
The fixture is engineered to exercise every regression guard:
bare-account collisions across banks, both account types as src and
dst across all four wire_transfer triplets, mixed currencies,
illicit labels, self-loops, and at least one self-loop-only account.
"""

from __future__ import annotations

import datetime as dt
import random
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from graphwash.data import schema
from graphwash.data.node_types import assign_account_type

if TYPE_CHECKING:
    from pathlib import Path

FIXTURE_SEED = 42
FIXTURE_ROW_COUNT = 1000
FIXTURE_ILLICIT_FRACTION = 0.05
FIXTURE_CROSS_CURRENCY_FRACTION = 0.20
FIXTURE_SELF_LOOP_COUNT = 3
FIXTURE_TIMESTAMP_START = dt.datetime(2022, 9, 1, 8, 30, 0, tzinfo=dt.UTC)
FIXTURE_TIMESTAMP_SPAN_DAYS = 7

BANKS: tuple[int, ...] = (11, 47, 210, 1105, 88)
CURRENCIES: tuple[str, ...] = ("USD", "EUR", "GBP", "CAD", "JPY")
PAYMENT_FORMATS: tuple[str, ...] = ("Cheque", "ACH", "Credit Card", "Wire")


def _build_composites_by_type(
    rng: random.Random,
    total: int,
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Generate composites partitioned by SHA-256 assignment.

    Ensures at least one bare Account string appears under >= 2
    banks so the composite-dedup regression test has signal.
    """
    individual: list[tuple[int, str]] = []
    business: list[tuple[int, str]] = []
    candidate_idx = 0
    collision_strings = [f"shared_{i}" for i in range(5)]
    for collision_string in collision_strings:
        for bank in rng.sample(BANKS, 2):
            composite_str = f"{bank}|{collision_string}"
            bucket = assign_account_type(composite_str)
            entry = (bank, collision_string)
            if bucket == "individual":
                individual.append(entry)
            else:
                business.append(entry)

    while len(individual) + len(business) < total:
        bank = rng.choice(BANKS)
        account = f"acct_{candidate_idx:04x}"
        candidate_idx += 1
        composite_str = f"{bank}|{account}"
        bucket = assign_account_type(composite_str)
        entry = (bank, account)
        if bucket == "individual":
            individual.append(entry)
        else:
            business.append(entry)

    return individual, business


def _make_row(
    rng: random.Random,
    *,
    bank_from: int,
    account_from: str,
    bank_to: int,
    account_to: str,
) -> dict[str, object]:
    cross_currency_roll = rng.random() < FIXTURE_CROSS_CURRENCY_FRACTION
    receiving = rng.choice(CURRENCIES)
    payment = (
        rng.choice([currency for currency in CURRENCIES if currency != receiving])
        if cross_currency_roll
        else receiving
    )
    amount = round(rng.uniform(1.0, 10_000.0), 2)
    illicit = 1 if rng.random() < FIXTURE_ILLICIT_FRACTION else 0
    offset = dt.timedelta(
        seconds=rng.randint(0, FIXTURE_TIMESTAMP_SPAN_DAYS * 86_400 - 1),
    )
    timestamp = FIXTURE_TIMESTAMP_START + offset
    return {
        "Timestamp": timestamp.strftime(schema.TIMESTAMP_FORMAT),
        "From Bank": bank_from,
        "Account": account_from,
        "To Bank": bank_to,
        "Account.1": account_to,
        "Amount Received": amount,
        "Receiving Currency": receiving,
        "Amount Paid": amount,
        "Payment Currency": payment,
        "Payment Format": rng.choice(PAYMENT_FORMATS),
        "Is Laundering": illicit,
    }


def _build_fixture_rows(
    rng: random.Random,
    individual: list[tuple[int, str]],
    business: list[tuple[int, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    assert individual, "fixture needs at least one individual composite"
    assert business, "fixture needs at least one business composite"

    self_loop_only_bank = rng.choice(BANKS)
    self_loop_only_account = "self_loop_only_x"
    _ = assign_account_type(f"{self_loop_only_bank}|{self_loop_only_account}")

    rows.append(
        _make_row(
            rng,
            bank_from=self_loop_only_bank,
            account_from=self_loop_only_account,
            bank_to=self_loop_only_bank,
            account_to=self_loop_only_account,
        ),
    )
    self_loop_rows_remaining = FIXTURE_SELF_LOOP_COUNT - 1

    pool = individual + business
    for _ in range(self_loop_rows_remaining):
        bank, account = rng.choice(pool)
        rows.append(
            _make_row(
                rng,
                bank_from=bank,
                account_from=account,
                bank_to=bank,
                account_to=account,
            ),
        )

    target_per_combo = max(
        5,
        (FIXTURE_ROW_COUNT - FIXTURE_SELF_LOOP_COUNT) // 4,
    )
    combos = [
        (individual, individual),
        (individual, business),
        (business, individual),
        (business, business),
    ]
    for src_pool, dst_pool in combos:
        for _ in range(target_per_combo):
            src = rng.choice(src_pool)
            dst = rng.choice(dst_pool)
            if src == dst:
                continue
            rows.append(
                _make_row(
                    rng,
                    bank_from=src[0],
                    account_from=src[1],
                    bank_to=dst[0],
                    account_to=dst[1],
                ),
            )

    while len(rows) < FIXTURE_ROW_COUNT:
        src = rng.choice(pool)
        dst = rng.choice(pool)
        if src == dst:
            continue
        rows.append(
            _make_row(
                rng,
                bank_from=src[0],
                account_from=src[1],
                bank_to=dst[0],
                account_to=dst[1],
            ),
        )

    return rows[:FIXTURE_ROW_COUNT]


@pytest.fixture(scope="session")
def fixture_csv_dir(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Yield a directory containing a deterministic synthetic HI-Medium CSV."""
    rng = random.Random(FIXTURE_SEED)  # noqa: S311 - deterministic test fixture
    individual, business = _build_composites_by_type(rng, total=200)
    rows = _build_fixture_rows(rng, individual, business)

    df = pd.DataFrame(rows)
    df = df.rename(columns={"Account.1": "Account"})
    df = df[list(schema.HI_MEDIUM_RAW_COLUMNS)]

    out_dir = tmp_path_factory.mktemp("it_aml_fixture")
    out_path = out_dir / schema.RAW_FILENAME
    df.to_csv(out_path, index=False)
    return out_dir
