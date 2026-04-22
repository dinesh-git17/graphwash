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
import torch
from torch_geometric.data import HeteroData

from graphwash.data import schema
from graphwash.data.node_types import assign_account_type

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray
    from torch import Tensor

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
    from_composite = (
        df["from_bank"]
        .astype("string")
        .str.cat(
            df["from_account"].astype("string"),
            sep="|",
        )
    )
    to_composite = (
        df["to_bank"]
        .astype("string")
        .str.cat(
            df["to_account"].astype("string"),
            sep="|",
        )
    )

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


def _encode_relative_timestamps(
    df: pd.DataFrame,
) -> tuple[NDArray[np.int64], int]:
    """Encode timestamps as IBM-convention relative seconds.

    Returns ``(rel_ts, dataset_epoch_s)`` where
    ``rel_ts = unix_s - dataset_epoch_s`` and
    ``dataset_epoch_s = floor(unix_s.min() / 86400) * 86400
                       - RELATIVE_TIMESTAMP_MARGIN_S``.

    Raises:
        ValueError: computed epoch is negative or non-finite
            (indicates an all-NaT timestamp column).
    """
    unix_s = df["timestamp"].astype("datetime64[s]").astype("int64").to_numpy()
    min_unix = int(unix_s.min())
    if min_unix < 0:
        msg = (
            f"negative or non-finite epoch from unix_s.min()={min_unix}; "
            "check timestamp parsing for NaT rows"
        )
        raise ValueError(msg)
    dataset_epoch_s = (min_unix // 86400) * 86400 - RELATIVE_TIMESTAMP_MARGIN_S
    rel_ts = (unix_s - dataset_epoch_s).astype(np.int64)
    return rel_ts, dataset_epoch_s


def _compute_account_features(
    df: pd.DataFrame,
    bundle: NodeIndexBundle,
) -> dict[str, Tensor]:
    """Seven-feature per-type account aggregates.

    Columns (in order):
        0 out_count
        1 in_count
        2 out_amount_sum
        3 in_amount_sum
        4 unique_counterparty_count (undirected)
        5 cross_currency_out_count
        6 cross_currency_in_count
    """
    from scipy.sparse import csr_matrix  # type: ignore[import-untyped]  # noqa: PLC0415

    n = len(bundle.composite_ids)
    cross_currency_mask = (
        df["receiving_currency"].astype(str) != df["payment_currency"].astype(str)
    ).to_numpy()

    out_count = np.bincount(
        df["from_composite_idx"].to_numpy(),
        minlength=n,
    ).astype(np.float32)
    in_count = np.bincount(
        df["to_composite_idx"].to_numpy(),
        minlength=n,
    ).astype(np.float32)

    out_amount_sum = (
        df.groupby("from_composite_idx")["amount_paid"]
        .sum()
        .reindex(range(n), fill_value=0.0)
        .to_numpy()
        .astype(np.float32)
    )
    in_amount_sum = (
        df.groupby("to_composite_idx")["amount_paid"]
        .sum()
        .reindex(range(n), fill_value=0.0)
        .to_numpy()
        .astype(np.float32)
    )

    cross_out = np.bincount(
        df["from_composite_idx"].to_numpy(),
        weights=cross_currency_mask.astype(np.int64),
        minlength=n,
    ).astype(np.float32)
    cross_in = np.bincount(
        df["to_composite_idx"].to_numpy(),
        weights=cross_currency_mask.astype(np.int64),
        minlength=n,
    ).astype(np.float32)

    e = len(df)
    rows = np.concatenate(
        [
            df["from_composite_idx"].to_numpy(),
            df["to_composite_idx"].to_numpy(),
        ],
    )
    cols = np.concatenate(
        [
            df["to_composite_idx"].to_numpy(),
            df["from_composite_idx"].to_numpy(),
        ],
    )
    adj = csr_matrix(
        (np.ones(2 * e, dtype=np.int8), (rows, cols)),
        shape=(n, n),
    )
    adj.sum_duplicates()
    unique_counterparty_count = np.diff(adj.indptr).astype(np.float32)

    features_per_composite = np.stack(
        [
            out_count,
            in_count,
            out_amount_sum,
            in_amount_sum,
            unique_counterparty_count,
            cross_out,
            cross_in,
        ],
        axis=1,
    )

    individual_mask = bundle.account_type_per_composite == INDIVIDUAL_CODE
    business_mask = bundle.account_type_per_composite == BUSINESS_CODE

    return {
        "individual": torch.from_numpy(features_per_composite[individual_mask]),
        "business": torch.from_numpy(features_per_composite[business_mask]),
    }


def _compute_bank_features(
    df: pd.DataFrame,
    bundle: NodeIndexBundle,
) -> Tensor:
    """Seven-feature bank aggregates.

    Columns (in order):
        0 member_account_count
        1 outbound_transfer_count
        2 inbound_transfer_count
        3 outbound_amount_sum
        4 inbound_amount_sum
        5 internal_transfer_count
        6 external_transfer_count
    """
    n_bank = len(bundle.bank_ordered)

    from_bank_arr = df["from_bank"].to_numpy()
    to_bank_arr = df["to_bank"].to_numpy()
    amount = df["amount_paid"].to_numpy().astype(np.float64)

    from_local = np.searchsorted(bundle.bank_ordered, from_bank_arr)
    to_local = np.searchsorted(bundle.bank_ordered, to_bank_arr)

    member_count = np.zeros(n_bank, dtype=np.float32)
    member_locals = np.searchsorted(
        bundle.bank_ordered,
        bundle.bank_id_per_composite,
    )
    np.add.at(member_count, member_locals, 1.0)

    out_count = np.zeros(n_bank, dtype=np.float32)
    in_count = np.zeros(n_bank, dtype=np.float32)
    out_amount = np.zeros(n_bank, dtype=np.float64)
    in_amount = np.zeros(n_bank, dtype=np.float64)
    internal_count = np.zeros(n_bank, dtype=np.float32)
    external_count = np.zeros(n_bank, dtype=np.float32)

    np.add.at(out_count, from_local, 1.0)
    np.add.at(in_count, to_local, 1.0)
    np.add.at(out_amount, from_local, amount)
    np.add.at(in_amount, to_local, amount)

    same_bank_mask = from_bank_arr == to_bank_arr
    np.add.at(internal_count, from_local[same_bank_mask], 1.0)

    diff_mask = ~same_bank_mask
    np.add.at(external_count, from_local[diff_mask], 1.0)
    np.add.at(external_count, to_local[diff_mask], 1.0)

    features = np.stack(
        [
            member_count,
            out_count,
            in_count,
            out_amount.astype(np.float32),
            in_amount.astype(np.float32),
            internal_count,
            external_count,
        ],
        axis=1,
    ).astype(np.float32)

    return torch.from_numpy(features)


def _build_wire_transfer_edges(
    df: pd.DataFrame,
    bundle: NodeIndexBundle,
    rel_ts: NDArray[np.int64],
) -> dict[tuple[str, str, str], WireTransferEdgeBundle]:
    """Build per-triplet wire_transfer edge bundles.

    Emits one ``WireTransferEdgeBundle`` for each ``(src_type,
    dst_type)`` combination actually present in the data. Triplets
    with zero rows are not emitted.
    """
    src_type = bundle.account_type_per_composite[df["from_composite_idx"].to_numpy()]
    dst_type = bundle.account_type_per_composite[df["to_composite_idx"].to_numpy()]

    cross_currency_mask = (
        (df["receiving_currency"].astype(str) != df["payment_currency"].astype(str))
        .to_numpy()
        .astype(np.int8)
    )

    type_names = {INDIVIDUAL_CODE: "individual", BUSINESS_CODE: "business"}
    local_by_type = {
        INDIVIDUAL_CODE: bundle.individual_local_idx,
        BUSINESS_CODE: bundle.business_local_idx,
    }

    edges: dict[tuple[str, str, str], WireTransferEdgeBundle] = {}
    for src_code in (INDIVIDUAL_CODE, BUSINESS_CODE):
        for dst_code in (INDIVIDUAL_CODE, BUSINESS_CODE):
            mask = (src_type == src_code) & (dst_type == dst_code)
            if not mask.any():
                continue

            src_local = local_by_type[src_code][
                df["from_composite_idx"].to_numpy()[mask]
            ]
            dst_local = local_by_type[dst_code][df["to_composite_idx"].to_numpy()[mask]]
            edge_index = torch.from_numpy(
                np.stack([src_local, dst_local], axis=0).astype(np.int64),
            )
            amount_paid = torch.from_numpy(
                df["amount_paid"].to_numpy()[mask].astype(np.float32),
            )
            timestamp = torch.from_numpy(rel_ts[mask].astype(np.int64))
            cross_currency = torch.from_numpy(cross_currency_mask[mask])
            y = torch.from_numpy(
                df["is_laundering"].to_numpy()[mask].astype(np.int8),
            )

            edges[(type_names[src_code], "wire_transfer", type_names[dst_code])] = (
                WireTransferEdgeBundle(
                    edge_index=edge_index,
                    amount_paid=amount_paid,
                    timestamp=timestamp,
                    cross_currency=cross_currency,
                    y=y,
                )
            )

    return edges


def _build_at_bank_edges(
    bundle: NodeIndexBundle,
) -> dict[tuple[str, str, str], AtBankEdgeBundle]:
    """Build at_bank membership edges for each account type.

    Each account has exactly one at_bank edge pointing to its
    declared bank. No edge attributes.
    """
    type_names = {INDIVIDUAL_CODE: "individual", BUSINESS_CODE: "business"}
    local_by_type = {
        INDIVIDUAL_CODE: bundle.individual_local_idx,
        BUSINESS_CODE: bundle.business_local_idx,
    }

    edges: dict[tuple[str, str, str], AtBankEdgeBundle] = {}
    for code in (INDIVIDUAL_CODE, BUSINESS_CODE):
        composite_mask = bundle.account_type_per_composite == code
        if not composite_mask.any():
            continue
        src_local = local_by_type[code][composite_mask]
        dst_local = np.searchsorted(
            bundle.bank_ordered,
            bundle.bank_id_per_composite[composite_mask],
        ).astype(np.int64)
        edge_index = torch.from_numpy(
            np.stack([src_local, dst_local], axis=0).astype(np.int64),
        )
        edges[(type_names[code], "at_bank", "bank")] = AtBankEdgeBundle(
            edge_index=edge_index,
        )

    return edges


def _assemble_hetero_data(  # noqa: PLR0913
    bundle: NodeIndexBundle,
    account_features: dict[str, Tensor],
    bank_features: Tensor,
    wire_edges: dict[tuple[str, str, str], WireTransferEdgeBundle],
    at_bank_edges: dict[tuple[str, str, str], AtBankEdgeBundle],
    dataset_epoch_s: int,
) -> HeteroData:
    """Assemble the final HeteroData object.

    Args:
        bundle: Canonical node index table for this dataset.
        account_features: Per-type feature tensors keyed by
            ``"individual"`` and ``"business"``.
        bank_features: Feature tensor for bank nodes.
        wire_edges: Per-triplet wire_transfer edge bundles.
        at_bank_edges: Per-account-type at_bank edge bundles.
        dataset_epoch_s: IBM-convention dataset epoch in Unix seconds.

    Returns:
        A fully populated ``HeteroData`` carrying node features,
        edge stores, and the ``graphwash_*`` metadata attributes.
    """
    data = HeteroData()

    data["individual"].x = account_features["individual"]
    data["business"].x = account_features["business"]
    data["bank"].x = bank_features

    for triplet, eb in wire_edges.items():
        store = data[triplet]
        store.edge_index = eb.edge_index
        store.amount_paid = eb.amount_paid
        store.timestamp = eb.timestamp
        store.cross_currency = eb.cross_currency
        store.y = eb.y

    for triplet, ab_eb in at_bank_edges.items():
        data[triplet].edge_index = ab_eb.edge_index

    data.graphwash_timestamp_epoch_s = int(dataset_epoch_s)
    data.graphwash_bank_ids = bundle.bank_ordered.copy()

    individual_globals = np.where(
        bundle.account_type_per_composite == INDIVIDUAL_CODE,
    )[0]
    business_globals = np.where(
        bundle.account_type_per_composite == BUSINESS_CODE,
    )[0]
    data.graphwash_individual_composite_ids = tuple(
        bundle.composite_ids[i] for i in individual_globals
    )
    data.graphwash_business_composite_ids = tuple(
        bundle.composite_ids[i] for i in business_globals
    )

    return data


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
    csv_path = csv_dir / schema.RAW_FILENAME
    df = _load_raw_csv(csv_path)
    original_row_count = len(df)
    df = _drop_self_loops(df)
    self_loop_count = original_row_count - len(df)

    bundle, df = _build_account_node_index(df)
    bundle = _build_bank_index(df, bundle)
    rel_ts, dataset_epoch_s = _encode_relative_timestamps(df)

    account_features = _compute_account_features(df, bundle)
    bank_features = _compute_bank_features(df, bundle)
    wire_edges = _build_wire_transfer_edges(df, bundle, rel_ts)
    at_bank_edges = _build_at_bank_edges(bundle)

    data = _assemble_hetero_data(
        bundle=bundle,
        account_features=account_features,
        bank_features=bank_features,
        wire_edges=wire_edges,
        at_bank_edges=at_bank_edges,
        dataset_epoch_s=dataset_epoch_s,
    )

    total_wire_edges = sum(int(eb.edge_index.shape[1]) for eb in wire_edges.values())
    assert total_wire_edges == original_row_count - self_loop_count  # noqa: S101

    return data
