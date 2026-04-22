"""Sanity tests for the 1k synthetic fixture CSV.

These guard against fixture drift that would invalidate the
regression signal on later tests (composite dedup, self-loop drop,
triplet coverage).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from graphwash.data import schema
from graphwash.data.node_types import assign_account_type

if TYPE_CHECKING:
    from pathlib import Path


def test_fixture_csv_exists(fixture_csv_dir: Path) -> None:
    csv_path = fixture_csv_dir / schema.RAW_FILENAME
    assert csv_path.is_file()


def test_fixture_row_count_is_approximately_one_thousand(
    fixture_csv_dir: Path,
) -> None:
    df = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME)
    assert 950 <= len(df) <= 1050


def test_fixture_has_composite_collision_across_banks(
    fixture_csv_dir: Path,
) -> None:
    """At least one bare Account string appears under >= 2 banks."""
    df = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    stacked = pd.concat(
        [
            df[["from_bank", "from_account"]].rename(
                columns={"from_bank": "bank", "from_account": "account"},
            ),
            df[["to_bank", "to_account"]].rename(
                columns={"to_bank": "bank", "to_account": "account"},
            ),
        ],
        ignore_index=True,
    )
    banks_per_account = stacked.groupby("account")["bank"].nunique()
    collision_accounts = banks_per_account[banks_per_account >= 2]
    assert len(collision_accounts) >= 1


def test_fixture_has_self_loops(fixture_csv_dir: Path) -> None:
    df = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    self_loops = df[(df.from_bank == df.to_bank) & (df.from_account == df.to_account)]
    assert len(self_loops) >= 2


def test_fixture_has_self_loop_only_account(fixture_csv_dir: Path) -> None:
    """At least one account appears only in a self-loop row.

    Exercises the PRD s15 'isolated accounts: exclude' clause once
    _drop_self_loops has filtered the self-loop row.
    """
    df = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    self_loop_mask = (df.from_bank == df.to_bank) & (df.from_account == df.to_account)
    self_loop_composites = set(
        zip(
            df.loc[self_loop_mask, "from_bank"],
            df.loc[self_loop_mask, "from_account"],
            strict=True,
        )
    )
    non_loop = df.loc[~self_loop_mask]
    non_loop_composites = set(
        zip(non_loop.from_bank, non_loop.from_account, strict=True)
    ) | set(zip(non_loop.to_bank, non_loop.to_account, strict=True))
    self_loop_only = self_loop_composites - non_loop_composites
    assert len(self_loop_only) >= 1


def test_fixture_covers_all_four_wire_transfer_triplets(
    fixture_csv_dir: Path,
) -> None:
    """All four (src_type, dst_type) pairs must appear as real edges.

    Checking the source set and destination set independently is not
    enough; a fixture with only (individual, business) and
    (business, individual) rows would satisfy both sets while still
    leaving (individual, individual) and (business, business)
    triplets uncovered. This zips the pairs to pin full coverage.
    """
    df = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    non_loop = df[~((df.from_bank == df.to_bank) & (df.from_account == df.to_account))]
    observed_pairs = {
        (
            assign_account_type(f"{fb}|{fa}"),
            assign_account_type(f"{tb}|{ta}"),
        )
        for fb, fa, tb, ta in zip(
            non_loop.from_bank,
            non_loop.from_account,
            non_loop.to_bank,
            non_loop.to_account,
            strict=True,
        )
    }
    expected_pairs = {
        ("individual", "individual"),
        ("individual", "business"),
        ("business", "individual"),
        ("business", "business"),
    }
    assert observed_pairs == expected_pairs


def test_fixture_has_cross_currency_and_same_currency_rows(
    fixture_csv_dir: Path,
) -> None:
    df = pd.read_csv(fixture_csv_dir / schema.RAW_FILENAME).rename(
        columns=schema.RENAME_MAP,
    )
    same_currency = (df.receiving_currency == df.payment_currency).sum()
    cross_currency = (df.receiving_currency != df.payment_currency).sum()
    assert same_currency >= 1
    assert cross_currency >= 1
