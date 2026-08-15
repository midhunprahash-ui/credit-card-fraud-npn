"""Strict FIFO held-out replay with SSE publication and batched persistence."""

from __future__ import annotations

import asyncio
import math
import time
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, AsyncIterator, Protocol

import pandas as pd

from src.fraud_pipeline.behavioral import update_behavioral_reference
from src.fraud_pipeline.input_contract import RawInputContract
from src.fraud_pipeline.model_manager import ModelManager
from src.fraud_pipeline.registry import ModelRegistry

from .errors import ApiError
from .services import BehavioralReferenceProvider, PredictionService
from .stream_repository import (
    CompletedStreamRecord,
    PersistedModelPrediction,
    StoredStreamTransaction,
)


class StreamRepository(Protocol):
    async def list_datasets(self) -> list[dict[str, Any]]: ...

    async def fetch_transaction_batch(
        self, dataset_id: str, *, after_sequence: int, limit: int = 100
    ) -> list[StoredStreamTransaction]: ...

    async def create_run(
        self,
        *,
        dataset_id: str,
        selected_versions: list[str],
        selected_models: list[str],
        transactions_per_second: int,
    ) -> str: ...

    async def update_run(self, run_id: str, values: dict[str, Any]) -> None: ...

    async def persist_completed_batch(
        self,
        run_id: str,
        records: list[CompletedStreamRecord],
        run_values: dict[str, Any],
    ) -> None: ...


@dataclass
class QueueEvent:
    stored: StoredStreamTransaction
    arrival_time: datetime
    queue_position: int


class SseBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        event = {"event": event_type, "data": data}
        for queue in tuple(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    yield {"event": "heartbeat", "data": {"timestamp": _now_iso()}}
        finally:
            self._subscribers.discard(queue)


class StreamController:
    PREFETCH_SIZE = 100
    PREFETCH_LOW_WATERMARK = 20
    PERSIST_BATCH_SIZE = 10
    PERSIST_INTERVAL_SECONDS = 2.0

    def __init__(
        self,
        repository: StreamRepository,
        registry: ModelRegistry,
        model_manager: ModelManager,
        prediction_service: PredictionService,
        reference_provider: BehavioralReferenceProvider,
        raw_contract: RawInputContract,
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.model_manager = model_manager
        self.prediction_service = prediction_service
        self.reference_provider = reference_provider
        self.raw_contract = raw_contract
        self.broker = SseBroker()
        self._lock = asyncio.Lock()
        self._run_gate = asyncio.Event()
        self._stop_requested = asyncio.Event()
        self._producer_done = asyncio.Event()
        self._queue: asyncio.Queue[QueueEvent] = asyncio.Queue()
        self._persistence_queue: asyncio.Queue[CompletedStreamRecord | None] = asyncio.Queue()
        self._coordinator: asyncio.Task[None] | None = None
        self._reset_state()

    def _reset_state(self) -> None:
        self.run_id: str | None = None
        self.dataset_id: str | None = None
        self.selected_models: list[str] = []
        self.selected_versions: list[str] = []
        self.transactions_per_second = 1
        self.status = "IDLE"
        self.received_count = 0
        self.processed_count = 0
        self.failed_count = 0
        self.fraud_count = 0
        self.suspicious_transaction_value = 0.0
        self.current_sequence = -1
        self.currently_processing: dict[str, Any] | None = None
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self._latencies_ms: deque[float] = deque(maxlen=10_000)
        self._unpersisted_count = 0
        self._behavioral_reference: dict[str, Any] | None = None

    async def list_datasets(self) -> list[dict[str, Any]]:
        return await self.repository.list_datasets()

    async def start(
        self,
        *,
        dataset_id: str,
        selected_models: list[str],
        transactions_per_second: int,
    ) -> dict[str, Any]:
        async with self._lock:
            if self.status in {"LOADING", "RUNNING", "PAUSED", "STOPPING"}:
                raise ApiError(409, "stream_already_active", "A stream run is already active")
            try:
                specs = [self.registry.get(identifier) for identifier in selected_models]
            except ValueError as error:
                raise ApiError(422, "invalid_model_selection", str(error)) from error
            if len(selected_models) != len(set(selected_models)) or not selected_models:
                raise ApiError(422, "invalid_model_selection", "Select unique models")
            if len(selected_models) > self.model_manager.max_loaded_models:
                raise ApiError(
                    422,
                    "model_cache_too_small",
                    "Selected models exceed MODEL_CACHE_SIZE; increase the bounded cache or select fewer models",
                )
            if transactions_per_second not in {1, 2, 5}:
                raise ApiError(422, "invalid_stream_rate", "Rate must be 1, 2, or 5 transactions/second")
            datasets = await self.repository.list_datasets()
            if dataset_id not in {str(item["id"]) for item in datasets}:
                raise ApiError(404, "stream_dataset_not_found", "Stream dataset was not found")

            self._reset_state()
            self._queue = asyncio.Queue()
            self._persistence_queue = asyncio.Queue()
            self._run_gate = asyncio.Event()
            self._stop_requested = asyncio.Event()
            self._producer_done = asyncio.Event()
            self.dataset_id = dataset_id
            self.selected_models = list(selected_models)
            self.selected_versions = sorted({spec.version_name for spec in specs})
            self.transactions_per_second = transactions_per_second
            self.status = "LOADING"
            self.run_id = await self.repository.create_run(
                dataset_id=dataset_id,
                selected_versions=self.selected_versions,
                selected_models=self.selected_models,
                transactions_per_second=transactions_per_second,
            )

            load_results = await asyncio.to_thread(
                self.model_manager.preload, self.selected_models
            )
            failed = [item for item in load_results if item["status"] != "loaded"]
            if failed:
                self.status = "FAILED"
                await self.repository.update_run(
                    self.run_id,
                    {"status": "FAILED", "completed_at": _now_iso(), "updated_at": _now_iso()},
                )
                raise ApiError(
                    503,
                    "stream_models_unavailable",
                    "A selected model could not be prepared",
                    details=failed,
                )
            if "V2" in self.selected_versions:
                self._behavioral_reference = await asyncio.to_thread(
                    self.reference_provider.get_copy
                )
            self.status = "RUNNING"
            self.started_at = datetime.now(UTC)
            self._run_gate.set()
            await self.repository.update_run(
                self.run_id,
                {
                    "status": "RUNNING",
                    "started_at": self.started_at.isoformat(),
                    "updated_at": self.started_at.isoformat(),
                },
            )
            self._coordinator = asyncio.create_task(self._run(), name=f"stream-{self.run_id}")
            await self.broker.publish("stream_started", self.snapshot())
            return self.snapshot()

    async def pause(self) -> dict[str, Any]:
        async with self._lock:
            if self.status != "RUNNING":
                raise ApiError(409, "stream_not_running", "Only a running stream can be paused")
            self.status = "PAUSED"
            self._run_gate.clear()
            assert self.run_id is not None
            await self.repository.update_run(
                self.run_id, {"status": "PAUSED", "updated_at": _now_iso()}
            )
            await self.broker.publish("stream_paused", self.snapshot())
            return self.snapshot()

    async def resume(self) -> dict[str, Any]:
        async with self._lock:
            if self.status != "PAUSED":
                raise ApiError(409, "stream_not_paused", "Only a paused stream can be resumed")
            self.status = "RUNNING"
            self._run_gate.set()
            assert self.run_id is not None
            await self.repository.update_run(
                self.run_id, {"status": "RUNNING", "updated_at": _now_iso()}
            )
            await self.broker.publish("stream_resumed", self.snapshot())
            return self.snapshot()

    async def stop(self) -> dict[str, Any]:
        async with self._lock:
            if self.status not in {"RUNNING", "PAUSED", "LOADING"}:
                raise ApiError(409, "stream_not_active", "There is no active stream to stop")
            self.status = "STOPPING"
            self._stop_requested.set()
            self._run_gate.set()
            await self.broker.publish("stream_stopping", self.snapshot())
            coordinator = self._coordinator
        if coordinator is not None:
            await coordinator
        return self.snapshot()

    async def restart(self) -> dict[str, Any]:
        dataset_id = self.dataset_id
        models = list(self.selected_models)
        rate = self.transactions_per_second
        if not dataset_id or not models:
            raise ApiError(409, "stream_not_initialized", "No stream configuration can be restarted")
        if self.status in {"RUNNING", "PAUSED", "LOADING"}:
            await self.stop()
        return await self.start(
            dataset_id=dataset_id,
            selected_models=models,
            transactions_per_second=rate,
        )

    def snapshot(self) -> dict[str, Any]:
        latencies = list(self._latencies_ms)
        elapsed = (
            (datetime.now(UTC) - self.started_at).total_seconds()
            if self.started_at
            else 0.0
        )
        return {
            "stream_run_id": self.run_id,
            "dataset_id": self.dataset_id,
            "status": self.status,
            "selected_versions": self.selected_versions,
            "selected_models": self.selected_models,
            "transactions_per_second": self.transactions_per_second,
            "transactions_received": self.received_count,
            "transactions_processed": self.processed_count,
            "transactions_queued": self._queue.qsize(),
            "currently_processing": self.currently_processing,
            "current_sequence": self.current_sequence,
            "current_throughput": round(self.processed_count / elapsed, 3) if elapsed else 0.0,
            "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            "p95_latency_ms": round(_percentile(latencies, 0.95), 3) if latencies else 0.0,
            "fraud_alerts": self.fraud_count,
            "suspicious_transaction_value": round(self.suspicious_transaction_value, 2),
            "failed_transactions": self.failed_count,
            "unpersisted_transactions": self._unpersisted_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    async def _run(self) -> None:
        producer = asyncio.create_task(self._produce(), name="fifo-producer")
        consumer = asyncio.create_task(self._consume(), name="fifo-consumer")
        persistence = asyncio.create_task(self._persist(), name="persistence-writer")
        try:
            await producer
            await self._queue.join()
            await consumer
            await self._persistence_queue.put(None)
            await persistence
        except Exception as error:
            self.status = "FAILED"
            await self.broker.publish(
                "stream_failed", {**self.snapshot(), "error_code": type(error).__name__}
            )
        finally:
            for task in (producer, consumer, persistence):
                if not task.done():
                    task.cancel()
            await asyncio.gather(producer, consumer, persistence, return_exceptions=True)
            self.completed_at = datetime.now(UTC)
            if self._unpersisted_count:
                self.status = "FAILED"
            elif self.status != "FAILED":
                self.status = "STOPPED" if self._stop_requested.is_set() else "COMPLETED"
            if self.run_id is not None:
                try:
                    await self.repository.update_run(self.run_id, self._run_values())
                except Exception:
                    self.status = "FAILED"
            await self.broker.publish("stream_finished", self.snapshot())

    async def _produce(self) -> None:
        assert self.dataset_id is not None
        after_sequence = -1
        buffer = await self.repository.fetch_transaction_batch(
            self.dataset_id, after_sequence=after_sequence, limit=self.PREFETCH_SIZE
        )
        pending_fetch: asyncio.Task[list[StoredStreamTransaction]] | None = None
        previous_sequence = -1
        try:
            while buffer and not self._stop_requested.is_set():
                for position, stored in enumerate(buffer):
                    if self._stop_requested.is_set():
                        break
                    await self._run_gate.wait()
                    if self._stop_requested.is_set():
                        break
                    if stored.sequence_number <= previous_sequence:
                        raise RuntimeError("Supabase stream order is not strictly increasing")
                    previous_sequence = stored.sequence_number
                    remaining = len(buffer) - position - 1
                    if remaining == self.PREFETCH_LOW_WATERMARK and pending_fetch is None:
                        pending_fetch = asyncio.create_task(
                            self.repository.fetch_transaction_batch(
                                self.dataset_id,
                                after_sequence=buffer[-1].sequence_number,
                                limit=self.PREFETCH_SIZE,
                            )
                        )
                    event = QueueEvent(
                        stored=stored,
                        arrival_time=datetime.now(UTC),
                        queue_position=self._queue.qsize() + 1,
                    )
                    await self._queue.put(event)
                    self.received_count += 1
                    await self.broker.publish(
                        "transaction_received",
                        {
                            "sequence_number": stored.sequence_number,
                            "transaction_id": stored.transaction_id,
                            "arrival_time": event.arrival_time.isoformat(),
                            "queue_position": event.queue_position,
                            "status": "QUEUED",
                            "queue_length": self._queue.qsize(),
                        },
                    )
                    await asyncio.sleep(1 / self.transactions_per_second)
                if self._stop_requested.is_set():
                    break
                if pending_fetch is not None:
                    buffer = await pending_fetch
                    pending_fetch = None
                else:
                    buffer = await self.repository.fetch_transaction_batch(
                        self.dataset_id,
                        after_sequence=previous_sequence,
                        limit=self.PREFETCH_SIZE,
                    )
        finally:
            if pending_fetch is not None and not pending_fetch.done():
                pending_fetch.cancel()
                with suppress(asyncio.CancelledError):
                    await pending_fetch
            self._producer_done.set()

    async def _consume(self) -> None:
        while True:
            if self._producer_done.is_set() and self._queue.empty():
                return
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except TimeoutError:
                if self._producer_done.is_set() and self._queue.empty():
                    return
                continue
            await self._run_gate.wait()
            started = datetime.now(UTC)
            stored = event.stored
            self.currently_processing = {
                "sequence_number": stored.sequence_number,
                "transaction_id": stored.transaction_id,
                "processing_started_at": started.isoformat(),
                "status": "PROCESSING",
            }
            await self.broker.publish("transaction_processing", self.currently_processing)
            predictions: tuple[PersistedModelPrediction, ...] = ()
            status = "COMPLETED"
            error_code = None
            try:
                response = await asyncio.to_thread(
                    self.prediction_service.predict,
                    stored.transaction_payload,
                    self.selected_models,
                    behavioral_reference=self._behavioral_reference,
                )
                predictions = tuple(
                    PersistedModelPrediction(
                        model_identifier=item["model_identifier"],
                        risk_score=item["risk_score"],
                        threshold=item["threshold"],
                        decision=item["decision"],
                        latency_ms=item["latency_ms"],
                        model_run_id=item["run_id"],
                    )
                    for item in response["results"]
                )
                if self._behavioral_reference is not None:
                    aligned = self.raw_contract.align(
                        pd.DataFrame([stored.transaction_payload])
                    )
                    await asyncio.to_thread(
                        update_behavioral_reference,
                        self._behavioral_reference,
                        aligned,
                    )
                fraud_votes = sum(item.decision for item in predictions)
                if fraud_votes:
                    self.fraud_count += 1
                    amount = pd.to_numeric(
                        stored.transaction_payload.get("TransactionAmt"), errors="coerce"
                    )
                    if pd.notna(amount):
                        self.suspicious_transaction_value += float(amount)
                self.processed_count += 1
            except Exception as error:
                status = "FAILED"
                error_code = type(error).__name__
                self.failed_count += 1
            completed = datetime.now(UTC)
            latency_ms = (completed - started).total_seconds() * 1_000
            self._latencies_ms.append(latency_ms)
            self.current_sequence = stored.sequence_number
            self.currently_processing = None
            amount_value = pd.to_numeric(
                stored.transaction_payload.get("TransactionAmt"), errors="coerce"
            )
            record = CompletedStreamRecord(
                stream_transaction_id=stored.id,
                sequence_number=stored.sequence_number,
                transaction_id=stored.transaction_id,
                arrival_time=event.arrival_time,
                queue_position=event.queue_position,
                processing_started_at=started,
                completed_at=completed,
                status=status,
                actual_label=stored.actual_label,
                suspicious_amount=float(amount_value) if pd.notna(amount_value) else None,
                predictions=predictions,
                error_code=error_code,
            )
            await self._persistence_queue.put(record)
            await self.broker.publish(
                "transaction_completed" if status == "COMPLETED" else "transaction_failed",
                {
                    "sequence_number": stored.sequence_number,
                    "transaction_id": stored.transaction_id,
                    "arrival_time": event.arrival_time.isoformat(),
                    "queue_position": event.queue_position,
                    "processing_started_at": started.isoformat(),
                    "completed_at": completed.isoformat(),
                    "status": status,
                    "actual_label": stored.actual_label,
                    "results": response["results"] if status == "COMPLETED" else [],
                    "agreement": response["agreement"] if status == "COMPLETED" else None,
                    "latency_ms": latency_ms,
                    "queue_length": self._queue.qsize(),
                    "error_code": error_code,
                },
            )
            self._queue.task_done()

    async def _persist(self) -> None:
        batch: list[CompletedStreamRecord] = []
        while True:
            try:
                record = await asyncio.wait_for(
                    self._persistence_queue.get(),
                    timeout=self.PERSIST_INTERVAL_SECONDS,
                )
            except TimeoutError:
                record = None if self.status in {"COMPLETED", "FAILED"} else "timeout"
            if record == "timeout":
                if batch:
                    await self._flush(batch)
                    batch = []
                continue
            if record is None:
                if batch:
                    await self._flush(batch)
                return
            batch.append(record)
            if len(batch) >= self.PERSIST_BATCH_SIZE:
                await self._flush(batch)
                batch = []

    async def _flush(self, records: list[CompletedStreamRecord]) -> None:
        assert self.run_id is not None
        for attempt in range(3):
            try:
                await self.repository.persist_completed_batch(
                    self.run_id, records, self._run_values()
                )
                return
            except Exception:
                if attempt == 2:
                    self._unpersisted_count += len(records)
                    await self.broker.publish(
                        "persistence_failed",
                        {"record_count": len(records), "attempts": 3},
                    )
                    return
                await asyncio.sleep(0.25 * (2**attempt))

    def _run_values(self) -> dict[str, Any]:
        return {
            "status": self.status if self.status in {"RUNNING", "PAUSED"} else (
                "FAILED" if self.status == "FAILED" or self._unpersisted_count else
                "STOPPED" if self._stop_requested.is_set() else "COMPLETED"
            ),
            "current_sequence": self.current_sequence,
            "received_count": self.received_count,
            "processed_count": self.processed_count,
            "fraud_count": self.fraud_count,
            "failed_count": self.failed_count,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": _now_iso(),
        }


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
