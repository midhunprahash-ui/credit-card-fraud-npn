from __future__ import annotations

import json
import io
import zipfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.errors import ApiError
from api.main import create_app
from api.settings import Settings


class FakePredictionService:
    def predict(
        self, transaction: dict[str, Any], model_identifiers: list[str]
    ) -> dict[str, Any]:
        transaction_id = transaction.get("TransactionID")
        if (
            not isinstance(transaction_id, (int, float))
            or transaction_id <= 0
            or transaction_id % 1 != 0
        ):
            raise ApiError(422, "invalid_prediction_input", "Invalid TransactionID")
        results = []
        for index, identifier in enumerate(model_identifiers):
            version = identifier.rsplit(".", 1)[1].upper()
            base = {
                "logistic_regression": "LogisticRegression",
                "lightgbm": "LightGBM",
                "catboost": "CatBoost",
                "neural_network": "NeuralNetwork",
            }[identifier.rsplit(".", 1)[0]]
            score = 0.8 if index == 0 else 0.2
            results.append(
                {
                    "model_identifier": identifier,
                    "model_name": f"{base}.{version}",
                    "model_version": version,
                    "run_id": "test-run",
                    "risk_score": score,
                    "threshold": 0.5,
                    "decision": score >= 0.5,
                    "decision_label": "fraud" if score >= 0.5 else "legitimate",
                    "latency_ms": 1.0,
                    "champion": False,
                    "processing_status": "completed",
                    "important_features": None,
                }
            )
        votes = sum(item["decision"] for item in results)
        return {
            "transaction_id": int(transaction_id),
            "input_completeness": 0.75,
            "results": results,
            "agreement": {
                "fraud_vote_count": votes,
                "selected_model_count": len(results),
                "unanimous": votes in {0, len(results)},
                "agreement_label": "disagreement",
            },
        }

    def explain(
        self, transaction: dict[str, Any], model_identifier: str
    ) -> dict[str, Any]:
        return {
            "transaction_id": int(transaction["TransactionID"]),
            "model_identifier": model_identifier,
            "method": "local_feature_contribution",
            "explanation_technique": "shap",
            "explanation_technique_label": "SHAP feature contributions",
            "important_features": [
                {
                    "feature": "TransactionAmt",
                    "contribution": 0.12,
                    "direction": "toward_fraud",
                }
            ],
        }


