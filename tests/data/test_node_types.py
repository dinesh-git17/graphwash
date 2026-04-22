"""Tests for deterministic account node-type assignment."""

from __future__ import annotations

import random
import string
from collections import Counter

from graphwash.data.node_types import (
    BUSINESS_NODE_SHARE,
    assign_account_node_type,
)


def _random_account_id(rng: random.Random) -> str:
    return "".join(rng.choices(string.hexdigits.upper(), k=16))


def test_assignment_is_deterministic_per_id() -> None:
    account_id = "ABCD1234EF567890"
    first = assign_account_node_type(account_id)
    second = assign_account_node_type(account_id)
    assert first == second


def test_distinct_ids_produce_both_types() -> None:
    rng = random.Random(0)  # noqa: S311
    ids = [_random_account_id(rng) for _ in range(500)]
    types = {assign_account_node_type(a) for a in ids}
    assert types == {"individual", "business"}


def test_distribution_matches_target_share_within_tolerance() -> None:
    rng = random.Random(1)  # noqa: S311
    sample_size = 10_000
    ids = [_random_account_id(rng) for _ in range(sample_size)]
    counts = Counter(assign_account_node_type(a) for a in ids)

    observed_business = counts["business"] / sample_size
    tolerance = 0.02
    assert abs(observed_business - BUSINESS_NODE_SHARE) < tolerance


def test_return_type_is_literal() -> None:
    value = assign_account_node_type("some_id")
    assert value in {"individual", "business"}
