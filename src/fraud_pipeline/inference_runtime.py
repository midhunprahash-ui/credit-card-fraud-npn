"""Version-aware loaders for the eight approved fraud model pipelines.

Heavy native libraries are imported inside the selected branch. The verification
command runs each model in its own process so one model cannot leak memory or
native runtime state into another model's result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from .artifacts import sha256_file


VersionName = Literal["V1", "V2"]

DISPLAY_NAMES = {
    "logistic_regression": "Logistic Regression",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
    "neural_network": "Neural Network",
}
MODEL_ORDER = tuple(DISPLAY_NAMES)


@dataclass(frozen=True)
class SelectedModelSpec:
    model_key: str
    version_name: VersionName
    run_id: str
    artifact_directory: Path
    threshold: float

    @property
    def model_name(self) -> str:
        return f"{DISPLAY_NAMES[self.model_key]}.{self.version_name}"


def selected_model_specs(project_root: Path) -> list[SelectedModelSpec]:
    registry_paths: tuple[tuple[VersionName, Path], ...] = (
        ("V1", project_root / "config" / "model_registry.json"),
        ("V2", project_root / "config" / "model_registry_v2.json"),
    )
    specs: list[SelectedModelSpec] = []
    for version_name, registry_path in registry_paths:
        registry = json.loads(registry_path.read_text())
        models = registry.get("models", {})
        for model_key in MODEL_ORDER:
            model_config = models.get(model_key)
            if not model_config or not model_config.get("enabled"):
                raise ValueError(f"Required model is not enabled: {model_key}.{version_name}")
            specs.append(
                SelectedModelSpec(
                    model_key=model_key,
                    version_name=version_name,
                    run_id=model_config["run_id"],
                    artifact_directory=project_root
                    / "artifacts"
                    / model_config["artifact_subdirectory"],
                    threshold=float(model_config["threshold"]),
                )
            )
    return specs


def verify_artifact_manifest(directory: Path) -> dict[str, Any]:
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    declared = {item["path"]: item for item in manifest["files"]}
    actual = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != set(declared):
        missing = sorted(set(declared) - actual)
        unexpected = sorted(actual - set(declared))
        raise ValueError(f"Manifest file mismatch; missing={missing}, unexpected={unexpected}")

    for relative_path, item in declared.items():
        path = directory / relative_path
        if path.stat().st_size != item["bytes"]:
            raise ValueError(f"Artifact size mismatch: {relative_path}")
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"Artifact checksum mismatch: {relative_path}")
    return {"files_verified": len(actual)}


def predict_with_selected_model(
    spec: SelectedModelSpec,
    model_input: pd.DataFrame,
) -> np.ndarray:
    """Load one trusted selected bundle and return fraud risk scores."""
    directory = spec.artifact_directory

    if spec.model_key == "logistic_regression":
        import joblib

        model = joblib.load(directory / "model.joblib")
        return np.asarray(model.predict_proba(model_input)[:, 1], dtype=np.float64)

    if spec.model_key == "lightgbm":
        import joblib
        import lightgbm as lgb

        preprocessor = joblib.load(directory / "preprocessor.joblib")
        model = lgb.Booster(model_file=str(directory / "model.txt"))
        return np.asarray(model.predict(preprocessor.transform(model_input)), dtype=np.float64)

    if spec.model_key == "catboost":
        import joblib
        from catboost import CatBoostClassifier, Pool

        preprocessor = joblib.load(directory / "preprocessor.joblib")
        transformed = preprocessor.transform(model_input)
        model = CatBoostClassifier()
        model.load_model(str(directory / "model.cbm"))
        pool = Pool(transformed, cat_features=preprocessor.categorical_features)
        return np.asarray(model.predict_proba(pool)[:, 1], dtype=np.float64)

    if spec.model_key == "neural_network":
        import joblib
        import torch

        from .neural import network_from_config
        from .neural_v2 import network_v2_from_config

        preprocessor = joblib.load(
            directory / "numeric_and_categorical_preprocessor.joblib"
        )
        numeric, categorical = preprocessor.transform(model_input)
        checkpoint = torch.load(directory / "model.pt", map_location="cpu", weights_only=True)
        factory = network_from_config if spec.version_name == "V1" else network_v2_from_config
        model = factory(checkpoint["model_config"])
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        with torch.inference_mode():
            scores = torch.sigmoid(
                model(torch.from_numpy(numeric), torch.from_numpy(categorical))
            )
        return scores.detach().cpu().numpy().astype(np.float64, copy=False)

    raise ValueError(f"Unsupported model key: {spec.model_key}")

