"""Tests for src/graphwash/data/node_types.py."""

from __future__ import annotations

from collections import Counter

from graphwash.data import node_types
from graphwash.data.node_types import ACCOUNT_TYPE_THRESHOLD, assign_account_type


def test_threshold_is_exact_integer_seven_tenths_of_two_to_the_sixtyfour() -> None:
    """Threshold must use exact integer arithmetic, not float.

    float(0.7 * 2**64) loses precision at the 2**64 scale;
    7 * 2**64 // 10 is exact.
    """
    assert ACCOUNT_TYPE_THRESHOLD == 7 * 2**64 // 10
    assert ACCOUNT_TYPE_THRESHOLD == 12_912_720_851_596_686_131


def test_assign_account_type_is_deterministic() -> None:
    composite = "42|abc12345"
    first = assign_account_type(composite)
    second = assign_account_type(composite)
    assert first == second
    assert first in {"individual", "business"}


def test_assign_account_type_golden_values() -> None:
    """Pin three hand-picked composites against hardcoded hash outputs.

    Literal labels recorded by computing SHA-256 once against
    ACCOUNT_TYPE_THRESHOLD = 7 * 2**64 // 10. Any change to the hash
    policy (different algorithm, different byte width, different
    threshold) will surface as a test diff rather than a silent
    distribution drift. See plan Task 3 Step 1a for the derivation.
    """
    assert assign_account_type("1|alpha") == "individual"
    assert assign_account_type("2|beta") == "individual"
    assert assign_account_type("3|gamma") == "business"


def test_distribution_at_one_hundred_thousand() -> None:
    """Unbiased hash lands within +/- 0.5% of 70/30 at N=100k.

    Guards against any accidental reintroduction of modulo bias.
    PR #37 used digest[0] % 10 < 7 which lands at 70.7 / 29.3
    and would fail this test.
    """
    composites = [f"{bank}|acct_{i}" for bank in range(5) for i in range(20_000)]
    assert len(composites) == 100_000

    counts = Counter(assign_account_type(c) for c in composites)
    individual_fraction = counts["individual"] / 100_000
    business_fraction = counts["business"] / 100_000

    assert abs(individual_fraction - 0.70) < 0.005
    assert abs(business_fraction - 0.30) < 0.005
    assert counts["individual"] + counts["business"] == 100_000


def test_module_does_not_mutate_globals() -> None:
    """Spot-check: calling the function leaves module globals unchanged."""
    before = set(vars(node_types).keys())
    assign_account_type("999|immutability_check")
    after = set(vars(node_types).keys())
    assert before == after
