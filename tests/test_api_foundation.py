from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


def test_health_reports_eight_registered_models_without_secrets() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body.pop("model_artifacts_available") <= 8
    assert body == {
        "status": "ok",
        "environment": "development",
        "models_registered": 8,
        "supabase_configured": False,
        "r2_configured": False,
    }


def test_model_catalog_uses_canonical_v1_v2_names() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/models", params={"version": "V2"})

    assert response.status_code == 200
    assert [item["model_name"] for item in response.json()["models"]] == [
        "LogisticRegression.V2",
        "LightGBM.V2",
        "CatBoost.V2",
        "NeuralNetwork.V2",
    ]
    assert [item["model_identifier"] for item in response.json()["models"]] == [
        "logistic_regression.v2",
        "lightgbm.v2",
        "catboost.v2",
        "neural_network.v2",
    ]


def test_model_version_filter_rejects_unknown_versions() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/models", params={"version": "V3"})

    assert response.status_code == 422
