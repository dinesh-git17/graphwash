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

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd
import torch
from torch_geometric.data import HeteroData

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


@dataclass(frozen=True)
class _EdgeBundle:
    """Per-triplet edge tensors for the ``wire_transfer`` relation."""

    edge_index: torch.Tensor
    amount: torch.Tensor
    timestamp: torch.Tensor
    currency_flag: torch.Tensor
    is_laundering: torch.Tensor


def _build_wire_transfer_edges(
    frame: pd.DataFrame,
    tables: Mapping[str, dict[str, int]],
) -> dict[tuple[AccountNodeType, str, AccountNodeType], _EdgeBundle]:
    """Bucket rows into per-triplet edge tensors.

    Produces up to four ``(src_type, 'wire_transfer', dst_type)``
    triplets spanning ``individual``/``business`` only. Banks are not
    endpoints of ``wire_transfer`` in v1.

    Args:
        frame: DataFrame returned by ``_load_raw_csv``.
        tables: Node-index maps returned by ``_build_node_index_tables``.

    Returns:
        Dict keyed by ``(src_type, 'wire_transfer', dst_type)`` triplets,
        each holding an ``_EdgeBundle`` with edge_index and per-edge features.
    """
    src_types = frame["from_account"].map(assign_account_node_type)
    dst_types = frame["to_account"].map(assign_account_node_type)

    timestamp_seconds = (frame["timestamp"].astype("int64") // 1_000_000_000).to_numpy()
    amount = frame["amount_paid"].to_numpy()
    currency_flag = (
        frame["receiving_currency"].to_numpy() != frame["payment_currency"].to_numpy()
    ).astype("int8")
    is_laundering = frame["is_laundering"].to_numpy().astype("int8")

    individual_idx = tables["individual"]
    business_idx = tables["business"]

    def _local_index(account_id: str, node_type: AccountNodeType) -> int:
        table = individual_idx if node_type == "individual" else business_idx
        return table[account_id]

    bundles: dict[
        tuple[AccountNodeType, str, AccountNodeType],
        _EdgeBundle,
    ] = {}

    for src_type in _ACCOUNT_NODE_TYPES:
        for dst_type in _ACCOUNT_NODE_TYPES:
            mask = (src_types == src_type) & (dst_types == dst_type)
            if not mask.any():
                continue
            subset = frame.loc[mask]
            src_local = [_local_index(a, src_type) for a in subset["from_account"]]
            dst_local = [_local_index(a, dst_type) for a in subset["to_account"]]
            edge_index = torch.tensor([src_local, dst_local], dtype=torch.int64)
            bool_mask = mask.to_numpy()
            bundles[(src_type, "wire_transfer", dst_type)] = _EdgeBundle(
                edge_index=edge_index,
                amount=torch.tensor(amount[bool_mask], dtype=torch.float32),
                timestamp=torch.tensor(timestamp_seconds[bool_mask], dtype=torch.int64),
                currency_flag=torch.tensor(currency_flag[bool_mask], dtype=torch.int8),
                is_laundering=torch.tensor(is_laundering[bool_mask], dtype=torch.int8),
            )

    return bundles


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


def build_hetero_data(csv_dir: Path) -> HeteroData:
    """Construct the IT-AML HI-Medium graph as a PyG ``HeteroData``.

    Args:
        csv_dir: Directory containing ``HI-Medium_Trans.csv``.

    Returns:
        A ``HeteroData`` instance with three node types
        (``individual``, ``business``, ``bank``) and up to four
        ``(src, 'wire_transfer', dst)`` edge triplets across
        ``individual`` and ``business``. ``bank`` nodes are edge-
        isolated in v1. Node feature tensors ``x`` are placeholder
        ``torch.ones(N, 1)``. Edge labels (``is_laundering``) are
        stored on each triplet's ``.y`` tensor.
    """
    frame = _load_raw_csv(csv_dir)
    tables = _build_node_index_tables(frame)
    edges = _build_wire_transfer_edges(frame, tables)

    data = HeteroData()
    for node_type in ("individual", "business", "bank"):
        num_nodes = len(tables[node_type])
        data[node_type].num_nodes = num_nodes
        data[node_type].x = torch.ones(num_nodes, 1)

    for triplet, bundle in edges.items():
        store = data[triplet]
        store.edge_index = bundle.edge_index
        store.amount = bundle.amount
        store.timestamp = bundle.timestamp
        store.currency_flag = bundle.currency_flag
        store.y = bundle.is_laundering

    return data
