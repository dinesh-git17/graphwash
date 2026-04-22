"""Import-surface smoke tests for src/graphwash/data/loader.py."""

from __future__ import annotations

import dataclasses
from typing import Protocol

import pytest

from graphwash.data import loader


class DataclassParamsLike(Protocol):
    """Protocol for the dataclass params object on exported classes."""

    frozen: bool
    slots: bool


class DataclassExport(Protocol):
    """Protocol for exported dataclass types under test."""

    __dataclass_params__: DataclassParamsLike


def test_loader_exports_public_entry_point() -> None:
    assert hasattr(loader, "build_hetero_data")
    assert callable(loader.build_hetero_data)


def test_loader_exports_relative_timestamp_margin() -> None:
    assert loader.RELATIVE_TIMESTAMP_MARGIN_S == 10


def test_loader_exports_individual_and_business_codes() -> None:
    assert loader.INDIVIDUAL_CODE == 0
    assert loader.BUSINESS_CODE == 1


@pytest.mark.parametrize(
    "cls",
    [
        loader.NodeIndexBundle,
        loader.WireTransferEdgeBundle,
        loader.AtBankEdgeBundle,
    ],
    ids=["NodeIndexBundle", "WireTransferEdgeBundle", "AtBankEdgeBundle"],
)
def test_loader_exports_frozen_slotted_dataclass(cls: DataclassExport) -> None:
    assert dataclasses.is_dataclass(cls)
    params = cls.__dataclass_params__
    assert params.frozen is True
    assert params.slots is True
