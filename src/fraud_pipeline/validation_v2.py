"""Version 2 time validation and ensemble helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def expanding_time_folds(row_count: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return three expanding chronological folds within the first 85%.

    Percentages refer to the full labelled development data. The latest 15% is
    deliberately absent and remains the final test period.
    """
    if row_count < 100:
        raise ValueError("At least 100 ordered rows are required for time folds")
    boundaries = ((0.45, 0.55), (0.60, 0.70), (0.70, 0.85))
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    for train_end_fraction, validation_end_fraction in boundaries:
        train_end = int(row_count * train_end_fraction / 0.85)
        validation_end = int(row_count * validation_end_fraction / 0.85)
        folds.append(
            (
                np.arange(0, train_end, dtype=np.int64),
                np.arange(train_end, validation_end, dtype=np.int64),
            )
        )
    return folds


def positive_weight(y: Iterable[int], mode: str) -> float:
    values = np.asarray(list(y), dtype=np.int8)
    negative, positive = np.bincount(values, minlength=2)
    if positive == 0:
        raise ValueError("Training partition contains no fraud examples")
    ratio = float(negative / positive)
    if mode == "none":
        return 1.0
    if mode == "sqrt_balanced":
        return float(np.sqrt(ratio))
    if mode == "balanced":
        return ratio
    raise ValueError(f"Unknown class-weight mode: {mode}")


def logit(probabilities: np.ndarray, epsilon: float = 1e-6) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), epsilon, 1 - epsilon)
    return np.log(clipped / (1 - clipped))


def fit_two_model_logit_blend(
    y_true: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    *,
    grid_size: int = 101,
) -> dict[str, float]:
    """Choose the first-model weight using validation PR-AUC only."""
    best = {"first_weight": 0.5, "second_weight": 0.5, "validation_pr_auc": -1.0}
    first_logit, second_logit = logit(first), logit(second)
    for weight in np.linspace(0.0, 1.0, grid_size):
        score = weight * first_logit + (1 - weight) * second_logit
        metric = float(average_precision_score(y_true, score))
        if metric > best["validation_pr_auc"]:
            best = {
                "first_weight": float(weight),
                "second_weight": float(1 - weight),
                "validation_pr_auc": metric,
            }
    return best


def apply_two_model_logit_blend(
    first: np.ndarray, second: np.ndarray, first_weight: float
) -> np.ndarray:
    """Return a monotonic 0–1 consensus score from weighted model logits."""
    blended_logit = first_weight * logit(first) + (1 - first_weight) * logit(second)
    return 1.0 / (1.0 + np.exp(-np.clip(blended_logit, -40, 40)))


def best_complete_run(artifact_root: Path, model_key: str) -> Path:
    """Select the full-data run with the best saved validation PR-AUC."""
    candidates: list[tuple[float, Path]] = []
    for run in sorted((artifact_root / model_key).glob("*")):
        metrics_path = run / "metrics.json"
        config_path = run / "training_config.json"
        if not metrics_path.exists() or not config_path.exists():
            continue
        metrics = json.loads(metrics_path.read_text())
        config = json.loads(config_path.read_text())
        if config.get("fast_run", False):
            continue
        candidates.append((float(metrics["validation"]["pr_auc"]), run))
    if not candidates:
        raise FileNotFoundError(f"No complete full-data run found for {model_key}")
    return max(candidates, key=lambda item: item[0])[1]


def merge_prediction_files(paths: dict[str, Path], split: str) -> pd.DataFrame:
    """Join saved predictions by TransactionID with strict label agreement."""
    merged: pd.DataFrame | None = None
    for model_key, run in paths.items():
        current = pd.read_parquet(run / f"{split}_predictions.parquet")
        current = current[["TransactionID", "isFraud", "probability"]].rename(
            columns={"probability": model_key}
        )
        if merged is None:
            merged = current
        else:
            merged = merged.merge(
                current[["TransactionID", "isFraud", model_key]],
                on="TransactionID",
                how="inner",
                validate="one_to_one",
                suffixes=("", "_check"),
            )
            check = merged.pop("isFraud_check")
            if not np.array_equal(merged["isFraud"].to_numpy(), check.to_numpy()):
                raise ValueError(f"Label mismatch while joining {model_key} {split} predictions")
    if merged is None:
        raise ValueError("At least one prediction path is required")
    return merged.sort_values("TransactionID").reset_index(drop=True)
