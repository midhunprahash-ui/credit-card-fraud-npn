"""Common evaluation contract for comparable fraud experiments."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def select_operating_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    minimum_precision: float = 0.10,
) -> dict[str, float | str]:
    """Maximize recall subject to a precision floor; fall back to best F1."""
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    if len(thresholds) == 0:
        return {"threshold": 0.5, "method": "fallback_0.5", "precision": 0.0, "recall": 0.0}

    p = precision[:-1]
    r = recall[:-1]
    valid = np.flatnonzero(p >= minimum_precision)
    if len(valid):
        best = valid[np.argmax(r[valid])]
        method = f"maximum_recall_with_precision_at_least_{minimum_precision:.2f}"
    else:
        f1 = 2 * p * r / np.maximum(p + r, 1e-12)
        best = int(np.nanargmax(f1))
        method = "maximum_f1_fallback"
    return {
        "threshold": float(thresholds[best]),
        "method": method,
        "precision": float(p[best]),
        "recall": float(r[best]),
    }


def _capacity_metrics(
    y_true: np.ndarray, probabilities: np.ndarray, fraction: float
) -> dict[str, float | int]:
    count = max(1, int(np.ceil(len(y_true) * fraction)))
    top_indices = np.argsort(probabilities)[-count:]
    captured = int(np.asarray(y_true)[top_indices].sum())
    positives = int(np.asarray(y_true).sum())
    return {
        "reviewed_rows": count,
        "fraud_captured": captured,
        "recall": float(captured / positives) if positives else 0.0,
        "precision": float(captured / count),
    }


def evaluate_binary_classifier(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    probabilities = np.asarray(probabilities, dtype=float)
    predictions = (probabilities >= threshold).astype(np.int8)
    matrix = confusion_matrix(y, predictions, labels=[0, 1])
    return {
        "rows": int(len(y)),
        "fraud_rate": float(y.mean()),
        "threshold": float(threshold),
        "pr_auc": float(average_precision_score(y, probabilities)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "confusion_matrix": matrix.tolist(),
        "top_1_percent": _capacity_metrics(y, probabilities, 0.01),
        "top_5_percent": _capacity_metrics(y, probabilities, 0.05),
        "top_10_percent": _capacity_metrics(y, probabilities, 0.10),
    }
