import json
from pathlib import Path

from src.fraud_pipeline.artifacts import build_manifest, write_json
from src.fraud_pipeline.inference_runtime import (
    selected_model_specs,
    verify_artifact_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_selected_catalog_contains_exactly_eight_canonical_models() -> None:
    specs = selected_model_specs(PROJECT_ROOT)

    assert [spec.model_name for spec in specs] == [
        "LogisticRegression.V1",
        "LightGBM.V1",
        "CatBoost.V1",
        "NeuralNetwork.V1",
        "LogisticRegression.V2",
        "LightGBM.V2",
        "CatBoost.V2",
        "NeuralNetwork.V2",
    ]

    assert [spec.identifier for spec in specs] == [
        "logistic_regression.v1",
        "lightgbm.v1",
        "catboost.v1",
        "neural_network.v1",
        "logistic_regression.v2",
        "lightgbm.v2",
        "catboost.v2",
        "neural_network.v2",
    ]


def test_manifest_verifier_rejects_changed_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "model.txt"
    artifact.write_text("trusted")
    write_json(tmp_path / "manifest.json", build_manifest(tmp_path))
    assert verify_artifact_manifest(tmp_path) == {"files_verified": 1}

    artifact.write_text("changed")

    try:
        verify_artifact_manifest(tmp_path)
    except ValueError as error:
        assert "mismatch" in str(error)
    else:
        raise AssertionError("Changed artifact should fail manifest verification")


def test_selected_registry_run_ids_match_artifact_directories() -> None:
    for spec in selected_model_specs(PROJECT_ROOT):
        manifest = json.loads((spec.artifact_directory / "manifest.json").read_text())
        assert manifest["artifact_directory"] == spec.run_id
