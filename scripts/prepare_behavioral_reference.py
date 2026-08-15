#!/usr/bin/env python3
"""Build a leakage-safe V2 reference from pre-held-out history only."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fraud_pipeline.behavioral import build_behavioral_reference
from src.fraud_pipeline.input_contract import RawInputContract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--train",
        type=Path,
        default=PROJECT_ROOT / "data/processed/v2/train.parquet",
    )
    parser.add_argument(
        "--validation",
        type=Path,
        default=PROJECT_ROOT / "data/processed/v2/validation.parquet",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=PROJECT_ROOT / "config/raw_input_schema.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data/processed/v2/behavioral_reference.joblib",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = RawInputContract.load(args.schema)
    columns = list(contract.columns)
    history = pd.concat(
        [
            pd.read_parquet(args.train, columns=columns),
            pd.read_parquet(args.validation, columns=columns),
        ],
        ignore_index=True,
    )
    reference = build_behavioral_reference(history)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="behavioral-reference-",
        suffix=".joblib",
        dir=args.output.parent,
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(reference, temporary_path, compress=3)
        temporary_path.replace(args.output)
    finally:
        temporary_path.unlink(missing_ok=True)
    metadata = reference["contract"]["metadata"]
    print(
        json.dumps(
            {
                "status": "prepared",
                "history_rows": metadata["history_row_count"],
                "history_end_transaction_dt": metadata["history_end_transaction_dt"],
                "history_end_transaction_id": metadata["history_end_transaction_id"],
                "output": str(args.output.relative_to(PROJECT_ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
