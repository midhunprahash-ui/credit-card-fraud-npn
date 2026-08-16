from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


def test_health_reports_eight_registered_models_without_secrets() -> None:
    settings = Settings(
        _env_file=None,
        r2_endpoint_url=None,
        r2_access_key_id=None,
        r2_secret_access_key=None,
        r2_bucket_name=None,
    )
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body.pop("model_artifacts_available") <= 8
    assert isinstance(body.pop("behavioral_reference_available"), bool)
    assert body == {
        "status": "ok",
        "environment": "development",
        "models_registered": 8,
        "supabase_configured": False,
        "r2_configured": False,
        "artifact_source": "local",
    }


def test_app_starts_and_stops_with_supabase_configured() -> None:
    settings = Settings(
        supabase_url="https://project-test-only.supabase.co",
        supabase_secret_key="sb_secret_test-only",
        r2_endpoint_url=None,
        r2_access_key_id=None,
        r2_secret_access_key=None,
        r2_bucket_name=None,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["supabase_configured"] is True


def test_model_catalog_uses_canonical_v1_v2_names() -> None:
    client = TestClient(create_app(Settings(_env_file=None)))

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
    client = TestClient(create_app(Settings(_env_file=None)))

    response = client.get("/models", params={"version": "V3"})

    assert response.status_code == 422


def test_model_catalog_exposes_comparison_metrics_when_artifacts_are_local() -> None:
    client = TestClient(create_app(Settings(_env_file=None)))

    response = client.get("/models", params={"version": "V2"})

    assert response.status_code == 200
    catboost = next(
        item
        for item in response.json()["models"]
        if item["model_identifier"] == "catboost.v2"
    )
    assert catboost["metrics"]["validation"]["pr_auc"] == catboost["validation_pr_auc"]
    assert catboost["metrics"]["test"]["confusion_matrix"] == [
        [53930, 31568],
        [201, 2882],
    ]
    assert catboost["feature_importance_available"] is True
