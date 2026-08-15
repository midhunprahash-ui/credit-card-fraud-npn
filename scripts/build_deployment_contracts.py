#!/usr/bin/env python3
"""Build deterministic deployment and public model-catalog contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.catalog import load_model_catalog
from src.fraud_pipeline.artifacts import sha256_file
from src.fraud_pipeline.model_adapters import verify_artifact_manifest
from src.fraud_pipeline.registry import ModelRegistry


def main() -> None:
    registry = ModelRegistry.load(PROJECT_ROOT)
    models = {}
    for spec in registry:
        verification = verify_artifact_manifest(spec.artifact_directory)
        manifest_path = spec.artifact_directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        models[spec.identifier] = {
            "run_id": spec.run_id,
            "object_prefix": (
                f"models/{spec.version_name.lower()}/{spec.model_key}/{spec.run_id}"
            ),
            "manifest_sha256": sha256_file(manifest_path),
            "files": verification["files_verified"] + 1,
            "bytes": manifest_path.stat().st_size
            + sum(int(item["bytes"]) for item in manifest["files"]),
        }

    behavioral = PROJECT_ROOT / "data/processed/v2/behavioral_reference.joblib"
    if not behavioral.is_file():
        raise FileNotFoundError(
            "Prepare data/processed/v2/behavioral_reference.joblib first"
        )
    deployment = {
        "schema_version": "1.0",
        "r2_prefix": "models",
        "models": models,
        "runtime": {
            "behavioral_reference.v2": {
                "object_key": "models/runtime/v2/behavioral_reference.joblib",
                "local_path": "data/processed/v2/behavioral_reference.joblib",
                "bytes": behavioral.stat().st_size,
                "sha256": sha256_file(behavioral),
            }
        },
    }
    (PROJECT_ROOT / "config/deployment_artifacts.json").write_text(
        json.dumps(deployment, indent=2, sort_keys=True) + "\n"
    )
    (PROJECT_ROOT / "config/model_catalog.json").write_text(
        json.dumps(load_model_catalog(), indent=2, sort_keys=True) + "\n"
    )
    print("Wrote deployment contracts for eight approved models")


if __name__ == "__main__":
    main()
