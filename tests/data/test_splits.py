"""Tests for ``graphwash.data.splits.stratified_split``.

Exercises T-025 acceptance (sizes sum, ratio preserved, seed reproduces)
plus invariants from the design doc at
``docs/superpowers/specs/2026-04-23-t-025-stratified-splits-design.md``.
"""

from __future__ import annotations

import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pytest
import torch
from torch_geometric.data import HeteroData

from graphwash.data.splits import stratified_split


@pytest.mark.parametrize(
    ("ratios", "reason"),
    [
        ((0.7, 0.2, 0.2), "wrong_sum"),
        ((0.5, 0.5), "wrong_length"),
        ((-0.1, 0.5, 0.6), "negative_ratio"),
        ((float("nan"), 0.5, 0.5), "nan_ratio"),
    ],
)
def test_ratios_validation_raises(
    ratios: tuple[float, ...],
    reason: str,
) -> None:
    del reason
    empty = HeteroData()
    empty["individual"].x = torch.zeros((1, 2))
    with pytest.raises(ValueError, match="ratios"):
        stratified_split(empty, ratios, seed=0)  # type: ignore[arg-type]


def test_non_cpu_input_raises() -> None:
    fake = HeteroData()
    fake["individual"].x = torch.zeros((1, 2))
    triplet = ("individual", "wire_transfer", "individual")
    fake[triplet].edge_index = torch.zeros((2, 1), dtype=torch.long)
    fake[triplet].y = torch.zeros(1, dtype=torch.int8)

    class _FakeDevice:
        type = "cuda"

    class _FakeTensor:
        device = _FakeDevice()

    fake[triplet].y = _FakeTensor()

    with pytest.raises(ValueError, match="CPU tensors"):
        stratified_split(fake, (1.0, 0.0, 0.0), seed=0)


def empty_wire_transfer_data() -> HeteroData:
    """HeteroData with no wire_transfer triplets.

    Matches the loader's behaviour when there are no wire_transfer rows
    to emit. Node stores, at_bank triplets, and all four graphwash_*
    metadata attributes are present.
    """
    data = HeteroData()
    data["individual"].x = torch.zeros((2, 3))
    data["business"].x = torch.zeros((1, 3))
    data["bank"].x = torch.zeros((1, 2))
    data[("individual", "at_bank", "bank")].edge_index = torch.tensor(
        [[0, 1], [0, 0]],
        dtype=torch.long,
    )
    data[("business", "at_bank", "bank")].edge_index = torch.tensor(
        [[0], [0]],
        dtype=torch.long,
    )
    data.graphwash_timestamp_epoch_s = 1_661_990_390
    data.graphwash_bank_ids = np.array([101], dtype="int64")
    data.graphwash_individual_composite_ids = ("101|a", "101|b")
    data.graphwash_business_composite_ids = ("101|c",)
    return data


def test_empty_source_returns_three_empty_splits() -> None:
    data = empty_wire_transfer_data()
    out_train, out_val, out_test = stratified_split(
        data,
        (0.7, 0.15, 0.15),
        seed=42,
    )
    expected_at_bank = {
        ("individual", "at_bank", "bank"),
        ("business", "at_bank", "bank"),
    }
    for split in (out_train, out_val, out_test):
        assert split.node_types == ["individual", "business", "bank"]
        assert set(split.edge_types) == expected_at_bank
        for at_bank in expected_at_bank:
            assert torch.equal(
                split[at_bank].edge_index,
                data[at_bank].edge_index,
            )
        assert split.graphwash_timestamp_epoch_s == data.graphwash_timestamp_epoch_s
        assert split.graphwash_bank_ids is data.graphwash_bank_ids
        assert (
            split.graphwash_individual_composite_ids
            == data.graphwash_individual_composite_ids
        )
        assert (
            split.graphwash_business_composite_ids
            == data.graphwash_business_composite_ids
        )


_FIXTURE_SEED = 2026_04_23

_N_NODES = 10
_N_BANKS = 2
_TIMESTAMP_MAX = 10_000

_TRIPLET_IVI = ("individual", "wire_transfer", "individual")
_TRIPLET_IVB = ("individual", "wire_transfer", "business")
_TRIPLET_BVI = ("business", "wire_transfer", "individual")


