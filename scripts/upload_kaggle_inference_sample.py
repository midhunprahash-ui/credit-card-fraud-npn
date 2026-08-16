#!/usr/bin/env python3
"""Prepare and upload 100 unlabelled Kaggle test transactions to Supabase."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.settings import Settings
from api.stream_repository import SupabaseRestClient

DEFAULT_TRANSACTION_SOURCE = (
    PROJECT_ROOT / "data/raw/ieee-fraud-detection/test_transaction.csv"
)
DEFAULT_IDENTITY_SOURCE = (
    PROJECT_ROOT / "data/raw/ieee-fraud-detection/test_identity.csv"
)
RAW_SCHEMA = PROJECT_ROOT / "config/raw_input_schema.json"
DATASET_NAME = "kaggle_inference_sample"
SAMPLE_ROWS = 100


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transaction-source", type=Path, default=DEFAULT_TRANSACTION_SOURCE
    )
    parser.add_argument("--identity-source", type=Path, default=DEFAULT_IDENTITY_SOURCE)
    parser.add_argument("--row-limit", type=int, default=SAMPLE_ROWS)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--sql-output",
        type=Path,
        help="Write an idempotent SQL upload file instead of contacting Supabase.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize locally without contacting Supabase.",
    )
    return parser.parse_args()


def raw_columns() -> list[str]:
    return list(json.loads(RAW_SCHEMA.read_text())["required_columns"])


def prepare_rows(
    transaction_source: Path,
    identity_source: Path,
    *,
    row_limit: int = SAMPLE_ROWS,
) -> list[dict[str, Any]]:
    if not 1 <= row_limit <= SAMPLE_ROWS:
        raise ValueError(f"Row limit must be between 1 and {SAMPLE_ROWS}")
    if not transaction_source.is_file() or not identity_source.is_file():
        raise FileNotFoundError("Kaggle test transaction and identity CSV files are required")

    transactions = pd.read_csv(transaction_source, nrows=row_limit)
    if len(transactions) != row_limit:
        raise ValueError(f"Expected {row_limit} Kaggle transactions; found {len(transactions)}")
    if transactions["TransactionID"].duplicated().any():
        raise ValueError("Kaggle transaction sample contains duplicate TransactionIDs")

    transaction_ids = set(transactions["TransactionID"].astype(int))
    identity_matches: list[pd.DataFrame] = []
    for chunk in pd.read_csv(identity_source, chunksize=50_000):
        matched = chunk.loc[chunk["TransactionID"].isin(transaction_ids)]
        if not matched.empty:
            identity_matches.append(matched)
    identities = (
        pd.concat(identity_matches, ignore_index=True)
        if identity_matches
        else pd.DataFrame(columns=["TransactionID"])
    )
    identities = identities.rename(
        columns={column: column.replace("id-", "id_") for column in identities}
    )
    if identities["TransactionID"].duplicated().any():
        raise ValueError("Kaggle identity sample contains duplicate TransactionIDs")

    joined = transactions.merge(
        identities,
        on="TransactionID",
        how="left",
        validate="one_to_one",
        sort=False,
    )
    columns = raw_columns()
    missing = sorted(set(columns) - set(joined.columns))
    unexpected = sorted(set(joined.columns) - set(columns))
    if missing or unexpected:
        raise ValueError(
            f"Kaggle joined schema mismatch; missing={missing}, unexpected={unexpected}"
        )
    joined = joined.loc[:, columns].sort_values(
        ["TransactionDT", "TransactionID"], kind="stable"
    )

    rows: list[dict[str, Any]] = []
    for sequence_number, record in enumerate(joined.to_dict(orient="records")):
        transaction_id = int(record["TransactionID"])
        transaction_dt = float(record["TransactionDT"])
        payload = {
            column: _json_value(value)
            for column, value in record.items()
            if not _is_missing(value)
        }
        payload.pop("isFraud", None)
        rows.append(
            {
                "sequence_number": sequence_number,
                "transaction_id": transaction_id,
                "transaction_dt": transaction_dt,
                "transaction_payload": payload,
            }
        )
    return rows


async def upload(
    client: SupabaseRestClient,
    rows: list[dict[str, Any]],
    *,
    batch_size: int,
) -> None:
    if not 1 <= batch_size <= 100:
        raise ValueError("Batch size must be between 1 and 100")
    datasets = await client.request(
        "POST",
        "stream_datasets",
        params={"on_conflict": "name"},
        body={
            "name": DATASET_NAME,
            "description": (
                "First 100 chronological transactions from the official unlabelled "
                "IEEE-CIS Kaggle test dataset, left-joined with identity data."
            ),
            "split": "kaggle_inference",
            "schema_version": "raw-v1",
            "supported_versions": ["V1", "V2"],
            "row_count": len(rows),
            "fraud_count": None,
            "fraud_rate": None,
            "labels_available": False,
            "status": "preparing",
        },
        prefer="resolution=merge-duplicates,return=representation",
    )
    if len(datasets) != 1:
        raise RuntimeError("Supabase did not return the prepared Kaggle dataset")
    dataset_id = str(datasets[0]["id"])

    for start in range(0, len(rows), batch_size):
        batch = [dict(row, dataset_id=dataset_id) for row in rows[start : start + batch_size]]
        stored = await client.request(
            "POST",
            "stream_transactions",
            params={"on_conflict": "dataset_id,transaction_id"},
            body=batch,
            prefer="resolution=merge-duplicates,return=representation",
        )
        if len(stored) != len(batch):
            raise RuntimeError("Supabase did not return every Kaggle transaction")
        print(f"{DATASET_NAME}: uploaded {start + len(batch):,}/{len(rows):,}")

    await client.request(
        "PATCH",
        "stream_datasets",
        params={"id": f"eq.{dataset_id}"},
        body={"status": "ready"},
        prefer="return=minimal",
    )


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    distinct_fields = {
        key for row in rows for key in row["transaction_payload"].keys()
    }


def build_upload_sql(rows: list[dict[str, Any]]) -> str:
    description = (
        "First 100 chronological transactions from the official unlabelled "
        "IEEE-CIS Kaggle test dataset, left-joined with identity data."
    )
    values = []
    for row in rows:
        payload = json.dumps(
            row["transaction_payload"],
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).replace("'", "''")
        values.append(
            "((select id from public.stream_datasets where name = "
            f"'{DATASET_NAME}'), {row['sequence_number']}, "
            f"{row['transaction_id']}, {row['transaction_dt']}, "
            f"'{payload}'::jsonb)"
        )
    return "\n".join(
        [
            "begin;",
            "",
            "insert into public.stream_datasets (",
            "    name, description, split, schema_version, supported_versions,",
            "    row_count, fraud_count, fraud_rate, labels_available, status",
            ") values (",
            f"    '{DATASET_NAME}', '{description}', 'kaggle_inference', 'raw-v1',",
            f"    array['V1', 'V2']::text[], {len(rows)}, null, null, false, 'preparing'",
            ") on conflict (name) do update set",
            "    description = excluded.description,",
            "    split = excluded.split,",
            "    schema_version = excluded.schema_version,",
            "    supported_versions = excluded.supported_versions,",
            "    row_count = excluded.row_count,",
            "    fraud_count = excluded.fraud_count,",
            "    fraud_rate = excluded.fraud_rate,",
            "    labels_available = excluded.labels_available,",
            "    status = excluded.status;",
            "",
            "insert into public.stream_transactions (",
            "    dataset_id, sequence_number, transaction_id, transaction_dt,",
            "    transaction_payload",
            ") values",
            ",\n".join(values),
            "on conflict (dataset_id, transaction_id) do update set",
            "    sequence_number = excluded.sequence_number,",
            "    transaction_dt = excluded.transaction_dt,",
            "    transaction_payload = excluded.transaction_payload;",
            "",
            "update public.stream_datasets",
            "set status = 'ready'",
            f"where name = '{DATASET_NAME}';",
            "",
            "commit;",
            "",
        ]
    )
    return {
        "name": DATASET_NAME,
        "row_count": len(rows),
        "labels_available": False,
        "distinct_payload_fields": len(distinct_fields),
        "first_transaction_id": rows[0]["transaction_id"],
        "last_transaction_id": rows[-1]["transaction_id"],
    }


def _is_missing(value: Any) -> bool:
    missing = pd.isna(value)
    return bool(missing) if isinstance(missing, (bool, np.bool_)) else False


def _json_value(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


async def run(args: argparse.Namespace) -> None:
    rows = prepare_rows(
        args.transaction_source,
        args.identity_source,
        row_limit=args.row_limit,
    )
    print(json.dumps(summary(rows), indent=2))
    if args.dry_run:
        return
    if args.sql_output is not None:
        args.sql_output.write_text(build_upload_sql(rows))
        return
    client = SupabaseRestClient(Settings())
    try:
        await upload(client, rows, batch_size=args.batch_size)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