class FakeDemoRepository:
    dataset_name = "kaggle_inference_sample"
    split = "kaggle_inference"
    labels_available = False

    def list(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return [
            {
                "transaction_id": 100 + offset,
                "transaction_dt": 500.0,
                "transaction_amount": 25.0,
                "product_code": "W",
                "has_identity": True,
            }
        ][:limit]

    def get(self, transaction_id: int) -> dict[str, Any]:
        if transaction_id != 100:
            raise ApiError(404, "transaction_not_found", "Transaction not found")
        return {
            "TransactionID": 100,
            "TransactionDT": 500,
            "TransactionAmt": 25.0,
        }


def client(settings: Settings | None = None) -> TestClient:
    return TestClient(
        create_app(
            settings or Settings(_env_file=None),
            prediction_service=FakePredictionService(),
            demo_repository=FakeDemoRepository(),
        )
    )


def test_input_schema_excludes_label_and_reports_limits() -> None:
    response = client().get("/input-schema")

    assert response.status_code == 200
    body = response.json()
    assert body["required_fields"] == ["TransactionID", "TransactionDT"]
    assert body["target_excluded"] == "isFraud"
    assert "isFraud" not in body["optional_fields"]
    assert body["batch_limits"]["maximum_rows"] == 1000


def test_demo_lookup_never_returns_label() -> None:
    api = client()
    listing = api.get("/demo-transactions", params={"limit": 1})
    detail = api.get("/transactions/100")

    assert listing.status_code == 200
    assert listing.json()["labels_hidden"] is True
    assert listing.json()["labels_available"] is False
    assert listing.json()["dataset"] == "kaggle_inference_sample"
    assert detail.status_code == 200
    assert detail.json()["labels_hidden"] is True
    assert detail.json()["labels_available"] is False
    assert "isFraud" not in detail.json()["transaction_payload"]


def test_single_prediction_returns_independent_results_and_agreement() -> None:
    response = client().post(
        "/predict",
        json={
            "model_identifiers": ["catboost.v2", "lightgbm.v1"],
            "transaction": {
                "TransactionID": 100,
                "TransactionDT": 500,
                "isFraud": 1,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == 100
    assert [item["model_name"] for item in body["results"]] == [
        "CatBoost.V2",
        "LightGBM.V1",
    ]
    assert body["agreement"] == {
        "fraud_vote_count": 1,
        "selected_model_count": 2,
        "unanimous": False,
        "agreement_label": "disagreement",
    }


def test_local_explanation_is_returned_on_demand() -> None:
    response = client().post(
        "/explain",
        json={
            "model_identifier": "catboost.v2",
            "transaction": {
                "TransactionID": 100,
                "TransactionDT": 500,
                "TransactionAmt": 25,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["explanation_technique"] == "shap"
    assert response.json()["explanation_technique_label"] == (
        "SHAP feature contributions"
    )
    assert response.json()["important_features"][0] == {
        "feature": "TransactionAmt",
        "contribution": 0.12,
        "direction": "toward_fraud",
    }


def test_one_row_csv_uses_single_prediction_contract() -> None:
    response = client().post(
        "/predict/file",
        data={"models": '["catboost.v2"]'},
        files={
            "file": (
                "transaction.csv",
                b"TransactionID,TransactionDT,TransactionAmt\n100,500,25\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["transaction_id"] == 100
    assert response.json()["results"][0]["model_name"] == "CatBoost.V2"


def test_request_validation_has_standard_safe_error() -> None:
    response = client().post(
        "/predict",
        json={"model_identifiers": [], "transaction": {}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"


def test_batch_reports_duplicate_rows_and_versioned_columns() -> None:
    csv = (
        b"TransactionID,TransactionDT,TransactionAmt,isFraud\n"
        b"100,500,25,1\n101,501,30,0\n101,502,40,1\n"
    )
    response = client().post(
        "/predict/batch",
        data={"models": json.dumps(["catboost.v2", "lightgbm.v1"])},
        files={"file": ("transactions.csv", csv, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_rows"] == 3
    assert body["summary"]["valid_rows"] == 1
    assert body["summary"]["invalid_rows"] == 2
    assert body["summary"]["fraud_count_by_model"] == {
        "catboost.v2": 1,
        "lightgbm.v1": 0,
    }
    assert "CatBoost.V2_score" in body["results"][0]
    assert "LightGBM.V1_decision" in body["results"][0]
    assert body["results"][0]["input_payload"]["TransactionAmt"] == 25
    assert "isFraud" not in body["results"][0]["input_payload"]
    assert {
        row["error_code"] for row in body["invalid_row_report"]
    } == {"duplicate_transaction_id"}


def test_batch_invalid_fractional_identifier_is_returned_safely() -> None:
    response = client().post(
        "/predict/batch",
        data={"models": '["catboost.v2"]'},
        files={
            "file": (
                "transactions.csv",
                b"TransactionID,TransactionDT\n1.5,500\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    report = response.json()["invalid_row_report"]
    assert report[0]["transaction_id"] == 1.5
    assert report[0]["error_code"] == "invalid_prediction_input"


def test_batch_zip_contains_results_and_invalid_row_downloads() -> None:
    response = client().post(
        "/predict/batch",
        data={"models": '["catboost.v2"]', "response_format": "zip"},
        files={
            "file": (
                "transactions.csv",
                b"TransactionID,TransactionDT,TransactionAmt\n100,500,25\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "prediction_results.csv",
            "invalid_rows.csv",
            "summary.json",
        }
        prediction_csv = archive.read("prediction_results.csv")
        assert b"CatBoost.V2_score" in prediction_csv
        assert b"input_payload" not in prediction_csv


@pytest.mark.parametrize(
    "filename, content_type, expected_status, expected_code",
    [
        ("transactions.txt", "text/plain", 415, "invalid_file_type"),
        ("transactions.csv", "text/csv", 422, "missing_required_columns"),
    ],
)
def test_batch_rejects_invalid_uploads(
    filename: str, content_type: str, expected_status: int, expected_code: str
) -> None:
    response = client().post(
        "/predict/batch",
        data={"models": '["catboost.v2"]'},
        files={"file": (filename, b"TransactionID\n1\n", content_type)},
    )
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


def test_batch_enforces_upload_size_before_parsing() -> None:
    api = client(Settings(_env_file=None, batch_max_file_bytes=20))
    response = api.post(
        "/predict/batch",
        data={"models": '["catboost.v2"]'},
        files={
            "file": (
                "transactions.csv",
                b"TransactionID,TransactionDT\n1,2\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "batch_file_too_large"


def test_batch_rejects_unknown_model_before_row_processing() -> None:
    response = client().post(
        "/predict/batch",
        data={"models": '["unknown.v1"]'},
        files={
            "file": (
                "transactions.csv",
                b"TransactionID,TransactionDT\n1,2\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_model_selection"
