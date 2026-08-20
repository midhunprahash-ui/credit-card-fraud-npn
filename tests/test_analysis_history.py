import asyncio
import csv
import io
import uuid

from fastapi.testclient import TestClient

from api.analysis_history import AnalysisHistoryRepository
from api.main import create_app
from api.settings import Settings


class RecordingClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def request(self, method, table, **kwargs):
        self.calls.append((method, table, kwargs))
        return self.responses.pop(0)


def prediction_response():
    return {
        "transaction_id": 100,
        "input_completeness": 0.8,
        "agreement": {
            "fraud_vote_count": 1,
            "selected_model_count": 1,
            "unanimous": True,
            "agreement_label": "all_flag_fraud",
        },
        "results": [
            {
                "model_identifier": "catboost.v2",
                "model_name": "CatBoost.V2",
                "model_version": "V2",
                "run_id": "model-run-1",
                "risk_score": 0.91,
                "threshold": 0.4,
                "decision": True,
                "decision_label": "fraud",
                "latency_ms": 2.5,
                "champion": True,
                "processing_status": "completed",
                "important_features": None,
            }
        ],
    }


def test_single_analysis_persists_run_input_and_each_model_result() -> None:
    async def scenario() -> None:
        client = RecordingClient(
            [
                [{"id": "run-1"}],
                [{"id": "transaction-1"}],
                [{"id": "prediction-1", "model_identifier": "catboost.v2"}],
                [],
            ]
        )
        repository = AnalysisHistoryRepository(client)
        stored = await repository.persist_single(
            client_id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            mode="single",
            selected_models=["catboost.v2"],
            input_payload={"TransactionID": 100, "TransactionDT": 50, "isFraud": 1},
            prediction=prediction_response(),
        )

        assert stored["catboost.v2"] == "prediction-1"
        assert [call[1] for call in client.calls] == [
            "analysis_runs",
            "analysis_transactions",
            "analysis_prediction_results",
            "analysis_runs",
        ]
        transaction = client.calls[1][2]["body"]
        assert transaction["input_payload"] == {
            "TransactionID": 100,
            "TransactionDT": 50,
        }
        result = client.calls[2][2]["body"][0]
        assert result["model_identifier"] == "catboost.v2"
        assert result["decision"] is True

    asyncio.run(scenario())


def test_history_export_keeps_required_columns_and_marks_missing_explanations() -> None:
    class ExportRepository(AnalysisHistoryRepository):
        async def _all_rows(self, table, params):
            assert table == "analysis_runs"
            return [{"id": "run-1", "created_at": "2026-08-20T00:00:00Z"}]

        async def get_run(self, *, client_id, run_id):
            return {
                "run": {"id": run_id},
                "transactions": [
                    {
                        "raw_transaction_id": "100",
                        "transaction_id": 100,
                        "input_payload": {"TransactionID": 100, "TransactionAmt": 25},
                        "status": "COMPLETED",
                        "error_code": None,
                        "error_message": None,
                        "predictions": [
                            {
                                "model_identifier": "catboost.v2",
                                "decision": True,
                                "risk_score": 0.91,
                                "threshold": 0.4,
                                "explanation_status": "NOT_GENERATED",
                                "top_contributed_features": None,
                                "reasoning": None,
                            }
                        ],
                    }
                ],
            }

    async def scenario() -> None:
        repository = ExportRepository(RecordingClient([]))
        content = await repository.export_csv(
            client_id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            mode="csv",
        )
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
        assert rows[0]["transaction_id"] == "100"
        assert rows[0]["predicted_output"] == "Fraud"
        assert rows[0]["top_contributed_features"] == "Not generated"
        assert rows[0]["reasoning"] == "Not generated"
        assert "TransactionAmt" in rows[0]["input_columns"]

    asyncio.run(scenario())


def test_cached_explanation_is_returned_without_recomputing() -> None:
    async def scenario() -> None:
        client = RecordingClient(
            [
                [
                    {
                        "id": "prediction-1",
                        "analysis_transaction_id": "transaction-1",
                        "model_identifier": "catboost.v2",
                        "decision": True,
                        "explanation_status": "COMPLETED",
                        "explanation_technique": "shap",
                        "explanation_technique_label": "SHAP feature contributions",
                        "top_contributed_features": [],
                        "reasoning": "Saved reasoning",
                        "reasoning_source": "template",
                    }
                ],
                [
                    {
                        "id": "transaction-1",
                        "analysis_run_id": "run-1",
                        "transaction_id": 100,
                        "input_payload": {"TransactionID": 100},
                    }
                ],
                [{"id": "run-1"}],
            ]
        )

        class MustNotExplain:
            def explain(self, *args, **kwargs):
                raise AssertionError("cached explanations must not be recomputed")

        result = await AnalysisHistoryRepository(client).explain_prediction(
            client_id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            prediction_id="prediction-1",
            prediction_service=MustNotExplain(),
        )
        assert result["transaction_id"] == 100
        assert result["behavioral_explanation"] == "Saved reasoning"

    asyncio.run(scenario())


def test_prediction_route_requires_browser_identity_and_returns_history_ids() -> None:
    class PredictionService:
        def predict(self, transaction, model_identifiers):
            return prediction_response()

    class HistoryRepository:
        async def persist_single(self, **kwargs):
            assert kwargs["client_id"] == uuid.UUID(
                "11111111-1111-4111-8111-111111111111"
            )
            return {
                "run_id": "22222222-2222-4222-8222-222222222222",
                "catboost.v2": "33333333-3333-4333-8333-333333333333",
            }

    client = TestClient(
        create_app(
            Settings(_env_file=None),
            prediction_service=PredictionService(),
            history_repository=HistoryRepository(),
        )
    )
    missing = client.post(
        "/predict",
        json={
            "model_identifiers": ["catboost.v2"],
            "transaction": {"TransactionID": 100, "TransactionDT": 50},
        },
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "missing_history_client"

    stored = client.post(
        "/predict",
        headers={"X-Client-ID": "11111111-1111-4111-8111-111111111111"},
        json={
            "model_identifiers": ["catboost.v2"],
            "transaction": {"TransactionID": 100, "TransactionDT": 50},
        },
    )
    assert stored.status_code == 200
    assert stored.json()["history_status"] == "stored"
    assert stored.json()["results"][0]["history_prediction_id"] == (
        "33333333-3333-4333-8333-333333333333"
    )
