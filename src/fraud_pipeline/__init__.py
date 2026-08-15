"""Reusable training and inference utilities for the fraud project."""

from .common import (
    IDENTIFIER_COLUMNS,
    TARGET_COLUMN,
    add_shared_features,
    build_feature_audit,
    chronological_split,
    reduce_memory_usage,
)
from .evaluation import evaluate_binary_classifier, select_operating_threshold
from .preprocessing import (
    CatBoostPreprocessor,
    FrequencyEncoder,
    LightGBMPreprocessor,
    NeuralTabularPreprocessor,
    build_logistic_preprocessor,
    infer_feature_groups,
)
from .model_contracts import MODEL_DISPLAY_NAMES, MODEL_ORDER, VERSION_ORDER
from .model_manager import ModelLoadError, ModelManager
from .registry import ModelRegistry, ModelSpec

__all__ = [
    "IDENTIFIER_COLUMNS",
    "TARGET_COLUMN",
    "add_shared_features",
    "build_feature_audit",
    "chronological_split",
    "reduce_memory_usage",
    "evaluate_binary_classifier",
    "select_operating_threshold",
    "CatBoostPreprocessor",
    "FrequencyEncoder",
    "LightGBMPreprocessor",
    "NeuralTabularPreprocessor",
    "build_logistic_preprocessor",
    "infer_feature_groups",
    "MODEL_DISPLAY_NAMES",
    "MODEL_ORDER",
    "VERSION_ORDER",
    "ModelRegistry",
    "ModelSpec",
    "ModelLoadError",
    "ModelManager",
]
