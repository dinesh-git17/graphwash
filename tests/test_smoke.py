"""Smoke test: package is importable."""

from __future__ import annotations

import graphwash


def test_package_importable() -> None:
    """graphwash package imports without error."""
    assert graphwash.__name__ == "graphwash"
