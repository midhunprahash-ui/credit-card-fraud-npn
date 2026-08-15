"""Expose the canonical public catalog for the eight approved model runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.fraud_pipeline.model_contracts import VersionName
from src.fraud_pipeline.registry import ModelRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_model_catalog() -> list[dict[str, Any]]:
    catalog = []
    for spec in ModelRegistry.load(PROJECT_ROOT):
        metrics = _read_json(spec.artifact_directory / "metrics.json")
        training = _read_json(spec.artifact_directory / "training_config.json")
        top_features = _read_top_features(spec.artifact_directory)
        test_metrics = metrics.get("test", {})
        test_rows = test_metrics.get("rows")
        prediction_seconds = training.get("test_prediction_seconds")
        catalog.append(
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
                "metrics": {
                    "validation": metrics.get("validation"),
                    "test": test_metrics or None,
                    "training_seconds": training.get("training_seconds"),
                    "prediction_latency_ms": (
                        float(prediction_seconds) * 1_000 / int(test_rows)
                        if prediction_seconds is not None and test_rows
                        else None
                    ),
                },
                "feature_importance_available": bool(top_features),
                "top_features": top_features,
            }
        )
    return catalog


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    document = json.loads(path.read_text())
    return document if isinstance(document, dict) else {}


def _read_top_features(directory: Path) -> list[dict[str, Any]]:
    candidates = (
        (directory / "feature_importance.csv", ("importance", "gain"), "importance"),
        (directory / "top_coefficients.csv", ("absolute_coefficient",), "coefficient"),
    )
    for path, value_columns, kind in candidates:
        if not path.is_file():
            continue
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        output = []
        for row in rows[:8]:
            value_column = next(
                (column for column in value_columns if row.get(column) not in {None, ""}),
                None,
            )
            if value_column is None or not row.get("feature"):
                continue
            output.append(
                {
                    "feature": row["feature"],
                    "value": float(row[value_column]),
                    "kind": kind,
                }
            )
        return output
    return []
