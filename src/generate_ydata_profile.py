"""Generate a ydata-profiling HTML report for the left-joined training set.

The script intentionally reads only the labelled training transaction and
identity tables. It never reads the Kaggle competition test set.
"""

from __future__ import annotations

import argparse
import gc
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from ydata_profiling import ProfileReport


DEFAULT_DATA_DIR = Path("data/raw/ieee-fraud-detection")
DEFAULT_OUTPUT = Path("reports/generated/ieee_cis_train_left_join_profile.html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an interactive HTML EDA report from train_transaction "
            "LEFT JOIN train_identity on TransactionID."
        )
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=0,
        help=(
            "Number of joined rows to profile. Use 0 for every training row. "
            "Sampling is deterministic and stratified by isFraud."
        ),
    )
    parser.add_argument(
        "--standard",
        action="store_true",
        help=(
            "Enable the more expensive standard ydata analysis. Recommended "
            "only together with --sample-rows 50000 (or similar)."
        ),
    )
    return parser.parse_args()


def memory_mb(frame: pd.DataFrame) -> float:
    return frame.memory_usage(index=True, deep=True).sum() / 1024**2


def reduce_memory(frame: pd.DataFrame) -> pd.DataFrame:
    """Downcast columns without changing their analytical meaning."""
    for column in frame.select_dtypes(include=["float64"]).columns:
        frame[column] = pd.to_numeric(frame[column], downcast="float")

    for column in frame.select_dtypes(include=["int64"]).columns:
        frame[column] = pd.to_numeric(frame[column], downcast="integer")

    # Category dtype drastically reduces repeated-string memory. YData still
    # treats these fields as categorical variables in the generated report.
    for column in frame.select_dtypes(include=["object"]).columns:
        frame[column] = frame[column].astype("category")

    return frame


def stratified_sample(frame: pd.DataFrame, rows: int) -> pd.DataFrame:
    if rows <= 0 or rows >= len(frame):
        return frame

    fractions = frame["isFraud"].value_counts(normalize=True)
    pieces: list[pd.DataFrame] = []
    remaining = rows
    labels = list(fractions.index)

    for index, label in enumerate(labels):
        group = frame.loc[frame["isFraud"] == label]
        if index == len(labels) - 1:
            count = min(remaining, len(group))
        else:
            count = min(int(round(rows * fractions[label])), len(group))
            remaining -= count
        pieces.append(group.sample(n=count, random_state=42))

    return (
        pd.concat(pieces, axis=0)
        .sort_values("TransactionDT", kind="stable")
        .reset_index(drop=True)
    )


def load_left_joined_training_data(data_dir: Path) -> pd.DataFrame:
    transaction_path = data_dir / "train_transaction.csv"
    identity_path = data_dir / "train_identity.csv"

    missing = [str(path) for path in (transaction_path, identity_path) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required training file(s): " + ", ".join(missing))

    print(f"Reading {transaction_path} ...", flush=True)
    transactions = reduce_memory(pd.read_csv(transaction_path))
    print(
        f"Transactions: {transactions.shape}, {memory_mb(transactions):,.1f} MB",
        flush=True,
    )

    print(f"Reading {identity_path} ...", flush=True)
    identities = reduce_memory(pd.read_csv(identity_path))
    print(f"Identities: {identities.shape}, {memory_mb(identities):,.1f} MB", flush=True)

    if not transactions["TransactionID"].is_unique:
        raise ValueError("TransactionID must be unique in train_transaction.csv")
    if not identities["TransactionID"].is_unique:
        raise ValueError("TransactionID must be unique in train_identity.csv")

    identity_ids = set(identities["TransactionID"].to_numpy())
    transactions["has_identity"] = (
        transactions["TransactionID"].isin(identity_ids).astype(np.int8)
    )
    identity_ids.clear()

    print("LEFT JOIN on TransactionID ...", flush=True)
    joined = transactions.merge(
        identities,
        on="TransactionID",
        how="left",
        validate="one_to_one",
        sort=False,
        copy=False,
    )
    del transactions, identities
    gc.collect()

    if len(joined) != 590_540:
        raise ValueError(f"Expected 590,540 joined rows; received {len(joined):,}")
    if joined["isFraud"].isna().any():
        raise ValueError("isFraud contains missing values after the join")

    print(f"Joined training data: {joined.shape}, {memory_mb(joined):,.1f} MB", flush=True)
    print(f"Fraud rate: {joined['isFraud'].mean():.4%}", flush=True)
    print(f"Identity coverage: {joined['has_identity'].mean():.4%}", flush=True)
    return joined


def main() -> None:
    args = parse_args()
    started = perf_counter()
    joined = load_left_joined_training_data(args.data_dir)
    profiled = stratified_sample(joined, args.sample_rows)

    if profiled is not joined:
        del joined
        gc.collect()
        print(
            f"Profiling a deterministic stratified sample: {profiled.shape}",
            flush=True,
        )
    else:
        print("Profiling every joined training row.", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "standard" if args.standard else "memory-safe minimal"
    report = ProfileReport(
        profiled,
        title="IEEE-CIS Fraud Detection — Left-Joined Training Data",
        explorative=args.standard,
        minimal=not args.standard,
        sort=None,
        progress_bar=True,
        dataset={
            "description": (
                "train_transaction LEFT JOIN train_identity on TransactionID. "
                "The isFraud field is the supervised training target."
            ),
            "copyright_holder": "IEEE-CIS / Vesta dataset; analysis for NPN hackathon",
        },
    )
    report.to_file(args.output)

    elapsed_minutes = (perf_counter() - started) / 60
    print(f"Created: {args.output.resolve()}", flush=True)
    print(f"Mode: {mode}; elapsed: {elapsed_minutes:.1f} minutes", flush=True)


if __name__ == "__main__":
    main()
