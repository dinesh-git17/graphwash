"""IT-AML HI-Medium HeteroData construction.

Public entry point: ``build_hetero_data(csv_dir)``. See
``docs/superpowers/specs/2026-04-22-t-024-hetero-data-construction-design.md``
for the full design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import pandas as pd

from graphwash.data import schema
from graphwash.data.node_types import assign_account_type

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray
    from torch import Tensor
    from torch_geometric.data import HeteroData

RELATIVE_TIMESTAMP_MARGIN_S: Final[int] = 10

INDIVIDUAL_CODE: Final[int] = 0
BUSINESS_CODE: Final[int] = 1

_READ_CSV_DTYPES: Final[dict[str, str]] = {
    "From Bank": "int32",
    "To Bank": "int32",
    "Account": "string",
    "Account.1": "string",
    "Amount Paid": "float32",
    "Receiving Currency": "category",
    "Payment Currency": "category",
    "Is Laundering": "int8",
}

_USECOLS: Final[tuple[str, ...]] = (
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account.1",
    "Amount Paid",
    "Receiving Currency",
    "Payment Currency",
    "Is Laundering",
)


@dataclass(frozen=True, slots=True)
class NodeIndexBundle:
    """Canonical per-composite and per-bank node index table."""

    composite_ids: tuple[str, ...]
    bank_id_per_composite: NDArray[np.int32]
    account_type_per_composite: NDArray[np.uint8]
    individual_local_idx: NDArray[np.int64]
    business_local_idx: NDArray[np.int64]
    bank_ordered: NDArray[np.int32]


@dataclass(frozen=True, slots=True)
class WireTransferEdgeBundle:
    """Per-triplet wire_transfer edge store payload."""

    edge_index: Tensor
    amount_paid: Tensor
    timestamp: Tensor
    cross_currency: Tensor
    y: Tensor


@dataclass(frozen=True, slots=True)
class AtBankEdgeBundle:
    """Per-account-type at_bank edge store payload."""

    edge_index: Tensor


def _load_raw_csv(csv_path: Path) -> pd.DataFrame:
    """Load the raw HI-Medium CSV with typed dtypes applied.

    Drops ``Amount Received`` and ``Payment Format`` via ``usecols``
    (unused by T-024 per the spec). Timestamps are parsed into
    ``datetime64[ns]`` using the captured ``TIMESTAMP_FORMAT``.

    Raises:
        FileNotFoundError: ``csv_path`` does not exist.
        ValueError: CSV is empty or columns disagree with the
            expected post-rename set.
    """
    resolved_path = csv_path.resolve()
    if not csv_path.is_file():
        msg = f"expected HI-Medium CSV at {resolved_path}"
        raise FileNotFoundError(msg)

    try:
        df = pd.read_csv(
            csv_path,
            usecols=list(_USECOLS),
            dtype={
                column: dtype
                for column, dtype in _READ_CSV_DTYPES.items()
                if column in _USECOLS
            },
            parse_dates=["Timestamp"],
            date_format=schema.TIMESTAMP_FORMAT,
        )
    except ValueError as error:
        msg = f"column set mismatch at {resolved_path}: {error}"
        raise ValueError(msg) from error

    if len(df) == 0:
        msg = f"CSV at {resolved_path} is empty (no data rows)"
        raise ValueError(msg)

    df = df.rename(columns=schema.RENAME_MAP)

    expected = {schema.RENAME_MAP[column] for column in _USECOLS}
    if set(df.columns) != expected:
        msg = (
            f"column set mismatch at {resolved_path}: "
            f"expected {sorted(expected)}, got {sorted(df.columns)}"
        )
        raise ValueError(msg)

    return df


def _drop_self_loops(df: pd.DataFrame) -> pd.DataFrame:
    """Drop self-loop rows per PRD section 15.

    Self-loop transfers (account-to-itself) are simulator artifacts
    with no AML signal. Dropping here, before the composite
    factorise, also satisfies the adjacent "isolated accounts:
    exclude" clause for any account whose only raw activity is a
    self-loop.
    """
    self_loop_mask = (df["from_bank"] == df["to_bank"]) & (
        df["from_account"] == df["to_account"]
    )
    return df.loc[~self_loop_mask].reset_index(drop=True)


def _build_account_node_index(
    df: pd.DataFrame,
) -> tuple[NodeIndexBundle, pd.DataFrame]:
    """Factorise composite (bank, account) nodes and assign types.

    Returns the partial ``NodeIndexBundle`` (account portion; bank
    portion populated by ``_build_bank_index``) and ``df`` augmented
    with two new ``int64`` columns ``from_composite_idx`` and
    ``to_composite_idx`` for downstream edge construction.
    """
    from_composite = df["from_bank"].astype(str) + "|" + df["from_account"].astype(str)
    to_composite = df["to_bank"].astype(str) + "|" + df["to_account"].astype(str)

    union = pd.concat([from_composite, to_composite], ignore_index=True)
    codes, categories = pd.factorize(union, sort=False)

    composite_ids = tuple(categories.tolist())
    num_composites = len(composite_ids)

    bank_id_per_composite = np.array(
        [int(composite_id.split("|", 1)[0]) for composite_id in composite_ids],
        dtype=np.int32,
    )

    account_type_per_composite = np.empty(num_composites, dtype=np.uint8)
    for i, composite_id in enumerate(composite_ids):
        account_type_per_composite[i] = (
            INDIVIDUAL_CODE
            if assign_account_type(composite_id) == "individual"
            else BUSINESS_CODE
        )

    individual_mask = account_type_per_composite == INDIVIDUAL_CODE
    business_mask = account_type_per_composite == BUSINESS_CODE

    individual_local_idx = np.full(num_composites, -1, dtype=np.int64)
    business_local_idx = np.full(num_composites, -1, dtype=np.int64)
    individual_local_idx[individual_mask] = np.arange(int(individual_mask.sum()))
    business_local_idx[business_mask] = np.arange(int(business_mask.sum()))

    n_rows = len(df)
    df = df.copy()
    df["from_composite_idx"] = codes[:n_rows].astype(np.int64)
    df["to_composite_idx"] = codes[n_rows:].astype(np.int64)

    bundle = NodeIndexBundle(
        composite_ids=composite_ids,
        bank_id_per_composite=bank_id_per_composite,
        account_type_per_composite=account_type_per_composite,
        individual_local_idx=individual_local_idx,
        business_local_idx=business_local_idx,
        bank_ordered=np.empty(0, dtype=np.int32),
    )
    return bundle, df


def _build_bank_index(
    df: pd.DataFrame,
    bundle: NodeIndexBundle,
) -> NodeIndexBundle:
    """Populate the bank portion of the NodeIndexBundle.

    ``bank_ordered`` is the sorted union of ``from_bank`` and
    ``to_bank``. Lookups at use sites call ``np.searchsorted`` so
    there is no density assumption on bank id range.
    """
    bank_ordered = np.unique(
        np.concatenate(
            [df["from_bank"].to_numpy(), df["to_bank"].to_numpy()],
        ),
    ).astype(np.int32)
    return NodeIndexBundle(
        composite_ids=bundle.composite_ids,
        bank_id_per_composite=bundle.bank_id_per_composite,
        account_type_per_composite=bundle.account_type_per_composite,
        individual_local_idx=bundle.individual_local_idx,
        business_local_idx=bundle.business_local_idx,
        bank_ordered=bank_ordered,
    )


def build_hetero_data(csv_dir: Path) -> HeteroData:
    """Construct the HeteroData object for the IT-AML HI-Medium dataset.

    Args:
        csv_dir: Directory containing ``HI-Medium_Trans.csv``.

    Returns:
        A PyG ``HeteroData`` with three node types
        (``individual``, ``business``, ``bank``), two edge types
        (``wire_transfer``, ``at_bank``), and the namespaced
        metadata attributes documented in the spec.
    """
    msg = "implemented in later tasks"
    raise NotImplementedError(msg)
