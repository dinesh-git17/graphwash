"""Construct a PyG ``HeteroData`` object from the IT-AML HI-Medium CSV.

See ``docs/graphwash-prd.md`` REQ-001 for the functional requirement
and ``src/graphwash/data/schema.py`` for the raw-column contract.

The loader uses three node types (``individual``, ``business``, ``bank``)
and one relation (``wire_transfer``). Accounts are split between
``individual`` and ``business`` via ``assign_account_node_type``, a
deterministic SHA-256 hash policy (70/30 target). Banks become
standalone nodes with no incident edges in v1 -- the ``wire_transfer``
relation connects accounts only. Richer bank attachment is out of
scope for this task and revisited in Phase 2.

Per-edge features:
    - ``amount``: float32, sourced from ``amount_paid``.
    - ``timestamp``: int64 unix seconds, derived from the parsed
      ``datetime64[ns]`` column.
    - ``currency_flag``: int8, ``1`` when ``receiving_currency`` and
      ``payment_currency`` differ, else ``0``.

The ``is_laundering`` label is carried per edge as ``.y`` on each
triplet, to unblock downstream stratified splitting (T-025).

Node feature tensors ``x`` are placeholder ``torch.ones(N, 1)`` per
type; real node features land in a follow-up task.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from graphwash.data.node_types import AccountNodeType

from graphwash.data.node_types import assign_account_node_type
from graphwash.data.schema import (
    RAW_COLUMN_DTYPES,
    RAW_FILENAME,
    RENAME_MAP,
    TIMESTAMP_FORMAT,
)

_ACCOUNT_NODE_TYPES: tuple[AccountNodeType, ...] = ("individual", "business")


def _build_node_index_tables(
    frame: pd.DataFrame,
) -> Mapping[str, dict[str, int]]:
    """Build ``{original_id: local_idx}`` maps for each node type.

    Account ids (strings) are classified by ``assign_account_node_type``.
    Bank ids (ints, stringified for dict keys) populate the ``bank``
    table. Local indices are contiguous zero-based per type, assigned
    in first-seen order over ``(from, to)`` scanning.

    Args:
        frame: DataFrame returned by ``_load_raw_csv``.

    Returns:
        Mapping with keys ``"individual"``, ``"business"``, and ``"bank"``,
        each holding a ``{original_id: local_idx}`` dict.
    """
    individual: dict[str, int] = {}
    business: dict[str, int] = {}
    bank: dict[str, int] = {}

    def _register_account(account_id: str) -> None:
        node_type = assign_account_node_type(account_id)
        table = individual if node_type == "individual" else business
        if account_id not in table:
            table[account_id] = len(table)

    def _register_bank(bank_id: int) -> None:
        key = str(bank_id)
        if key not in bank:
            bank[key] = len(bank)

    for account_id in frame["from_account"]:
        _register_account(account_id)
    for account_id in frame["to_account"]:
        _register_account(account_id)
    for bank_id in frame["from_bank"]:
        _register_bank(int(bank_id))
    for bank_id in frame["to_bank"]:
        _register_bank(int(bank_id))

    return {"individual": individual, "business": business, "bank": bank}


def _load_raw_csv(csv_dir: Path) -> pd.DataFrame:
    """Load the HI-Medium transactions CSV and apply the schema rename map.

    Args:
        csv_dir: Directory containing ``HI-Medium_Trans.csv``.

    Returns:
        DataFrame with renamed columns and a parsed ``timestamp`` column.
    """
    path = csv_dir / RAW_FILENAME
    frame = pd.read_csv(path, dtype=dict(RAW_COLUMN_DTYPES))  # type: ignore[arg-type]  # reason: pandas-stubs DtypeArg union does not accept dict[str, str] directly; runtime behaviour is correct
    frame = frame.rename(columns=dict(RENAME_MAP))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], format=TIMESTAMP_FORMAT)
    return frame
