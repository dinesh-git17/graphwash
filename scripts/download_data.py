"""Download IT-AML HI-Medium from Kaggle into data/raw/."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore[import-untyped]

from graphwash.data.schema import DATASET_SLUG, RAW_FILENAME

if TYPE_CHECKING:
    from collections.abc import Sequence


def _destination() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "raw" / RAW_FILENAME


def main(argv: Sequence[str] | None = None) -> None:
    """Download IT-AML HI-Medium from Kaggle into ``data/raw/``."""
    parser = argparse.ArgumentParser(
        description="Download IT-AML HI-Medium from Kaggle.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the file already exists.",
    )
    args = parser.parse_args(argv)

    destination = _destination()

    if destination.is_file() and not args.force:
        print(
            f"Already present at data/raw/{RAW_FILENAME}, "
            "skipping (use --force to re-download)",
        )
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    api.dataset_download_file(
        DATASET_SLUG,
        RAW_FILENAME,
        path=str(destination.parent),
    )
    zipped = destination.parent / f"{RAW_FILENAME}.zip"
    if zipped.is_file():
        with zipfile.ZipFile(zipped) as zf:
            zf.extractall(destination.parent)
        zipped.unlink()
    print(f"Downloaded data/raw/{RAW_FILENAME}")


if __name__ == "__main__":
    main()
