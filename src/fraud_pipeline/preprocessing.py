"""Training-only preprocessors that are serializable for later API inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .common import IDENTIFIER_COLUMNS


def infer_feature_groups(
    frame: pd.DataFrame,
    *,
    low_cardinality_max: int = 100,
) -> dict[str, list[str]]:
    """Separate quantities from categorical labels and numeric identifier codes."""
    excluded = {"isFraud", "TransactionID"}
    categorical = [
        c
        for c in frame.columns
        if c not in excluded
        and (
            c in IDENTIFIER_COLUMNS
            or isinstance(frame[c].dtype, pd.CategoricalDtype)
            or frame[c].dtype == "object"
            or pd.api.types.is_string_dtype(frame[c])
        )
    ]
    numeric = [
        c
        for c in frame.columns
        if c not in excluded and c not in categorical and pd.api.types.is_numeric_dtype(frame[c])
    ]
    low = [c for c in categorical if frame[c].nunique(dropna=True) <= low_cardinality_max]
    high = [c for c in categorical if c not in low]
    return {"numeric": numeric, "low_cardinality": low, "high_cardinality": high}


class FrequencyEncoder(BaseEstimator, TransformerMixin):
    """Compact training-only encoding for high-cardinality labels."""

    def __init__(self) -> None:
        self.columns_: list[str] = []
        self.frequency_maps_: dict[str, dict[str, float]] = {}

    @staticmethod
    def _clean(series: pd.Series) -> pd.Series:
        return series.astype("string").fillna("MISSING")

    def fit(self, X: pd.DataFrame, y: Any = None) -> "FrequencyEncoder":
        frame = pd.DataFrame(X).copy()
        self.columns_ = list(frame.columns.astype(str))
        frame.columns = self.columns_
        self.frequency_maps_ = {}
        for column in self.columns_:
            values = self._clean(frame[column])
            self.frequency_maps_[column] = values.value_counts(normalize=True).to_dict()
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        frame = pd.DataFrame(X).copy()
        frame.columns = self.columns_
        encoded = np.zeros((len(frame), len(self.columns_)), dtype=np.float32)
        for index, column in enumerate(self.columns_):
            encoded[:, index] = (
                self._clean(frame[column])
                .map(self.frequency_maps_[column])
                .fillna(0.0)
                .astype("float32")
            )
        return encoded

    def get_feature_names_out(self, input_features: Any = None) -> np.ndarray:
        return np.asarray([f"{c}__frequency" for c in self.columns_], dtype=object)


class CategoricalStringCleaner(BaseEstimator, TransformerMixin):
    """Convert mixed numeric/text category columns into uniform strings."""

    def __init__(self) -> None:
        self.columns_: list[str] = []

    def fit(self, X: pd.DataFrame, y: Any = None) -> "CategoricalStringCleaner":
        frame = pd.DataFrame(X)
        self.columns_ = [str(column) for column in frame.columns]
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        frame = pd.DataFrame(X).copy()
        frame.columns = self.columns_
        cleaned = pd.DataFrame(index=frame.index)
        for column in self.columns_:
            cleaned[column] = frame[column].astype("string").fillna("MISSING").astype(str)
        return cleaned.to_numpy(dtype=object)

    def get_feature_names_out(self, input_features: Any = None) -> np.ndarray:
        return np.asarray(self.columns_, dtype=object)


def build_logistic_preprocessor(
    groups: dict[str, list[str]], *, rare_min_count: int = 20
) -> ColumnTransformer:
    """Build a sparse, memory-conscious Logistic Regression transformation."""
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler(with_mean=False)),
        ]
    )
    low_category_pipeline = Pipeline(
        steps=[
            ("string_cleaner", CategoricalStringCleaner()),
            (
                "one_hot",
                OneHotEncoder(
                    handle_unknown="infrequent_if_exist",
                    min_frequency=rare_min_count,
                    sparse_output=True,
                    dtype=np.float32,
                ),
            ),
        ]
    )
    high_category_pipeline = Pipeline(
        steps=[
            ("frequency", FrequencyEncoder()),
            ("scaler", StandardScaler(with_mean=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, groups["numeric"]),
            ("low_category", low_category_pipeline, groups["low_cardinality"]),
            ("high_category", high_category_pipeline, groups["high_cardinality"]),
        ],
        remainder="drop",
        sparse_threshold=0.2,
        verbose_feature_names_out=True,
    )


@dataclass
class LightGBMPreprocessor:
    """Native low-cardinality categories plus compact high-card frequencies."""

    low_cardinality_max: int = 100
    rare_min_count: int = 20
    groups: dict[str, list[str]] = field(default_factory=dict)
    category_levels: dict[str, list[str]] = field(default_factory=dict)
    kept_categories: dict[str, set[str]] = field(default_factory=dict)
    training_categories: dict[str, set[str]] = field(default_factory=dict)
    frequency_maps: dict[str, dict[str, float]] = field(default_factory=dict)

    @staticmethod
    def _clean(series: pd.Series) -> pd.Series:
        return series.astype("string").fillna("MISSING")

    def fit(self, frame: pd.DataFrame) -> "LightGBMPreprocessor":
        self.groups = infer_feature_groups(
            frame, low_cardinality_max=self.low_cardinality_max
        )
        self.category_levels = {}
        self.kept_categories = {}
        self.training_categories = {}
        for column in self.groups["low_cardinality"]:
            values = self._clean(frame[column])
            counts = values.value_counts()
            kept = set(counts[counts >= self.rare_min_count].index)
            grouped = values.where(values.isin(kept), "OTHER")
            levels = sorted(set(grouped.unique()) | {"MISSING", "OTHER", "UNKNOWN"})
            self.category_levels[column] = levels
            self.kept_categories[column] = {str(value) for value in kept}
            self.training_categories[column] = set(values.unique().astype(str))

        self.frequency_maps = {}
        for column in self.groups["high_cardinality"]:
            values = self._clean(frame[column])
            self.frequency_maps[column] = values.value_counts(normalize=True).to_dict()
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        output_columns: dict[str, pd.Series] = {}
        for column in self.groups["numeric"]:
            output_columns[column] = pd.to_numeric(frame[column], errors="coerce").astype("float32")
        for column in self.groups["low_cardinality"]:
            values = self._clean(frame[column])
            levels = self.category_levels[column]
            kept = self.kept_categories[column]
            seen = self.training_categories[column]
            is_seen = values.isin(seen)
            is_kept = values.isin(kept | {"MISSING"})
            values = values.where(is_kept, "OTHER")
            values = values.where(is_seen, "UNKNOWN")
            output_columns[column] = pd.Series(
                pd.Categorical(values, categories=levels), index=frame.index
            )
        for column in self.groups["high_cardinality"]:
            output_columns[f"{column}__frequency"] = (
                self._clean(frame[column])
                .map(self.frequency_maps[column])
                .fillna(0.0)
                .astype("float32")
            )
        return pd.DataFrame(output_columns, index=frame.index)

    @property
    def categorical_features(self) -> list[str]:
        return list(self.groups.get("low_cardinality", []))


@dataclass
class CatBoostPreprocessor:
    """Preserve categorical identity while enforcing a stable schema."""

    groups: dict[str, list[str]] = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=list)

    def fit(self, frame: pd.DataFrame) -> "CatBoostPreprocessor":
        self.groups = infer_feature_groups(frame, low_cardinality_max=100)
        self.feature_columns = (
            self.groups["numeric"]
            + self.groups["low_cardinality"]
            + self.groups["high_cardinality"]
        )
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        output_columns: dict[str, pd.Series] = {}
        categorical = set(
            self.groups.get("low_cardinality", [])
            + self.groups.get("high_cardinality", [])
        )
        for column in self.feature_columns:
            if column in categorical:
                output_columns[column] = frame[column].astype("string").fillna("MISSING").astype(str)
            else:
                output_columns[column] = pd.to_numeric(frame[column], errors="coerce").astype("float32")
        return pd.DataFrame(output_columns, index=frame.index)

    @property
    def categorical_features(self) -> list[str]:
        return self.groups.get("low_cardinality", []) + self.groups.get(
            "high_cardinality", []
        )


@dataclass
class NeuralTabularPreprocessor:
    """Median/scale numerical values and map categories to embedding IDs."""

    rare_min_count: int = 20
    groups: dict[str, list[str]] = field(default_factory=dict)
    numeric_medians: dict[str, float] = field(default_factory=dict)
    numeric_means: dict[str, float] = field(default_factory=dict)
    numeric_stds: dict[str, float] = field(default_factory=dict)
    vocabularies: dict[str, dict[str, int]] = field(default_factory=dict)
    training_categories: dict[str, set[str]] = field(default_factory=dict)

    @staticmethod
    def _clean(series: pd.Series) -> pd.Series:
        return series.astype("string").fillna("MISSING")

    def fit(self, frame: pd.DataFrame) -> "NeuralTabularPreprocessor":
        self.groups = infer_feature_groups(frame, low_cardinality_max=100)
        self.numeric_medians = {}
        self.numeric_means = {}
        self.numeric_stds = {}
        for column in self.groups["numeric"]:
            values = pd.to_numeric(frame[column], errors="coerce").astype("float32")
            median = float(values.median()) if values.notna().any() else 0.0
            filled = values.fillna(median)
            mean = float(filled.mean())
            std = float(filled.std())
            self.numeric_medians[column] = median
            self.numeric_means[column] = mean
            self.numeric_stds[column] = std if np.isfinite(std) and std > 1e-8 else 1.0

        self.vocabularies = {}
        self.training_categories = {}
        categorical = self.groups["low_cardinality"] + self.groups["high_cardinality"]
        for column in categorical:
            values = self._clean(frame[column])
            counts = values.value_counts()
            kept = sorted(counts[counts >= self.rare_min_count].index.astype(str))
            vocabulary = {"MISSING": 0, "UNKNOWN": 1, "OTHER": 2}
            for value in kept:
                if value not in vocabulary:
                    vocabulary[value] = len(vocabulary)
            self.vocabularies[column] = vocabulary
            self.training_categories[column] = set(values.unique().astype(str))
        return self

    def transform(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        numeric_columns = self.groups["numeric"]
        numeric = np.empty((len(frame), len(numeric_columns) * 2), dtype=np.float32)
        for index, column in enumerate(numeric_columns):
            values = pd.to_numeric(frame[column], errors="coerce").astype("float32")
            missing = values.isna().to_numpy(dtype=np.float32)
            filled = values.fillna(self.numeric_medians[column]).to_numpy(dtype=np.float32)
            scaled = (filled - self.numeric_means[column]) / self.numeric_stds[column]
            numeric[:, index] = np.nan_to_num(scaled, nan=0.0, posinf=10.0, neginf=-10.0)
            numeric[:, len(numeric_columns) + index] = missing

        categorical_columns = self.categorical_columns
        categorical = np.empty((len(frame), len(categorical_columns)), dtype=np.int64)
        for index, column in enumerate(categorical_columns):
            vocabulary = self.vocabularies[column]
            values = self._clean(frame[column])
            training_values = self.training_categories[column]
            mapped = values.map(vocabulary)
            known_rare = mapped.isna() & values.isin(training_values)
            mapped = mapped.mask(known_rare, vocabulary["OTHER"])
            categorical[:, index] = mapped.fillna(vocabulary["UNKNOWN"]).to_numpy(dtype=np.int64)
        return numeric, categorical

    @property
    def categorical_columns(self) -> list[str]:
        return self.groups.get("low_cardinality", []) + self.groups.get(
            "high_cardinality", []
        )

    @property
    def numeric_output_size(self) -> int:
        return len(self.groups.get("numeric", [])) * 2

    @property
    def cardinalities(self) -> list[int]:
        return [len(self.vocabularies[c]) for c in self.categorical_columns]