def small_stratifiable_data() -> HeteroData:
    """1000-edge HeteroData with 100 positives (10% local illicit rate).

    Spread across three source-present wire_transfer triplets. Each
    wire_transfer store carries a fixture-only ``test_edge_id`` with
    globally unique ids, used by the seed-diff test to observe the
    edge partition without ambiguity under shared endpoints.
    """
    rng = torch.Generator().manual_seed(_FIXTURE_SEED)
    data = HeteroData()
    data["individual"].x = torch.zeros((_N_NODES, 3))
    data["business"].x = torch.zeros((_N_NODES, 3))
    data["bank"].x = torch.zeros((_N_BANKS, 2))
    data[("individual", "at_bank", "bank")].edge_index = torch.tensor(
        [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0] * _N_NODES],
        dtype=torch.long,
    )
    data[("business", "at_bank", "bank")].edge_index = torch.tensor(
        [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1] * _N_NODES],
        dtype=torch.long,
    )

    triplet_specs = (
        (_TRIPLET_IVI, 400, 40, 0),
        (_TRIPLET_IVB, 300, 30, 400),
        (_TRIPLET_BVI, 300, 30, 700),
    )
    for triplet, n_edges, n_pos, id_offset in triplet_specs:
        edge_index = torch.randint(
            0,
            _N_NODES,
            (2, n_edges),
            generator=rng,
            dtype=torch.long,
        )
        amount_paid = torch.rand(n_edges, generator=rng, dtype=torch.float32)
        timestamp = torch.randint(
            0,
            _TIMESTAMP_MAX,
            (n_edges,),
            generator=rng,
            dtype=torch.long,
        )
        cross_currency = torch.zeros(n_edges, dtype=torch.int8)
        y = torch.zeros(n_edges, dtype=torch.int8)
        y[:n_pos] = 1
        test_edge_id = torch.arange(
            id_offset,
            id_offset + n_edges,
            dtype=torch.long,
        )
        store = data[triplet]
        store.edge_index = edge_index
        store.amount_paid = amount_paid
        store.timestamp = timestamp
        store.cross_currency = cross_currency
        store.y = y
        store.test_edge_id = test_edge_id

    data.graphwash_timestamp_epoch_s = 1_661_990_390
    data.graphwash_bank_ids = np.array([101, 202], dtype="int64")
    data.graphwash_individual_composite_ids = tuple(
        f"101|ind_{i}" for i in range(_N_NODES)
    )
    data.graphwash_business_composite_ids = tuple(
        f"202|biz_{i}" for i in range(_N_NODES)
    )
    return data


WIRE_TRIPLETS = (
    _TRIPLET_IVI,
    _TRIPLET_IVB,
    _TRIPLET_BVI,
)


def _total_edges(data: HeteroData) -> int:
    return sum(
        int(data[t].edge_index.size(1))
        for t in data.edge_types
        if t[1] == "wire_transfer"
    )


def _illicit_rate(data: HeteroData) -> float:
    y_parts = [data[t].y for t in data.edge_types if t[1] == "wire_transfer"]
    if not y_parts:
        return 0.0
    y_all = torch.cat(y_parts)
    return float(y_all.sum().item()) / float(y_all.numel())


_REL_ERR_TOLERANCE = 0.005
_DEFAULT_RATIOS = (0.7, 0.15, 0.15)
_DEFAULT_SEED = 42


def test_split_sizes_sum_to_source() -> None:
    data = small_stratifiable_data()
    out_train, out_val, out_test = stratified_split(
        data,
        _DEFAULT_RATIOS,
        seed=_DEFAULT_SEED,
    )
    for triplet in WIRE_TRIPLETS:
        src_n = int(data[triplet].edge_index.size(1))
        total = sum(
            int(split[triplet].edge_index.size(1))
            for split in (out_train, out_val, out_test)
        )
        assert total == src_n, f"{triplet}: {total} != {src_n}"


def test_illicit_ratio_preserved_relative() -> None:
    data = small_stratifiable_data()
    global_rate = _illicit_rate(data)
    out_train, out_val, out_test = stratified_split(
        data,
        _DEFAULT_RATIOS,
        seed=_DEFAULT_SEED,
    )
    for split in (out_train, out_val, out_test):
        rate = _illicit_rate(split)
        rel_err = abs(rate - global_rate) / global_rate
        assert rel_err <= _REL_ERR_TOLERANCE, (
            f"split rate {rate} vs global {global_rate} "
            f"relative error {rel_err} > {_REL_ERR_TOLERANCE}"
        )


def test_same_seed_reproduces_splits() -> None:
    data = small_stratifiable_data()
    a = stratified_split(data, _DEFAULT_RATIOS, seed=_DEFAULT_SEED)
    b = stratified_split(data, _DEFAULT_RATIOS, seed=_DEFAULT_SEED)
    for s_a, s_b in zip(a, b, strict=True):
        for triplet in WIRE_TRIPLETS:
            for key in (
                "edge_index",
                "amount_paid",
                "timestamp",
                "cross_currency",
                "y",
                "test_edge_id",
            ):
                assert torch.equal(
                    getattr(s_a[triplet], key),
                    getattr(s_b[triplet], key),
                ), f"{triplet}.{key} differs between runs"


def test_outputs_validate_as_pyg_graphs() -> None:
    data = small_stratifiable_data()
    outputs = stratified_split(data, _DEFAULT_RATIOS, seed=_DEFAULT_SEED)
    for split in outputs:
        assert split.validate() is True
        assert split.node_types == data.node_types
        assert set(split.edge_types) == set(data.edge_types)


