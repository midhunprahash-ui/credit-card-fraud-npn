import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from api.settings import Settings
from api.stream_repository import (
    CompletedStreamRecord,
    PersistedModelPrediction,
    SupabaseRepositoryError,
    SupabaseRestClient,
    SupabaseStreamRepository,
)


class RecordingClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def request(self, method, table, **kwargs):
        self.calls.append((method, table, kwargs))
        return self.responses.pop(0)


def test_server_rest_client_uses_pooled_apikey_without_authorization(
    monkeypatch,
) -> None:
    captured = {}

    class StubClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def request(self, method, url, *, headers, params, json):
            captured.update(
                {"method": method, "url": url, "headers": headers, "params": params}
            )
            request = httpx.Request(method, url)
            return httpx.Response(200, request=request, json=[])

        async def aclose(self):
            captured["closed"] = True

    monkeypatch.setattr("api.stream_repository.httpx.AsyncClient", StubClient)

    async def scenario() -> None:
        client = SupabaseRestClient(
            Settings(
                supabase_url="https://example.supabase.co",
                supabase_secret_key="test-server-secret",
            )
        )
        await client.request("GET", "stream_datasets")
        await client.close()

    asyncio.run(scenario())
    assert captured["headers"]["apikey"] == "test-server-secret"
    assert "Authorization" not in captured["headers"]
    assert captured["closed"] is True


def test_prefetch_uses_ordered_batch_query_and_separate_ground_truth_lookup() -> None:
    async def scenario() -> None:
        client = RecordingClient(
            [
                [
                    {
                        "id": 11,
                        "dataset_id": "dataset-1",
                        "sequence_number": 7,
                        "transaction_id": 1007,
                        "transaction_dt": 20.0,
                        "transaction_payload": {"TransactionID": 1007, "TransactionDT": 20.0},
                        "stream_datasets": {"labels_available": True},
                    }
                ],
                [{"stream_transaction_id": 11, "is_fraud": True}],
            ]
        )
        repository = SupabaseStreamRepository(client)
        rows = await repository.fetch_transaction_batch(
            "dataset-1", after_sequence=6, limit=100
        )
        assert rows[0].actual_label is True
        assert "isFraud" not in rows[0].transaction_payload
        transaction_query = client.calls[0][2]["params"]
        assert transaction_query["order"] == "sequence_number.asc"
        assert transaction_query["limit"] == "100"
        assert transaction_query["sequence_number"] == "gt.6"
        assert client.calls[1][1] == "stream_ground_truth"

    asyncio.run(scenario())


def test_prefetch_rejects_missing_ground_truth() -> None:
    async def scenario() -> None:
        client = RecordingClient(
            [
                [
                    {
                        "id": 11,
                        "dataset_id": "dataset-1",
                        "sequence_number": 0,
                        "transaction_id": 1001,
                        "transaction_dt": 1.0,
                        "transaction_payload": {"TransactionID": 1001},
                        "stream_datasets": {"labels_available": True},
                    }
                ],
                [],
            ]
        )
        with pytest.raises(SupabaseRepositoryError, match="missing ground truth"):
            await SupabaseStreamRepository(client).fetch_transaction_batch(
                "dataset-1", after_sequence=-1
            )

    asyncio.run(scenario())


def test_prefetch_allows_an_unlabelled_inference_dataset() -> None:
    async def scenario() -> None:
        client = RecordingClient(
            [
                [
                    {
                        "id": 12,
                        "dataset_id": "kaggle-sample",
                        "sequence_number": 0,
                        "transaction_id": 3663549,
                        "transaction_dt": 18403224.0,
                        "transaction_payload": {"TransactionID": 3663549},
                        "stream_datasets": {"labels_available": False},
                    }
                ]
            ]
        )
        rows = await SupabaseStreamRepository(client).fetch_transaction_batch(
            "kaggle-sample", after_sequence=-1
        )
        assert rows[0].actual_label is None
        assert [call[1] for call in client.calls] == ["stream_transactions"]

    asyncio.run(scenario())


def test_completed_batch_is_persisted_in_bulk_with_one_alert_per_transaction() -> None:
    async def scenario() -> None:
        now = datetime.now(UTC)
        prediction = PersistedModelPrediction(
            model_identifier="catboost.v2",
            risk_score=0.9,
            threshold=0.4,
            decision=True,
            latency_ms=2.0,
            model_run_id="selected-v2-catboost",
        )
        record = CompletedStreamRecord(
            stream_transaction_id=11,
            sequence_number=0,
            transaction_id=1001,
            arrival_time=now,
            queue_position=1,
            processing_started_at=now,
            completed_at=now,
            status="COMPLETED",
            actual_label=True,
            suspicious_amount=50.0,
            predictions=(prediction,),
        )
        client = RecordingClient([[{"id": 99, "sequence_number": 0}], [], [], []])
        repository = SupabaseStreamRepository(client)
        await repository.persist_completed_batch(
            "run-1", [record], {"status": "RUNNING"}
        )
        assert [call[1] for call in client.calls] == [
            "stream_transaction_events",
            "prediction_events",
            "fraud_alerts",
            "stream_runs",
        ]
        assert client.calls[0][2]["params"] == {
            "on_conflict": "stream_run_id,sequence_number"
        }
        prediction_body = client.calls[1][2]["body"]
        assert prediction_body[0]["actual_label"] is True
        assert prediction_body[0]["model_identifier"] == "catboost.v2"
        assert client.calls[1][2]["params"]["on_conflict"].endswith(
            "model_identifier"
        )
        alert_body = client.calls[2][2]["body"]
        assert alert_body[0]["model_agreement"] == 1
        assert alert_body[0]["selected_model_count"] == 1

    asyncio.run(scenario())


def test_analyst_action_updates_alert_status_and_writes_audit_row() -> None:
    async def scenario() -> None:
        client = RecordingClient(
            [
                [],
                [
                    {
                        "id": "action-1",
                        "action": "CONFIRMED_FRAUD",
                        "analyst_identifier": "analyst-7",
                    }
                ],
            ]
        )
        repository = SupabaseStreamRepository(client)
        result = await repository.add_alert_action(
            "alert-1",
            action="CONFIRMED_FRAUD",
            analyst_identifier="analyst-7",
            note="Reviewed device evidence",
        )
        assert result["id"] == "action-1"
        assert [call[1] for call in client.calls] == [
            "fraud_alerts",
            "analyst_actions",
        ]
        assert client.calls[0][2]["body"]["status"] == "CONFIRMED_FRAUD"
        assert client.calls[1][2]["body"]["note"] == "Reviewed device evidence"

    asyncio.run(scenario())
