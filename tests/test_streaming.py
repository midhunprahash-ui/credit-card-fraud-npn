import asyncio
from dataclasses import dataclass
from typing import Any

from api.stream_repository import StoredStreamTransaction
from api.streaming import StreamController


@dataclass
class FakeSpec:
    version_name: str = "V1"


class FakeRegistry:
    def get(self, identifier: str) -> FakeSpec:
        if identifier != "logistic_regression.v1":
            raise ValueError("unknown model")
        return FakeSpec()


class FakeModelManager:
    max_loaded_models = 8

    def preload(self, identifiers: list[str]) -> list[dict[str, str]]:
        return [{"model_identifier": value, "status": "loaded"} for value in identifiers]


class FakePredictionService:
    def __init__(self) -> None:
        self.seen_ids: list[int] = []

    def predict(
        self,
        payload: dict[str, Any],
        model_identifiers: list[str],
        *,
        behavioral_reference=None,
    ) -> dict[str, Any]:
        assert "isFraud" not in payload
        transaction_id = int(payload["TransactionID"])
        self.seen_ids.append(transaction_id)
        score = 0.9 if transaction_id % 2 else 0.1
        return {
            "results": [
                {
                    "model_identifier": model_identifiers[0],
                    "risk_score": score,
                    "threshold": 0.5,
                    "decision": score >= 0.5,
                    "latency_ms": 1.0,
                    "run_id": "run-v1",
                }
            ],
            "agreement": {
                "fraud_vote_count": int(score >= 0.5),
                "selected_model_count": 1,
            },
        }


class FakeReferenceProvider:
    def get_copy(self):
        return {}


class FakeRepository:
    def __init__(self, count: int = 5, *, fail_persistence: bool = False) -> None:
        self.rows = [
            StoredStreamTransaction(
                id=index + 1,
                dataset_id="dataset-1",
                sequence_number=index,
                transaction_id=1001 + index,
                transaction_dt=float(index),
                transaction_payload={
                    "TransactionID": 1001 + index,
                    "TransactionDT": float(index),
                    "TransactionAmt": 10.0,
                },
                actual_label=bool(index % 2),
            )
            for index in range(count)
        ]
        self.persisted = []
        self.run_updates: list[dict[str, Any]] = []
        self.fetch_limits: list[int] = []
        self.fail_persistence = fail_persistence

    async def list_datasets(self):
        return [{"id": "dataset-1", "name": "demo_chronological"}]

    async def fetch_transaction_batch(self, dataset_id, *, after_sequence, limit=100):
        self.fetch_limits.append(limit)
        return [row for row in self.rows if row.sequence_number > after_sequence][:limit]

    async def create_run(self, **kwargs):
        return "stream-run-1"

    async def update_run(self, run_id, values):
        self.run_updates.append(dict(values))

    async def persist_completed_batch(self, run_id, records, run_values):
        if self.fail_persistence:
            raise RuntimeError("database unavailable")
        self.persisted.extend(records)
        self.run_updates.append(dict(run_values))


def make_controller(repository: FakeRepository):
    service = FakePredictionService()
    controller = StreamController(
        repository,
        FakeRegistry(),
        FakeModelManager(),
        service,
        FakeReferenceProvider(),
        raw_contract=None,
    )
    controller.PERSIST_BATCH_SIZE = 2
    controller.PERSIST_INTERVAL_SECONDS = 0.05
    return controller, service


async def wait_until(predicate, timeout: float = 3.0) -> None:
    started = asyncio.get_running_loop().time()
    while not predicate():
        if asyncio.get_running_loop().time() - started > timeout:
            raise AssertionError("condition was not reached before timeout")
        await asyncio.sleep(0.01)


def test_stream_processes_strict_fifo_and_reveals_labels_only_after_prediction() -> None:
    async def scenario() -> None:
        repository = FakeRepository(count=4)
        controller, service = make_controller(repository)
        await controller.start(
            dataset_id="dataset-1",
            selected_models=["logistic_regression.v1"],
            transactions_per_second=5,
        )
        assert controller._coordinator is not None
        await controller._coordinator

        assert controller.status == "COMPLETED"
        assert service.seen_ids == [1001, 1002, 1003, 1004]
        assert [record.sequence_number for record in repository.persisted] == [0, 1, 2, 3]
        assert [record.actual_label for record in repository.persisted] == [False, True, False, True]
        assert repository.fetch_limits and set(repository.fetch_limits) == {100}
        assert controller.snapshot()["transactions_queued"] == 0

    asyncio.run(scenario())


def test_stream_pause_resume_locks_progress_then_completes() -> None:
    async def scenario() -> None:
        repository = FakeRepository(count=6)
        controller, _ = make_controller(repository)
        await controller.start(
            dataset_id="dataset-1",
            selected_models=["logistic_regression.v1"],
            transactions_per_second=5,
        )
        await wait_until(lambda: controller.received_count >= 2)
        await controller.pause()
        await asyncio.sleep(0.3)
        paused_received = controller.received_count
        paused_processed = controller.processed_count
        await asyncio.sleep(0.3)
        assert (controller.received_count, controller.processed_count) == (
            paused_received,
            paused_processed,
        )
        await controller.resume()
        assert controller._coordinator is not None
        await controller._coordinator
        assert controller.status == "COMPLETED"
        assert controller.processed_count == 6

    asyncio.run(scenario())


def test_stop_drains_fifo_without_silently_dropping_accepted_events() -> None:
    async def scenario() -> None:
        repository = FakeRepository(count=10)
        controller, service = make_controller(repository)
        await controller.start(
            dataset_id="dataset-1",
            selected_models=["logistic_regression.v1"],
            transactions_per_second=5,
        )
        await wait_until(lambda: controller.received_count >= 2)
        result = await controller.stop()
        assert result["status"] == "STOPPED"
        assert result["transactions_received"] == result["transactions_processed"]
        assert len(service.seen_ids) == result["transactions_received"]
        assert len(repository.persisted) == result["transactions_received"]

    asyncio.run(scenario())


def test_persistence_failure_marks_run_failed_without_losing_count() -> None:
    async def scenario() -> None:
        repository = FakeRepository(count=1, fail_persistence=True)
        controller, _ = make_controller(repository)
        await controller.start(
            dataset_id="dataset-1",
            selected_models=["logistic_regression.v1"],
            transactions_per_second=5,
        )
        assert controller._coordinator is not None
        await controller._coordinator
        assert controller.status == "FAILED"
        assert controller.processed_count == 1
        assert controller.failed_count == 0
        assert controller.snapshot()["unpersisted_transactions"] == 1

    asyncio.run(scenario())
