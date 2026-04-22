"""Unit tests for scripts/download_data.py (T-023)."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from scripts.download_data import main

from graphwash.data.schema import RAW_FILENAME

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def redirect_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[], Path]:
    """Point the script's destination at ``tmp_path / data/raw/RAW_FILENAME``."""
    target = tmp_path / "data" / "raw" / RAW_FILENAME

    def _fake_destination() -> Path:
        return target

    monkeypatch.setattr(
        "scripts.download_data._destination",
        _fake_destination,
    )
    return lambda: target


def test_skip_when_file_present(
    redirect_destination: Callable[[], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = redirect_destination()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"existing content")

    with patch("scripts.download_data.KaggleApi") as mock_api:
        main([])

    mock_api.assert_not_called()
    captured = capsys.readouterr()
    assert "skipping" in captured.out
    assert RAW_FILENAME in captured.out


def test_download_when_file_absent(
    redirect_destination: Callable[[], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = redirect_destination()
    target.parent.mkdir(parents=True, exist_ok=True)

    with patch("scripts.download_data.KaggleApi") as mock_api_cls:
        mock_api = mock_api_cls.return_value
        main([])

    mock_api.authenticate.assert_called_once_with()
    mock_api.dataset_download_file.assert_called_once_with(
        "ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
        RAW_FILENAME,
        path=str(target.parent),
    )
    captured = capsys.readouterr()
    assert "Downloaded" in captured.out


def test_force_overrides_skip(
    redirect_destination: Callable[[], Path],
) -> None:
    target = redirect_destination()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"existing content")

    with patch("scripts.download_data.KaggleApi") as mock_api_cls:
        mock_api = mock_api_cls.return_value
        main(["--force"])

    mock_api.authenticate.assert_called_once_with()
    mock_api.dataset_download_file.assert_called_once_with(
        "ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
        RAW_FILENAME,
        path=str(target.parent),
    )


def test_mkdir_creates_missing_raw_dir(
    redirect_destination: Callable[[], Path],
) -> None:
    target = redirect_destination()
    assert not target.parent.exists()

    with patch("scripts.download_data.KaggleApi") as mock_api_cls:
        mock_api = mock_api_cls.return_value
        main([])

    assert target.parent.is_dir()
    mock_api.dataset_download_file.assert_called_once()


def test_extracts_zip_dropped_by_kaggle_and_removes_it(
    redirect_destination: Callable[[], Path],
) -> None:
    target = redirect_destination()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = b"id,amount\n1,100\n"

    def fake_download(
        dataset: str,  # noqa: ARG001
        file_name: str,
        path: str,
    ) -> None:
        zip_path = Path(path) / f"{file_name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(file_name, payload)

    with patch("scripts.download_data.KaggleApi") as mock_api_cls:
        mock_api_cls.return_value.dataset_download_file.side_effect = fake_download
        main([])

    assert target.is_file()
    assert target.read_bytes() == payload
    assert not (target.parent / f"{RAW_FILENAME}.zip").exists()
