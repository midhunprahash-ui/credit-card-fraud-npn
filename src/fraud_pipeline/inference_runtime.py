"""Backward-compatible selected-model runtime helpers.

New application code should use :mod:`fraud_pipeline.registry`,
:mod:`fraud_pipeline.model_adapters`, and :mod:`fraud_pipeline.inference_engine`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .model_adapters import load_model_adapter, verify_artifact_manifest
from .model_contracts import MODEL_DISPLAY_NAMES as DISPLAY_NAMES
from .model_contracts import MODEL_ORDER, VersionName
from .registry import ModelRegistry, ModelSpec


SelectedModelSpec = ModelSpec


def selected_model_specs(project_root: Path) -> list[ModelSpec]:
    return list(ModelRegistry.load(project_root))


def predict_with_selected_model(spec: ModelSpec, model_input: pd.DataFrame) -> np.ndarray:
    adapter = load_model_adapter(spec, verify_manifest=False)
    return np.asarray(
        [prediction.risk_score for prediction in adapter.predict(model_input)],
        dtype=np.float64,
    )


__all__ = [
    "DISPLAY_NAMES",
    "MODEL_ORDER",
    "ModelRegistry",
    "SelectedModelSpec",
    "VersionName",
    "predict_with_selected_model",
    "selected_model_specs",
    "verify_artifact_manifest",
]

