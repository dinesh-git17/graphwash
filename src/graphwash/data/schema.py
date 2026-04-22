r"""IT-AML HI-Medium raw schema (captured 2026-04-22).

Source
------
- Kaggle dataset: ``ealtman2019/ibm-transactions-for-anti-money-laundering-aml``
  (accessed 2026-04-22).
- Paper: Altman et al., "Realistic Synthetic Financial Transactions for
  Anti-Money Laundering Models," NeurIPS 2023 (arXiv:2306.16424).
- Reference script: IBM/Multi-GNN ``format_kaggle_files.py`` (Apache-2.0),
  which names every raw column by read-by-key, making it the authoritative
  diff target for column semantics.

Reproduction recipe
-------------------
Ensure ``~/.kaggle/kaggle.json`` is present with 0600 permissions, then::

    kaggle datasets download \
        -d <DATASET_SLUG> \
        -f <RAW_FILENAME> \
        -p data/raw/ \
        --unzip

where ``DATASET_SLUG`` and ``RAW_FILENAME`` are the module-level
``Final`` constants defined at the bottom of this module.

Capture with pandas::

    import pandas as pd
    df = pd.read_csv("data/raw/HI-Medium_Trans.csv", nrows=1000)
    labels = pd.read_csv(
        "data/raw/HI-Medium_Trans.csv",
        usecols=["Is Laundering"],
        dtype={"Is Laundering": "int8"},
    )

Schema as captured
------------------
Raw header row, literal bytes (11 columns; note the duplicate ``Account``
at positions 2 and 4)::

    Timestamp,From Bank,Account,To Bank,Account,Amount Received,
    Receiving Currency,Amount Paid,Payment Currency,Payment Format,
    Is Laundering

Pandas resolves the duplicate ``Account`` header on read by suffixing the
second occurrence to ``Account.1``. Downstream code imports
``PANDAS_LOADED_COLUMNS`` (the post-resolution names); ``HI_MEDIUM_RAW_COLUMNS``
documents the source-of-truth bytes.

Counts table
------------
================================  ================  ====================
Statistic                         Paper Table 4     Captured 2026-04-22
================================  ================  ====================
Transactions                      32,000,000        31,898,238
Laundering transactions           35,000            35,230
Laundering rate (1 per N)         905               905
Illicit fraction                  0.00110           0.00110
Bank accounts (not measured)      2,077,000         n/a
Days spanned (not measured)       16                n/a
================================  ================  ====================

Captured values are within a +/-10% relative tolerance of paper Table 4,
satisfying the amended S-02 success criterion (PRD §11a). Laundering rate
matches exactly at 1 per 905.

Divergences from prior PRD assumptions
--------------------------------------
Before this capture, PRD §1 and REQ-002 asserted ``~2%`` illicit
transactions. The paper and the captured labels both show ``~0.11%``
(roughly 1 per 905 in HI-Medium). The PRD amendments landed in the same
PR correct §1, REQ-001, REQ-002, §14 Tradeoff 3, and §11a S-02. ADR-0007
locks HI-Medium over LI-Medium for baseline comparability and
F1-reachability. Captured on 2026-04-22 against the spike's kill-signal
clause (§11a S-02: "if structural divergence, REQ-001 scope is amended
and task list updated before T-023").

Timestamp format
----------------
``%Y/%m/%d %H:%M`` (observed in the first row; consistent with IBM's
``format_kaggle_files.py`` strptime usage).
"""

from collections.abc import Mapping
from typing import Final

HI_MEDIUM_RAW_COLUMNS: Final[tuple[str, ...]] = (
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account",
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
)

PANDAS_LOADED_COLUMNS: Final[tuple[str, ...]] = (
    "Timestamp",
    "From Bank",
    "Account",
    "To Bank",
    "Account.1",
    "Amount Received",
    "Receiving Currency",
    "Amount Paid",
    "Payment Currency",
    "Payment Format",
    "Is Laundering",
)

RAW_COLUMN_DTYPES: Final[Mapping[str, str]] = {
    "Timestamp": "string",
    "From Bank": "int64",
    "Account": "string",
    "To Bank": "int64",
    "Account.1": "string",
    "Amount Received": "float64",
    "Receiving Currency": "string",
    "Amount Paid": "float64",
    "Payment Currency": "string",
    "Payment Format": "string",
    "Is Laundering": "int8",
}

RENAME_MAP: Final[Mapping[str, str]] = {
    "Timestamp": "timestamp",
    "From Bank": "from_bank",
    "Account": "from_account",
    "To Bank": "to_bank",
    "Account.1": "to_account",
    "Amount Received": "amount_received",
    "Receiving Currency": "receiving_currency",
    "Amount Paid": "amount_paid",
    "Payment Currency": "payment_currency",
    "Payment Format": "payment_format",
    "Is Laundering": "is_laundering",
}

TIMESTAMP_FORMAT: Final[str] = "%Y/%m/%d %H:%M"

TOTAL_TRANSACTIONS: Final[int] = 31_898_238
LAUNDERING_TRANSACTIONS: Final[int] = 35_230
LAUNDERING_RATE_1_PER_N: Final[int] = 905
ILLICIT_FRACTION: Final[float] = 0.0011044497191349566

PAPER_HI_MEDIUM_STATS: Final[Mapping[str, int]] = {
    "days_spanned": 16,
    "bank_accounts": 2_077_000,
    "transactions": 32_000_000,
    "laundering_transactions": 35_000,
    "laundering_rate_1_per_n": 905,
}

DATASET_SLUG: Final[str] = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
RAW_FILENAME: Final[str] = "HI-Medium_Trans.csv"
