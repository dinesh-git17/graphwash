"""Deterministic SHA-256 account-type split.

Per ADR-0008 Decision point 4, account nodes are partitioned into
``individual`` (~70%) and ``business`` (~30%) via a deterministic
hash of the canonical composite ``(bank, account)`` id string
``"{bank}|{account}"``.

The hash policy uses an unbiased 8-byte slice comparison against a
threshold, replacing the modulo-biased ``digest[0] % 10 < 7`` from
the closed-without-merge PR #37 attempt.
"""

from __future__ import annotations

import hashlib
from typing import Final

ACCOUNT_TYPE_THRESHOLD: Final[int] = 7 * 2**64 // 10


def assign_account_type(composite_id: str) -> str:
    """Classify a composite ``(bank, account)`` id as individual or business.

    Args:
        composite_id: Canonical string ``"{bank}|{account}"``.

    Returns:
        ``"individual"`` if the SHA-256 digest's first 8 bytes
        interpret-as-big-endian-int land below
        ``ACCOUNT_TYPE_THRESHOLD``; otherwise ``"business"``.
    """
    digest = hashlib.sha256(composite_id.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big")
    return "individual" if bucket < ACCOUNT_TYPE_THRESHOLD else "business"
