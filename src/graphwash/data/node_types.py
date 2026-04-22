"""Deterministic account node-type assignment.

Background
----------
The IT-AML HI-Medium raw CSV does not carry an individual-vs-business
marker on account rows. REQ-001 requires three node types; we split
account ids into ``individual`` and ``business`` via a deterministic
SHA-256 hash so the same ``account_id`` always maps to the same type
across training and inference.

This is a synthetic-data simplification, acknowledged in the project
PRD and README. The 70/30 target split is arbitrary but stable.
"""

from __future__ import annotations

import hashlib
from typing import Final, Literal

AccountNodeType = Literal["individual", "business"]

_HASH_MODULUS: Final[int] = 10
_INDIVIDUAL_THRESHOLD: Final[int] = 7

BUSINESS_NODE_SHARE: Final[float] = (
    _HASH_MODULUS - _INDIVIDUAL_THRESHOLD
) / _HASH_MODULUS


def assign_account_node_type(account_id: str) -> AccountNodeType:
    """Return the node type for ``account_id``.

    Args:
        account_id: Raw account identifier from the IT-AML CSV.

    Returns:
        ``"individual"`` for the first ``_INDIVIDUAL_THRESHOLD / _HASH_MODULUS``
        of the hash space, ``"business"`` for the remainder.
    """
    digest = hashlib.sha256(account_id.encode("utf-8")).digest()
    bucket = digest[0] % _HASH_MODULUS
    return "individual" if bucket < _INDIVIDUAL_THRESHOLD else "business"
