"""IT-AML HI-Medium HeteroData construction.

Public entry point: ``build_hetero_data(csv_dir)``. See
``docs/superpowers/specs/2026-04-22-t-024-hetero-data-construction-design.md``
for the full design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np
    from numpy.typing import NDArray
    from torch import Tensor
    from torch_geometric.data import HeteroData

RELATIVE_TIMESTAMP_MARGIN_S: Final[int] = 10

INDIVIDUAL_CODE: Final[int] = 0
BUSINESS_CODE: Final[int] = 1


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
