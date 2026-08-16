"""Read-only access to real chronological held-out demonstration transactions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.fraud_pipeline.input_contract import RawInputContract

from .errors import ApiError
from .stream_repository import SupabaseStreamRepository


class DemoTransactionRepository:
    dataset_name = "held_out_full"
    split = "chronological_test"
    labels_available = True

    def __init__(self, dataset_path: Path, contract: RawInputContract) -> None:
        self.dataset_path = dataset_path
        self.contract = contract

    def list(self, *, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        self._require_dataset()
        summary_columns = [
            column
            for column in (
                "TransactionID",
                "TransactionDT",
                "TransactionAmt",
                "ProductCD",
                "DeviceType",
                "DeviceInfo",
                "id_01",
            )
            if column in self.contract.columns
        ]
        frame = pd.read_parquet(self.dataset_path, columns=summary_columns).iloc[
            offset : offset + limit
        ]
        records: list[dict[str, Any]] = []
        identity_columns = [
            column
            for column in frame
            if column.startswith("id_") or column in {"DeviceType", "DeviceInfo"}
        ]
        for _, row in frame.iterrows():
            records.append(
                {
                    "transaction_id": int(row["TransactionID"]),
                    "transaction_dt": float(row["TransactionDT"]),
                    "transaction_amount": _safe_scalar(row.get("TransactionAmt")),
                    "product_code": _safe_scalar(row.get("ProductCD")),
                    "has_identity": bool(row[identity_columns].notna().any()),
                }
            )
        return records

    def get(self, transaction_id: int) -> dict[str, Any]:
        self._require_dataset()
        columns = list(self.contract.columns)
        try:
            frame = pd.read_parquet(
                self.dataset_path,
                columns=columns,
                filters=[("TransactionID", "==", transaction_id)],
            )
        except (TypeError, ValueError):
            frame = pd.read_parquet(self.dataset_path, columns=columns)
            frame = frame.loc[frame["TransactionID"] == transaction_id]
        if frame.empty:
            raise ApiError(
                404,
                "transaction_not_found",
                f"TransactionID {transaction_id} is not in the held-out demonstration dataset",
            )
        if len(frame) != 1:
            raise ApiError(500, "dataset_integrity_error", "Duplicate demonstration identifier")
        return {column: _safe_scalar(frame.iloc[0][column]) for column in columns}

    def _require_dataset(self) -> None:
        if not self.dataset_path.is_file():
            raise ApiError(
                503,
                "demo_dataset_unavailable",
                "The local held-out demonstration dataset is not available",
            )


class SupabaseDemoTransactionRepository:
    """Read label-free demonstration payloads through server-only PostgREST."""

    def __init__(
        self,
        repository: SupabaseStreamRepository,
        *,
        dataset_name: str = "kaggle_inference_sample",
    ) -> None:
        self.repository = repository
        self.dataset_name = dataset_name
        self.split = "kaggle_inference"
        self.labels_available = False
        self._dataset_id: str | None = None

    async def list(self, *, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        dataset_id = await self._demo_dataset_id()
        rows = await self.repository.client.request(
            "GET",
            "stream_transactions",
            params={
                "select": "transaction_id,transaction_dt,transaction_payload",
                "dataset_id": f"eq.{dataset_id}",
                "order": "sequence_number.asc",
                "offset": str(offset),
                "limit": str(limit),
            },
        )
        output = []
        for row in rows:
            payload = dict(row["transaction_payload"])
            payload.pop("isFraud", None)
            identity = any(
                value is not None
                for key, value in payload.items()
                if key.startswith("id_") or key in {"DeviceType", "DeviceInfo"}
            )
            output.append(
                {
                    "transaction_id": int(row["transaction_id"]),
                    "transaction_dt": float(row["transaction_dt"]),
                    "transaction_amount": payload.get("TransactionAmt"),
                    "product_code": payload.get("ProductCD"),
                    "has_identity": identity,
                }
            )
        return output

    async def get(self, transaction_id: int) -> dict[str, Any]:
        dataset_id = await self._demo_dataset_id()
        rows = await self.repository.client.request(
            "GET",
            "stream_transactions",
            params={
                "select": "transaction_payload",
                "dataset_id": f"eq.{dataset_id}",
                "transaction_id": f"eq.{transaction_id}",
                "limit": "1",
            },
        )
        if not rows:
            raise ApiError(
                404,
                "transaction_not_found",
                f"TransactionID {transaction_id} is not in the demonstration dataset",
            )
        payload = dict(rows[0]["transaction_payload"])
        payload.pop("isFraud", None)
        return payload

    async def _demo_dataset_id(self) -> str:
        if self._dataset_id is not None:
            return self._dataset_id
        rows = await self.repository.client.request(
            "GET",
            "stream_datasets",
            params={
                "select": "id",
                "name": f"eq.{self.dataset_name}",
                "status": "eq.ready",
                "limit": "1",
            },
        )
        if not rows:
            raise ApiError(
                503,
                "demo_dataset_unavailable",
                f"The Supabase dataset {self.dataset_name} is not ready",
            )
        self._dataset_id = str(rows[0]["id"])
        return self._dataset_id


def _safe_scalar(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value
