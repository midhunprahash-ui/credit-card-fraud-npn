import json
import shutil
from pathlib import Path

import pytest

from src.fraud_pipeline.artifacts import build_manifest, sha256_file, write_json
from src.fraud_pipeline.deployment_artifacts import (
    DeploymentArtifactContract,
    DeploymentArtifactError,
    R2ArtifactStore,
)
from src.fraud_pipeline.registry import ModelSpec


class FileBackedS3:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.downloads: list[str] = []

    def download_file(self, bucket: str, key: str, destination: str) -> None:
        self.downloads.append(key)
        shutil.copyfile(self.root / bucket / key, destination)


def fixture(tmp_path: Path):
    project = tmp_path / "project"
    source = tmp_path / "source"
    run_id = "20260815T000000Z"
    bundle = source / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "model.joblib").write_bytes(b"approved-model")
    (bundle / "feature_schema.json").write_text('{"feature_columns":["amount"]}')
    (bundle / "threshold.json").write_text('{"threshold":0.5}')
    write_json(bundle / "manifest.json", build_manifest(bundle))
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_directory"] = run_id
    write_json(bundle / "manifest.json", manifest)

    remote_prefix = f"models/v1/logistic_regression/{run_id}"
    remote = tmp_path / "remote" / "bucket" / remote_prefix
    remote.mkdir(parents=True)
    for path in bundle.iterdir():
        shutil.copyfile(path, remote / path.name)
    runtime_source = source / "behavioral.joblib"
    runtime_source.write_bytes(b"target-free-reference")
    runtime_remote = tmp_path / "remote/bucket/models/runtime/v2"
    runtime_remote.mkdir(parents=True)
    shutil.copyfile(runtime_source, runtime_remote / "behavioral_reference.joblib")

    contract_path = project / "config/deployment_artifacts.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "r2_prefix": "models",
                "models": {
                    "logistic_regression.v1": {
                        "run_id": run_id,
                        "object_prefix": remote_prefix,
                        "manifest_sha256": sha256_file(bundle / "manifest.json"),
                        "files": 4,
                        "bytes": sum(path.stat().st_size for path in bundle.iterdir()),
                    }
                },
                "runtime": {
                    "behavioral_reference.v2": {
                        "object_key": "models/runtime/v2/behavioral_reference.joblib",
                        "local_path": "data/processed/v2/behavioral_reference.joblib",
                        "bytes": runtime_source.stat().st_size,
                        "sha256": sha256_file(runtime_source),
                    }
                },
            }
        )
    )
    spec = ModelSpec(
        model_key="logistic_regression",
        version_name="V1",
        run_id=run_id,
        artifact_directory=project / f"artifacts/logistic_regression/{run_id}",
        threshold=0.5,
        champion=False,
        validation_pr_auc=0.4,
        test_pr_auc=0.2,
        files={"model_file": "model.joblib"},
    )
    contract = DeploymentArtifactContract.load(contract_path, project)
    client = FileBackedS3(tmp_path / "remote")
    return project, spec, contract, client


def test_r2_store_atomically_downloads_and_verifies_bundle(tmp_path: Path) -> None:
    project, spec, contract, client = fixture(tmp_path)
    store = R2ArtifactStore(client=client, bucket="bucket", contract=contract)

    result = store.ensure_model(spec)

    assert result == {"files_verified": 3, "downloaded": True}
    assert (spec.artifact_directory / "model.joblib").read_bytes() == b"approved-model"
    assert len(client.downloads) == 4
    cached = store.ensure_model(spec)
    assert cached == {"files_verified": 0, "downloaded": False, "cached": True}
    assert len(client.downloads) == 4
    assert not list(spec.artifact_directory.parent.glob(f".{spec.run_id}-*"))

    runtime = store.ensure_runtime("behavioral_reference.v2")
    assert runtime["downloaded"] is True
    assert (project / "data/processed/v2/behavioral_reference.joblib").read_bytes() == b"target-free-reference"


def test_r2_store_rejects_manifest_not_pinned_by_git_contract(tmp_path: Path) -> None:
    _, spec, contract, client = fixture(tmp_path)
    manifest = client.root / "bucket" / contract.model_prefix(spec) / "manifest.json"
    manifest.write_text(manifest.read_text() + "\n")
    store = R2ArtifactStore(client=client, bucket="bucket", contract=contract)

    with pytest.raises(DeploymentArtifactError, match="Manifest checksum mismatch"):
        store.ensure_model(spec)

    assert not spec.artifact_directory.exists()


def test_deployment_contract_covers_all_eight_registry_models() -> None:
    root = Path(__file__).resolve().parents[1]
    document = json.loads((root / "config/deployment_artifacts.json").read_text())

    assert len(document["models"]) == 8
    assert set(document["models"]) == {
        f"{model}.{version}"
        for version in ("v1", "v2")
        for model in (
            "logistic_regression",
            "lightgbm",
            "catboost",
            "neural_network",
        )
    }
