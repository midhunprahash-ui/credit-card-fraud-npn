"""Server-only Supabase repository for streaming datasets and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from .settings import Settings


class SupabaseRepositoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredStreamTransaction:
    id: int
    dataset_id: str
    sequence_number: int
    transaction_id: int
    transaction_dt: float
    transaction_payload: dict[str, Any]
    actual_label: bool


@dataclass(frozen=True)
class PersistedModelPrediction:
    model_identifier: str
    risk_score: float
    threshold: float
    decision: bool
    latency_ms: float
    model_run_id: str


@dataclass(frozen=True)
class CompletedStreamRecord:
    stream_transaction_id: int
    sequence_number: int
    transaction_id: int
    arrival_time: datetime
    queue_position: int
    processing_started_at: datetime
    completed_at: datetime
    status: str
    actual_label: bool
    suspicious_amount: float | None
    predictions: tuple[PersistedModelPrediction, ...]
    error_code: str | None = None


class SupabaseRestClient:
    """Small pooled PostgREST client authenticated only with a server secret."""

    def __init__(self, settings: Settings) -> None:
        if not settings.supabase_configured:
            raise SupabaseRepositoryError("Supabase server credentials are not configured")
        assert settings.supabase_url is not None
        assert settings.supabase_secret_key is not None
        self.base_url = f"{settings.supabase_url.rstrip('/')}/rest/v1"
        self.headers = {
            "apikey": settings.supabase_secret_key.get_secret_value(),
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        body: Any | None = None,
        prefer: str | None = None,
    ) -> list[dict[str, Any]]:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = await self._client.request(
                method,
                f"{self.base_url}/{table}",
                headers=headers,
                params=params,
                json=body,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise SupabaseRepositoryError(
                f"Supabase {table} request failed with {type(error).__name__}"
            ) from error
        if not response.content:
            return []
        payload = response.json()
        if not isinstance(payload, list):
            raise SupabaseRepositoryError(f"Unexpected Supabase response for {table}")
        return payload


class SupabaseStreamRepository:
    PREFETCH_SIZE = 100

    def __init__(self, client: SupabaseRestClient) -> None:
        self.client = client

    async def list_datasets(self) -> list[dict[str, Any]]:
        return await self.client.request(
            "GET",
            "stream_datasets",
            params={
                "select": "id,name,split,schema_version,row_count,fraud_count,fraud_rate,description,status",
                "status": "eq.ready",
                "order": "name.asc",
            },
        )

    async def fetch_transaction_batch(
        self,
        dataset_id: str,
        *,
        after_sequence: int,
        limit: int = PREFETCH_SIZE,
    ) -> list[StoredStreamTransaction]:
        if not 1 <= limit <= self.PREFETCH_SIZE:
            raise ValueError(f"Prefetch limit must be between 1 and {self.PREFETCH_SIZE}")
        rows = await self.client.request(
            "GET",
            "stream_transactions",
            params={
                "select": "id,dataset_id,sequence_number,transaction_id,transaction_dt,transaction_payload",
                "dataset_id": f"eq.{dataset_id}",
                "sequence_number": f"gt.{after_sequence}",
                "order": "sequence_number.asc",
                "limit": str(limit),
            },
        )
        if not rows:
            return []
        ids = [int(row["id"]) for row in rows]
        labels = await self.client.request(
            "GET",
            "stream_ground_truth",
            params={
                "select": "stream_transaction_id,is_fraud",
                "stream_transaction_id": f"in.({','.join(str(value) for value in ids)})",
            },
        )
        label_by_id = {
            int(row["stream_transaction_id"]): bool(row["is_fraud"])
            for row in labels
        }
        if set(label_by_id) != set(ids):
            raise SupabaseRepositoryError("A prefetched transaction is missing ground truth")
        transactions = [
            StoredStreamTransaction(
                id=int(row["id"]),
                dataset_id=str(row["dataset_id"]),
                sequence_number=int(row["sequence_number"]),
                transaction_id=int(row["transaction_id"]),
                transaction_dt=float(row["transaction_dt"]),
                transaction_payload=dict(row["transaction_payload"]),
                actual_label=label_by_id[int(row["id"])],
            )
            for row in rows
        ]
        sequences = [item.sequence_number for item in transactions]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise SupabaseRepositoryError("Supabase returned a non-FIFO transaction batch")
        return transactions

    async def create_run(
        self,
        *,
        dataset_id: str,
        selected_versions: list[str],
        selected_models: list[str],
        transactions_per_second: int,
    ) -> str:
        rows = await self.client.request(
            "POST",
            "stream_runs",
            body={
                "dataset_id": dataset_id,
                "selected_versions": selected_versions,
                "selected_models": selected_models,
                "transactions_per_second": transactions_per_second,
                "status": "LOADING",
            },
            prefer="return=representation",
        )
        if len(rows) != 1:
            raise SupabaseRepositoryError("Supabase did not return the created stream run")
        return str(rows[0]["id"])

    async def update_run(self, run_id: str, values: dict[str, Any]) -> None:
        await self.client.request(
            "PATCH",
            "stream_runs",
            params={"id": f"eq.{run_id}"},
            body=values,
            prefer="return=minimal",
        )

    async def persist_completed_batch(
        self,
        run_id: str,
        records: list[CompletedStreamRecord],
        run_values: dict[str, Any],
    ) -> None:
        if not records:
            await self.update_run(run_id, run_values)
            return
        event_rows = [
            {
                "stream_run_id": run_id,
                "stream_transaction_id": record.stream_transaction_id,
                "sequence_number": record.sequence_number,
                "transaction_id": record.transaction_id,
                "arrival_time": record.arrival_time.isoformat(),
                "queue_position": record.queue_position,
                "processing_started_at": record.processing_started_at.isoformat(),
                "completed_at": record.completed_at.isoformat(),
                "status": record.status,
                "error_code": record.error_code,
            }
            for record in records
        ]
        inserted_events = await self.client.request(
            "POST",
            "stream_transaction_events",
            params={"on_conflict": "stream_run_id,sequence_number"},
            body=event_rows,
            prefer="resolution=merge-duplicates,return=representation",
        )
        event_id_by_sequence = {
            int(row["sequence_number"]): int(row["id"]) for row in inserted_events
        }
        if len(event_id_by_sequence) != len(records):
            raise SupabaseRepositoryError("Not all FIFO events were persisted")

        prediction_rows: list[dict[str, Any]] = []
        alert_rows: list[dict[str, Any]] = []
        for record in records:
            event_id = event_id_by_sequence[record.sequence_number]
            fraud_votes = sum(prediction.decision for prediction in record.predictions)
            for prediction in record.predictions:
                prediction_rows.append(
                    {
                        "stream_run_id": run_id,
                        "stream_transaction_event_id": event_id,
                        "sequence_number": record.sequence_number,
                        "transaction_id": record.transaction_id,
                        "model_identifier": prediction.model_identifier,
                        "risk_score": prediction.risk_score,
                        "threshold": prediction.threshold,
                        "decision": prediction.decision,
                        "actual_label": record.actual_label,
                        "latency_ms": prediction.latency_ms,
                        "model_run_id": prediction.model_run_id,
                    }
                )
            if fraud_votes:
                alert_rows.append(
                    {
                        "stream_run_id": run_id,
                        "stream_transaction_event_id": event_id,
                        "transaction_id": record.transaction_id,
                        "highest_risk_score": max(
                            prediction.risk_score for prediction in record.predictions
                        ),
                        "model_agreement": fraud_votes,
                        "selected_model_count": len(record.predictions),
                        "suspicious_amount": record.suspicious_amount,
                    }
                )
        if prediction_rows:
            await self.client.request(
                "POST",
                "prediction_events",
                params={
                    "on_conflict": "stream_run_id,sequence_number,model_identifier"
                },
                body=prediction_rows,
                prefer="resolution=merge-duplicates,return=minimal",
            )
        if alert_rows:
            await self.client.request(
                "POST",
                "fraud_alerts",
                params={"on_conflict": "stream_run_id,transaction_id"},
                body=alert_rows,
                prefer="resolution=merge-duplicates,return=minimal",
            )
        await self.update_run(run_id, run_values)
