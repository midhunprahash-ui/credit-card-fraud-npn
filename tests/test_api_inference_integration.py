from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings
from src.fraud_pipeline.registry import ModelRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_LOCAL_ASSETS = [
    PROJECT_ROOT / "data/processed/v2/test.parquet",
    PROJECT_ROOT / "data/processed/v2/behavioral_reference.joblib",
    PROJECT_ROOT / "artifacts/logistic_regression/20260814T044445Z/model.joblib",
    PROJECT_ROOT / "artifacts/v2/logistic_regression/20260815T133526Z/model.joblib",
]


@pytest.mark.skipif(
    not all(path.is_file() for path in REQUIRED_LOCAL_ASSETS),
    reason="Local ignored held-out data and selected artifacts are required",
)
def test_real_heldout_transaction_scores_through_v1_and_v2_api() -> None:
    client = TestClient(create_app(Settings(model_cache_size=2)))
    listing = client.get("/demo-transactions", params={"limit": 1})
    transaction_id = listing.json()["transactions"][0]["transaction_id"]
    detail = client.get(f"/transactions/{transaction_id}")
    payload = detail.json()["transaction_payload"]

    response = client.post(
        "/predict",
        json={
            "model_identifiers": [
                "logistic_regression.v1",
                "logistic_regression.v2",
            ],
            "transaction": payload,
        },
    )

    assert response.status_code == 200
    assert "isFraud" not in payload
    results = {
        item["model_identifier"]: item for item in response.json()["results"]
    }
    registry = ModelRegistry.load(PROJECT_ROOT)
    for identifier in ("logistic_regression.v1", "logistic_regression.v2"):
        spec = registry.get(identifier)
        expected = pd.read_parquet(
            spec.artifact_directory / "test_predictions.parquet",
            columns=["TransactionID", "probability"],
        ).iloc[0]
        assert int(expected["TransactionID"]) == transaction_id
        assert np.isclose(
            results[identifier]["risk_score"],
            float(expected["probability"]),
            rtol=1e-5,
            atol=1e-7,
        )
        assert results[identifier]["threshold"] == spec.threshold
