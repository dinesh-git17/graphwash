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
    from pathlib import Path

from graphwash.data.schema import (
    RAW_COLUMN_DTYPES,
    RAW_FILENAME,
    RENAME_MAP,
    TIMESTAMP_FORMAT,
)


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
