#!/usr/bin/env python3
"""Validate and upload chronological held-out replay datasets to Supabase."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.settings import Settings
from api.stream_repository import SupabaseRestClient

DEFAULT_SOURCE = PROJECT_ROOT / "data/processed/v2/test.parquet"
RAW_SCHEMA = PROJECT_ROOT / "config/raw_input_schema.json"
EXPECTED_HELD_OUT_ROWS = 88_581


@dataclass(frozen=True)
class DatasetPlan:
    name: str
    split: str
    row_limit: int
    description: str


PLANS = {
    "held_out_full": DatasetPlan(
        name="held_out_full",
        split="chronological_test",
        row_limit=EXPECTED_HELD_OUT_ROWS,
        description="All labelled chronological held-out IEEE-CIS transactions.",
    ),
    "demo_chronological": DatasetPlan(
        name="demo_chronological",
        split="demo_chronological",
        row_limit=600,
        description="First 600 real transactions from the chronological held-out split.",
    ),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        choices=[*PLANS, "all"],
        help="Dataset definition to validate and upload.",
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize locally without contacting Supabase.",
    )
    return parser.parse_args()


def raw_columns() -> list[str]:
    document = json.loads(RAW_SCHEMA.read_text())
    return list(document["required_columns"])


def iter_source_rows(
    source: Path, *, row_limit: int, batch_size: int
) -> Iterator[list[dict[str, Any]]]:
    if not source.is_file():
        raise FileNotFoundError(f"Held-out source not found: {source}")
    if not 1 <= batch_size <= 100:
        raise ValueError("Batch size must be between 1 and 100")
    parquet = pq.ParquetFile(source)
    if parquet.metadata.num_rows != EXPECTED_HELD_OUT_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_HELD_OUT_ROWS:,} held-out rows; found "
            f"{parquet.metadata.num_rows:,}"
        )
    columns = [*raw_columns(), "isFraud"]
    missing = sorted(set(columns) - set(parquet.schema_arrow.names))
    if missing:
        raise ValueError(f"Held-out source is missing columns: {missing}")

    emitted = 0
    previous_key: tuple[float, int] | None = None
    for record_batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        output: list[dict[str, Any]] = []
        for row in record_batch.to_pylist():
            if emitted >= row_limit:
                break
            transaction_id = int(row["TransactionID"])
            transaction_dt = float(row["TransactionDT"])
            label = row.pop("isFraud")
            if label not in (0, 1, False, True):
                raise ValueError(f"Invalid isFraud label for TransactionID {transaction_id}")
            key = (transaction_dt, transaction_id)
            if previous_key is not None and key < previous_key:
                raise ValueError("Held-out rows are not in chronological FIFO order")
            previous_key = key
            payload = {
                column: _json_value(value)
                for column, value in row.items()
                if value is not None
            }
            payload.pop("isFraud", None)
            output.append(
                {
                    "sequence_number": emitted,
                    "transaction_id": transaction_id,
                    "transaction_dt": transaction_dt,
                    "transaction_payload": payload,
                    "actual_label": bool(label),
                }
            )
            emitted += 1
        if output:
            yield output
        if emitted >= row_limit:
            break
    if emitted != row_limit:
        raise ValueError(f"Expected {row_limit:,} rows for upload; prepared {emitted:,}")


def summarize(source: Path, plan: DatasetPlan, batch_size: int) -> dict[str, Any]:
    count = fraud_count = 0
    first_id = last_id = None
    for batch in iter_source_rows(source, row_limit=plan.row_limit, batch_size=batch_size):
        if first_id is None:
            first_id = batch[0]["transaction_id"]
        last_id = batch[-1]["transaction_id"]
        count += len(batch)
        fraud_count += sum(row["actual_label"] for row in batch)
    return {
        "name": plan.name,
        "row_count": count,
        "fraud_count": fraud_count,
        "fraud_rate": fraud_count / count,
        "first_transaction_id": first_id,
        "last_transaction_id": last_id,
    }


async def upload(
    client: SupabaseRestClient,
    source: Path,
    plan: DatasetPlan,
    summary: dict[str, Any],
    batch_size: int,
) -> None:
    datasets = await client.request(
        "POST",
        "stream_datasets",
        params={"on_conflict": "name"},
        body={
            "name": plan.name,
            "description": plan.description,
            "split": plan.split,
            "schema_version": "raw-v1",
            "supported_versions": ["V1", "V2"],
            "row_count": summary["row_count"],
            "fraud_count": summary["fraud_count"],
            "fraud_rate": summary["fraud_rate"],
            "status": "preparing",
        },
        prefer="resolution=merge-duplicates,return=representation",
    )
    if len(datasets) != 1:
        raise RuntimeError("Supabase did not return the prepared dataset")
    dataset_id = str(datasets[0]["id"])

    uploaded = 0
    for batch in iter_source_rows(source, row_limit=plan.row_limit, batch_size=batch_size):
        transaction_rows = [
            {
                "dataset_id": dataset_id,
                "sequence_number": row["sequence_number"],
                "transaction_id": row["transaction_id"],
                "transaction_dt": row["transaction_dt"],
                "transaction_payload": row["transaction_payload"],
            }
            for row in batch
        ]
        stored = await client.request(
            "POST",
            "stream_transactions",
            params={"on_conflict": "dataset_id,transaction_id"},
            body=transaction_rows,
            prefer="resolution=merge-duplicates,return=representation",
        )
        stored_by_transaction = {
            int(row["transaction_id"]): int(row["id"]) for row in stored
        }
        if len(stored_by_transaction) != len(batch):
            raise RuntimeError("Supabase did not return every uploaded transaction")
        labels = [
            {
                "stream_transaction_id": stored_by_transaction[row["transaction_id"]],
                "is_fraud": row["actual_label"],
            }
            for row in batch
        ]
        await client.request(
            "POST",
            "stream_ground_truth",
            params={"on_conflict": "stream_transaction_id"},
            body=labels,
            prefer="resolution=merge-duplicates,return=minimal",
        )
        uploaded += len(batch)
        if uploaded % 1_000 == 0 or uploaded == plan.row_limit:
            print(f"{plan.name}: uploaded {uploaded:,}/{plan.row_limit:,}")

    await client.request(
        "PATCH",
        "stream_datasets",
        params={"id": f"eq.{dataset_id}"},
        body={"status": "ready"},
        prefer="return=minimal",
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


async def _run(args: argparse.Namespace) -> None:
    plans = list(PLANS.values()) if args.dataset == "all" else [PLANS[args.dataset]]
    summaries = [(plan, summarize(args.source, plan, args.batch_size)) for plan in plans]
    for _, result in summaries:
        print(json.dumps(result, indent=2))
    if args.dry_run:
        return
    client = SupabaseRestClient(Settings())
    try:
        for plan, result in summaries:
            await upload(client, args.source, plan, result, args.batch_size)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
