"""Shared, row-level features and data checks used by all four models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TARGET_COLUMN = "isFraud"
ID_COLUMN = "TransactionID"
TIME_COLUMN = "TransactionDT"

# These columns contain codes, not quantities. A larger code has no numerical
# meaning, so models receive categorical/frequency/embedding representations.
IDENTIFIER_COLUMNS = ["card1", "card2", "card3", "card5", "addr1", "addr2"]


def reduce_memory_usage(frame: pd.DataFrame) -> pd.DataFrame:
    """Downcast a dataframe in place while preserving missing values."""
    for column in frame.select_dtypes(include=["float64"]).columns:
        frame[column] = pd.to_numeric(frame[column], downcast="float")
    for column in frame.select_dtypes(include=["int64"]).columns:
        frame[column] = pd.to_numeric(frame[column], downcast="integer")
    return frame


def _string_part(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series("MISSING", index=frame.index, dtype="string")
    return frame[column].astype("string").fillna("MISSING")


def add_shared_features(frame: pd.DataFrame, *, copy: bool = False) -> pd.DataFrame:
    """Add leakage-safe features available from the current transaction row.

    No mapping is learned here. Medians, frequencies, vocabularies and scalers
    belong to model-specific preprocessors and must be fitted on training only.
    """
    result = frame.copy() if copy else frame
    source_columns = [c for c in result.columns if c not in {TARGET_COLUMN, ID_COLUMN}]

    result["num_missing"] = result[source_columns].isna().sum(axis=1).astype("int16")

    family_prefixes = {
        "transaction_missing": ("TransactionAmt", "ProductCD", "dist1", "dist2"),
        "card_address_missing": tuple(IDENTIFIER_COLUMNS + ["card4", "card6"]),
        "identity_missing": tuple(c for c in result.columns if c.startswith("id_"))
        + ("DeviceType", "DeviceInfo"),
    }
    for feature, columns in family_prefixes.items():
        present = [c for c in columns if c in result]
        result[feature] = (
            result[present].isna().sum(axis=1).astype("int16") if present else 0
        )

    if "TransactionAmt" in result:
        amount = pd.to_numeric(result["TransactionAmt"], errors="coerce")
        result["transaction_amount_log1p"] = np.log1p(amount.clip(lower=0)).astype(
            "float32"
        )
        result["transaction_amount_cents"] = (
            np.round((amount - np.floor(amount)) * 100).astype("float32")
        )

    if TIME_COLUMN in result:
        seconds = pd.to_numeric(result[TIME_COLUMN], errors="coerce")
        result["transaction_relative_day"] = (seconds // 86_400).astype("float32")
        result["transaction_relative_week"] = (seconds // 604_800).astype("float32")
        # The dataset's calendar origin is undisclosed. This is a periodic phase,
        # not a claim that 0 means midnight in a real timezone.
        result["transaction_relative_hour_phase"] = (
            (seconds % 86_400) // 3_600
        ).astype("float32")

    result["card_1_2"] = (
        _string_part(result, "card1") + "__" + _string_part(result, "card2")
    ).astype("category")
    result["address_1_2"] = (
        _string_part(result, "addr1") + "__" + _string_part(result, "addr2")
    ).astype("category")
    result["email_pair"] = (
        _string_part(result, "P_emaildomain")
        + "__"
        + _string_part(result, "R_emaildomain")
    ).astype("category")

    return reduce_memory_usage(result)


def chronological_split(
    frame: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Sort by relative transaction time and return 70/15/15 partitions."""
    if TIME_COLUMN not in frame:
        raise KeyError(f"{TIME_COLUMN} is required for chronological splitting")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test partition")

    ordered = frame.sort_values([TIME_COLUMN, ID_COLUMN], kind="stable").reset_index(
        drop=True
    )
    train_end = int(len(ordered) * train_fraction)
    validation_end = int(len(ordered) * (train_fraction + validation_fraction))

    train = ordered.iloc[:train_end].copy()
    validation = ordered.iloc[train_end:validation_end].copy()
    test = ordered.iloc[validation_end:].copy()

    def summary(part: pd.DataFrame) -> dict[str, Any]:
        return {
            "rows": int(len(part)),
            "fraud_count": int(part[TARGET_COLUMN].sum()),
            "fraud_rate": float(part[TARGET_COLUMN].mean()),
            "transaction_dt_min": float(part[TIME_COLUMN].min()),
            "transaction_dt_max": float(part[TIME_COLUMN].max()),
        }

    metadata = {
        "method": "chronological",
        "sort_columns": [TIME_COLUMN, ID_COLUMN],
        "train_fraction": train_fraction,
        "validation_fraction": validation_fraction,
        "test_fraction": 1 - train_fraction - validation_fraction,
        "train": summary(train),
        "validation": summary(validation),
        "test": summary(test),
    }
    return train, validation, test, metadata


def cardinality_band(unique_count: int) -> str:
    if unique_count <= 20:
        return "low"
    if unique_count <= 100:
        return "medium"
    if unique_count <= 1_000:
        return "high"
    return "very_high"


def build_feature_audit(train: pd.DataFrame) -> pd.DataFrame:
    """Create an explainable model-by-model feature treatment table."""
    rows: list[dict[str, Any]] = []
    for column in train.columns:
        unique_count = int(train[column].nunique(dropna=True))
        is_identifier = column in IDENTIFIER_COLUMNS
        is_categorical = (
            is_identifier
            or isinstance(train[column].dtype, pd.CategoricalDtype)
            or train[column].dtype == "object"
            or pd.api.types.is_string_dtype(train[column])
        )
        role = (
            "target"
            if column == TARGET_COLUMN
            else "row_identifier"
            if column == ID_COLUMN
            else "identifier_code"
            if is_identifier
            else "categorical"
            if is_categorical
            else "numeric"
        )

        if role in {"target", "row_identifier"}:
            lr = lgbm = cat = nn = "exclude from model input"
        elif is_categorical:
            band = cardinality_band(unique_count)
            lr = "one-hot with rare grouping" if band in {"low", "medium"} else "frequency encode"
            lgbm = "native category" if band in {"low", "medium"} else "frequency encode"
            cat = "native categorical string"
            nn = "training vocabulary plus embedding"
        else:
            lr = "median impute, missing indicator, standardize"
            lgbm = "numeric; preserve NaN; no scaling"
            cat = "numeric; preserve NaN; no scaling"
            nn = "median impute, missing indicator, standardize"

        rows.append(
            {
                "feature": column,
                "dtype": str(train[column].dtype),
                "role": role,
                "missing_percent_train": round(float(train[column].isna().mean() * 100), 4),
                "unique_non_null_train": unique_count,
                "cardinality_band": cardinality_band(unique_count) if is_categorical else "not_applicable",
                "logistic_regression": lr,
                "lightgbm": lgbm,
                "catboost": cat,
                "neural_network": nn,
            }
        )
    return pd.DataFrame(rows)


def find_project_root(start: Path | None = None) -> Path:
    """Find the cloned repository whether a notebook opens at root or below it."""
    candidate = (start or Path.cwd()).resolve()
    for path in [candidate, *candidate.parents]:
        if (path / ".git").exists() and (path / "src").exists():
            return path
    raise FileNotFoundError("Open this notebook from inside the cloned project repository")