def test_zero_ratio_puts_everything_in_train() -> None:
    data = small_stratifiable_data()
    out_train, out_val, out_test = stratified_split(
        data,
        (1.0, 0.0, 0.0),
        seed=7,
    )
    assert _total_edges(out_train) == _total_edges(data)
    assert _total_edges(out_val) == 0
    assert _total_edges(out_test) == 0
    for triplet in WIRE_TRIPLETS:
        for split in (out_val, out_test):
            store = split[triplet]
            assert store.edge_index.shape == (2, 0)
            assert store.amount_paid.shape == (0,)
            assert store.timestamp.shape == (0,)
            assert store.cross_currency.shape == (0,)
            assert store.y.shape == (0,)


def test_rounded_to_zero_triplet_store_is_shaped_empty() -> None:
    data = small_stratifiable_data()
    tiny_triplet = ("business", "wire_transfer", "business")
    data[tiny_triplet].edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long)
    data[tiny_triplet].amount_paid = torch.tensor([0.1, 0.2], dtype=torch.float32)
    data[tiny_triplet].timestamp = torch.tensor([100, 200], dtype=torch.long)
    data[tiny_triplet].cross_currency = torch.zeros(2, dtype=torch.int8)
    data[tiny_triplet].y = torch.zeros(2, dtype=torch.int8)
    data[tiny_triplet].test_edge_id = torch.tensor([9998, 9999], dtype=torch.long)

    out_train, out_val, out_test = stratified_split(
        data,
        (0.95, 0.025, 0.025),
        seed=3,
    )
    for split in (out_train, out_val, out_test):
        assert tiny_triplet in split.edge_types
        store = split[tiny_triplet]
        assert store.edge_index.dtype == torch.long
        assert store.amount_paid.dtype == torch.float32
        assert store.timestamp.dtype == torch.long
        assert store.cross_currency.dtype == torch.int8
        assert store.y.dtype == torch.int8
        assert store.test_edge_id.dtype == torch.long


def test_split_invariant_data_not_copied() -> None:
    data = small_stratifiable_data()
    out_train, out_val, out_test = stratified_split(
        data,
        _DEFAULT_RATIOS,
        seed=_DEFAULT_SEED,
    )
    for split in (out_train, out_val, out_test):
        for node_type in ("individual", "business", "bank"):
            assert split[node_type].x.data_ptr() == data[node_type].x.data_ptr()
        for at_bank in (
            ("individual", "at_bank", "bank"),
            ("business", "at_bank", "bank"),
        ):
            assert (
                split[at_bank].edge_index.data_ptr()
                == data[at_bank].edge_index.data_ptr()
            )
        assert split.graphwash_bank_ids is data.graphwash_bank_ids
        assert split.graphwash_timestamp_epoch_s == data.graphwash_timestamp_epoch_s
        assert (
            split.graphwash_individual_composite_ids
            == data.graphwash_individual_composite_ids
        )
        assert (
            split.graphwash_business_composite_ids
            == data.graphwash_business_composite_ids
        )


def _train_edge_ids(splits: tuple[HeteroData, HeteroData, HeteroData]) -> set[int]:
    train = splits[0]
    ids: set[int] = set()
    for triplet in train.edge_types:
        if triplet[1] != "wire_transfer":
            continue
        tensor = train[triplet].test_edge_id
        ids.update(int(i) for i in tensor.tolist())
    return ids


def test_different_seed_produces_different_partition() -> None:
    data = small_stratifiable_data()
    a = stratified_split(data, _DEFAULT_RATIOS, seed=42)
    b = stratified_split(data, _DEFAULT_RATIOS, seed=43)
    assert _train_edge_ids(a) != _train_edge_ids(b)


@pytest.mark.slow
def test_stratified_split_fits_budget_on_hi_medium(
    capsys: pytest.CaptureFixture[str],
) -> None:
    if os.environ.get("RUN_SLOW") != "1":
        pytest.skip("RUN_SLOW=1 env flag not set")
    data_dir = os.environ.get("GRAPHWASH_DATA_DIR")
    if not data_dir:
        pytest.skip("GRAPHWASH_DATA_DIR not set")
    from graphwash.data.loader import build_hetero_data  # noqa: PLC0415

    data = build_hetero_data(Path(data_dir))
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start = time.perf_counter()
    _ = stratified_split(data, (0.7, 0.15, 0.15), seed=42)
    elapsed = time.perf_counter() - start
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # ru_maxrss units: bytes on darwin, kilobytes on linux.
    divisor = 1 if sys.platform == "darwin" else 1024
    peak_mb = rss_after / divisor / (1024 * 1024)
    delta_mb = max(0, (rss_after - rss_before)) / divisor / (1024 * 1024)

    with capsys.disabled():
        print(  # noqa: T201
            f"\n[t-025 benchmark] elapsed={elapsed:.2f}s "
            f"peak_rss={peak_mb:.1f}MB delta_rss={delta_mb:.1f}MB",
        )

    assert elapsed < 60.0, f"stratified_split on HI-Medium took {elapsed:.1f}s"
