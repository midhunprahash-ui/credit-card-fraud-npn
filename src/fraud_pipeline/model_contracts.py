"""Canonical public identifiers for the eight approved model pipelines."""

from __future__ import annotations

from typing import Literal, cast


VersionName = Literal["V1", "V2"]
ModelKey = Literal[
    "logistic_regression",
    "lightgbm",
    "catboost",
    "neural_network",
]

MODEL_DISPLAY_NAMES: dict[ModelKey, str] = {
    "logistic_regression": "LogisticRegression",
    "lightgbm": "LightGBM",
    "catboost": "CatBoost",
    "neural_network": "NeuralNetwork",
}
MODEL_ORDER: tuple[ModelKey, ...] = tuple(MODEL_DISPLAY_NAMES)
VERSION_ORDER: tuple[VersionName, ...] = ("V1", "V2")
PROTECTED_INPUT_COLUMNS = frozenset({"isFraud"})
IDENTIFIER_COLUMN = "TransactionID"


def normalize_version(value: str) -> VersionName:
    normalized = value.upper()
    if normalized not in VERSION_ORDER:
        raise ValueError(f"Unsupported feature-engineering version: {value}")
    return cast(VersionName, normalized)


def model_identifier(model_key: ModelKey, version_name: VersionName) -> str:
    return f"{model_key}.{version_name.lower()}"


def model_name(model_key: ModelKey, version_name: VersionName) -> str:
    return f"{MODEL_DISPLAY_NAMES[model_key]}.{version_name}"
