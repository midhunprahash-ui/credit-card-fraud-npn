"""Expose the canonical public catalog for the eight approved model runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.fraud_pipeline.model_contracts import VersionName
from src.fraud_pipeline.registry import ModelRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_model_catalog() -> list[dict[str, Any]]:
    return [
        {
            "model_key": spec.model_key,
            "model_identifier": spec.identifier,
            "model_name": spec.model_name,
            "display_name": spec.model_name.rsplit(".", 1)[0],
            "version_name": spec.version_name,
            "run_id": spec.run_id,
            "threshold": spec.threshold,
            "champion": spec.champion,
            "validation_pr_auc": spec.validation_pr_auc,
            "test_pr_auc": spec.test_pr_auc,
        }
        for spec in ModelRegistry.load(PROJECT_ROOT)
    ]
