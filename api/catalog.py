"""Read the approved V1/V2 registries and expose canonical model names."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal


VersionName = Literal["V1", "V2"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRIES: dict[VersionName, Path] = {
    "V1": PROJECT_ROOT / "config" / "model_registry.json",
    "V2": PROJECT_ROOT / "config" / "model_registry_v2.json",
}
DISPLAY_NAMES = {
    "logistic_regression": "Logistic Regression",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
    "neural_network": "Neural Network",
}
MODEL_ORDER = tuple(DISPLAY_NAMES)


def load_model_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for version_name, registry_path in REGISTRIES.items():
        registry = json.loads(registry_path.read_text())
        registered_models = registry.get("models", {})
        for model_key in MODEL_ORDER:
            config = registered_models.get(model_key)
            if not config or not config.get("enabled"):
                raise ValueError(f"Required model is not enabled: {model_key}.{version_name}")
            display_name = DISPLAY_NAMES[model_key]
            catalog.append(
                {
                    "model_key": model_key,
                    "model_name": f"{display_name}.{version_name}",
                    "display_name": display_name,
                    "version_name": version_name,
                    "run_id": config["run_id"],
                    "threshold": config["threshold"],
                    "validation_pr_auc": config["validation_pr_auc"],
                    "test_pr_auc": config["test_pr_auc"],
                }
            )
    return catalog

