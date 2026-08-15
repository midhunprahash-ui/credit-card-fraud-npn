"""Loaded-model adapters with one prediction contract across all approaches."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .artifacts import sha256_file
from .registry import ModelSpec


@dataclass(frozen=True)
class ModelPrediction:
    model_identifier: str
    model_name: str
    model_version: str
    run_id: str
    risk_score: float
    threshold: float
    decision: bool
    latency_ms: float
    champion: bool
    processing_status: str = "completed"


def verify_artifact_manifest(directory: Path) -> dict[str, int]:
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Artifact manifest is missing: {manifest_path}")
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


class ModelAdapter(ABC):
    def __init__(self, spec: ModelSpec) -> None:
        self.spec = spec
        self.feature_columns = _feature_columns(spec.artifact_directory / "feature_schema.json")

    def predict(self, frame: pd.DataFrame) -> list[ModelPrediction]:
        aligned = self._align(frame)
        started = time.perf_counter()
        scores = np.asarray(self._predict_scores(aligned), dtype=np.float64).reshape(-1)
        elapsed_ms = (time.perf_counter() - started) * 1_000
        if len(scores) != len(frame):
            raise ValueError(f"{self.spec.identifier} returned an unexpected score count")
        if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise ValueError(f"{self.spec.identifier} returned an invalid fraud-risk score")
        per_row_latency = elapsed_ms / max(len(scores), 1)
        return [
            ModelPrediction(
                model_identifier=self.spec.identifier,
                model_name=self.spec.model_name,
                model_version=self.spec.version_name,
                run_id=self.spec.run_id,
                risk_score=float(score),
                threshold=self.spec.threshold,
                decision=bool(score >= self.spec.threshold),
                latency_ms=per_row_latency,
                champion=self.spec.champion,
            )
            for score in scores
        ]

    def _align(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = sorted(set(self.feature_columns) - set(frame))
        if missing:
            raise ValueError(
                f"Feature schema mismatch for {self.spec.identifier}; "
                f"missing={missing}"
            )
        if "isFraud" in frame or "TransactionID" in frame:
            raise ValueError("Protected target or identifier reached a model adapter")
        return frame.loc[:, self.feature_columns]

    @abstractmethod
    def _predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError


class LogisticRegressionAdapter(ModelAdapter):
    def __init__(self, spec: ModelSpec) -> None:
        import joblib

        super().__init__(spec)
        self.model = joblib.load(spec.artifact_directory / spec.files["model_file"])

    def _predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(frame)[:, 1]


class LightGBMAdapter(ModelAdapter):
    def __init__(self, spec: ModelSpec) -> None:
        import joblib
        import lightgbm as lgb

        super().__init__(spec)
        self.preprocessor = joblib.load(
            spec.artifact_directory / spec.files["preprocessor_file"]
        )
        self.model = lgb.Booster(
            model_file=str(spec.artifact_directory / spec.files["model_file"])
        )

    def _predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self.preprocessor.transform(frame))


class CatBoostAdapter(ModelAdapter):
    def __init__(self, spec: ModelSpec) -> None:
        import joblib
        from catboost import CatBoostClassifier

        super().__init__(spec)
        self.preprocessor = joblib.load(
            spec.artifact_directory / spec.files["preprocessor_file"]
        )
        self.model = CatBoostClassifier()
        self.model.load_model(str(spec.artifact_directory / spec.files["model_file"]))

    def _predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        from catboost import Pool

        transformed = self.preprocessor.transform(frame)
        pool = Pool(transformed, cat_features=self.preprocessor.categorical_features)
        return self.model.predict_proba(pool)[:, 1]


class NeuralNetworkAdapter(ModelAdapter):
    def __init__(self, spec: ModelSpec) -> None:
        import joblib
        import torch

        from .neural import network_from_config
        from .neural_v2 import network_v2_from_config

        super().__init__(spec)
        self.preprocessor = joblib.load(
            spec.artifact_directory / spec.files["preprocessor_file"]
        )
        checkpoint = torch.load(
            spec.artifact_directory / spec.files["model_file"],
            map_location="cpu",
            weights_only=True,
        )
        factory = network_from_config if spec.version_name == "V1" else network_v2_from_config
        self.model = factory(checkpoint["model_config"])
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

    def _predict_scores(self, frame: pd.DataFrame) -> np.ndarray:
        import torch

        numeric, categorical = self.preprocessor.transform(frame)
        with torch.inference_mode():
            scores = torch.sigmoid(
                self.model(torch.from_numpy(numeric), torch.from_numpy(categorical))
            )
        return scores.detach().cpu().numpy()


def load_model_adapter(spec: ModelSpec, *, verify_manifest: bool = True) -> ModelAdapter:
    """Verify and load exactly one selected model bundle."""
    if verify_manifest:
        verify_artifact_manifest(spec.artifact_directory)
    _verify_threshold(spec)
    adapters: dict[str, type[ModelAdapter]] = {
        "logistic_regression": LogisticRegressionAdapter,
        "lightgbm": LightGBMAdapter,
        "catboost": CatBoostAdapter,
        "neural_network": NeuralNetworkAdapter,
    }
    return adapters[spec.model_key](spec)


def _feature_columns(path: Path) -> tuple[str, ...]:
    schema = json.loads(path.read_text())
    if "feature_columns" in schema:
        columns = list(schema["feature_columns"])
    else:
        groups = schema.get("groups", {})
        columns = [
            column
            for group in ("numeric", "low_cardinality", "high_cardinality")
            for column in groups.get(group, [])
        ]
    if not columns or len(columns) != len(set(columns)):
        raise ValueError(f"Invalid feature schema: {path}")
    if "isFraud" in columns or "TransactionID" in columns:
        raise ValueError(f"Protected column declared in feature schema: {path}")
    return tuple(columns)


def _verify_threshold(spec: ModelSpec) -> None:
    path = spec.artifact_directory / "threshold.json"
    artifact_threshold = float(json.loads(path.read_text())["threshold"])
    if not np.isclose(artifact_threshold, spec.threshold, rtol=0, atol=1e-15):
        raise ValueError(f"Registry/artifact threshold mismatch for {spec.identifier}")
