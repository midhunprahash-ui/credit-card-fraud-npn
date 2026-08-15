"""Leakage-safe Version 2 behavioural features for fraud modelling.

The batch transformer is intentionally target-free and chronological: a row may
only use transactions that appeared before it. This mirrors a real-time feature
store instead of computing statistics from future rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .common import ID_COLUMN, TARGET_COLUMN, TIME_COLUMN, add_shared_features


D_NORMALIZATION_COLUMNS = ("D1", "D2", "D4", "D10", "D15")
COUNT_TIME_KEYS = ("uid_proxy", "card_address_key", "card1_key", "device_key")
AMOUNT_KEYS = ("uid_proxy", "card_address_key")
UID_UNIQUE_VALUE_COLUMNS = (
    "P_emaildomain",
    "DeviceInfo",
    "transaction_amount_cents",
)
UID_D_STAT_COLUMNS = ("D4_normalized", "D10_normalized", "D15_normalized")
REFERENCE_SOURCE_COLUMNS = (
    ID_COLUMN,
    TIME_COLUMN,
    "TransactionAmt",
    "card1",
    "addr1",
    "D1",
    "D4",
    "D10",
    "D15",
    "P_emaildomain",
    "DeviceType",
    "DeviceInfo",
)


def _clean_text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("MISSING")


def _part(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series("MISSING", index=frame.index, dtype="string")
    return _clean_text(frame[column])


def _family(series: pd.Series) -> pd.Series:
    """Keep a stable browser/OS family without memorising full version strings."""
    cleaned = _clean_text(series).str.lower().str.strip()
    family = cleaned.str.extract(r"^([a-z][a-z0-9_+.-]*)", expand=False)
    return family.fillna("MISSING").astype("category")


def add_v2_row_features(frame: pd.DataFrame, *, copy: bool = False) -> pd.DataFrame:
    """Add deterministic Version 2 features available in the current row."""
    result = frame.copy() if copy else frame
    if "num_missing" not in result:
        result = add_shared_features(result, copy=False)
    # JSON-built single-row frames can have hundreds of tiny dtype blocks after
    # downcasting. Consolidating small inference batches prevents repeated
    # inserts from degrading latency without copying the full training dataset.
    if len(result) <= 1_000:
        result = result.copy()

    # The shared memory reducer may downcast small samples to int16/int32.
    # Promote before modulo/division so constants such as 86,400 cannot overflow.
    seconds = pd.to_numeric(result[TIME_COLUMN], errors="coerce").astype("float64")
    day = seconds / 86_400.0
    result["transaction_day_continuous"] = day.astype("float32")
    result["transaction_week_sin"] = np.sin(2 * np.pi * day / 7).astype("float32")
    result["transaction_week_cos"] = np.cos(2 * np.pi * day / 7).astype("float32")
    hour = (seconds % 86_400) / 3_600.0
    result["transaction_hour_sin"] = np.sin(2 * np.pi * hour / 24).astype("float32")
    result["transaction_hour_cos"] = np.cos(2 * np.pi * hour / 24).astype("float32")

    for column in D_NORMALIZATION_COLUMNS:
        if column in result:
            values = pd.to_numeric(result[column], errors="coerce")
            result[f"{column}_normalized"] = (day - values).astype("float32")

    amount = pd.to_numeric(result.get("TransactionAmt"), errors="coerce")
    result["transaction_amount_dollars"] = np.floor(amount).astype("float32")

    result["card1_key"] = _part(result, "card1").astype("category")
    result["card_address_key"] = (
        _part(result, "card1") + "__" + _part(result, "addr1")
    ).astype("category")
    result["card_address_email_key"] = (
        _part(result, "card1")
        + "__"
        + _part(result, "addr1")
        + "__"
        + _part(result, "P_emaildomain")
    ).astype("category")

    d1_anchor = result.get("D1_normalized", pd.Series(np.nan, index=result.index))
    d1_anchor = pd.to_numeric(d1_anchor, errors="coerce").round().astype("Int64").astype("string")
    result["uid_proxy"] = (
        _part(result, "card1")
        + "__"
        + _part(result, "addr1")
        + "__"
        + d1_anchor.fillna("MISSING")
    ).astype("category")
    result["device_key"] = (
        _part(result, "DeviceType") + "__" + _part(result, "DeviceInfo")
    ).astype("category")

    if "id_30" in result:
        result["operating_system_family"] = _family(result["id_30"])
    if "id_31" in result:
        result["browser_family"] = _family(result["id_31"])
    return result


def _prior_numeric_stats(
    frame: pd.DataFrame, key: str, value: str, prefix: str
) -> dict[str, pd.Series]:
    numeric = pd.to_numeric(frame[value], errors="coerce").astype("float64")
    valid = numeric.notna().astype("int64")
    filled = numeric.fillna(0.0)
    group = frame[key]

    prior_n = valid.groupby(group, observed=True).cumsum() - valid
    prior_sum = filled.groupby(group, observed=True).cumsum() - filled
    squared = filled * filled
    prior_sum_sq = squared.groupby(group, observed=True).cumsum() - squared
    denominator = prior_n.replace(0, np.nan)
    mean = prior_sum / denominator
    variance = (prior_sum_sq / denominator - mean * mean).clip(lower=0)
    std = np.sqrt(variance).where(prior_n >= 2)
    return {
        f"{prefix}_prior_numeric_count": prior_n.astype("int32"),
        f"{prefix}_prior_mean": mean.astype("float32"),
        f"{prefix}_prior_std": std.astype("float32"),
    }


def _prior_unique_count(frame: pd.DataFrame, key: str, value: str) -> pd.Series:
    safe_value = _clean_text(frame[value]) if value in frame else pd.Series(
        "MISSING", index=frame.index, dtype="string"
    )
    pairs = pd.DataFrame({"key": _clean_text(frame[key]), "value": safe_value})
    is_new = (~pairs.duplicated(["key", "value"])).astype("int32")
    return (is_new.groupby(pairs["key"], observed=True).cumsum() - is_new).astype("int32")


def add_causal_behavioral_features(
    frame: pd.DataFrame, *, copy: bool = False
) -> pd.DataFrame:
    """Add target-free historical features using earlier rows only.

    Input can contain train, validation and test periods together. Sorting by
    TransactionDT makes every cumulative statistic prequential: validation and
    test rows may use earlier observed transaction attributes but never labels or
    later rows.
    """
    result = add_v2_row_features(frame, copy=copy)
    original_index_name = result.index.name
    result = result.sort_values([TIME_COLUMN, ID_COLUMN], kind="stable").reset_index(drop=True)

    time = pd.to_numeric(result[TIME_COLUMN], errors="coerce").astype("float64")
    for key in COUNT_TIME_KEYS:
        group = result.groupby(key, observed=True, sort=False)
        result[f"{key}_prior_count"] = group.cumcount().astype("int32")
        previous = group[TIME_COLUMN].shift(1)
        result[f"{key}_seconds_since_previous"] = (time - previous).astype("float32")

    amount = pd.to_numeric(result["TransactionAmt"], errors="coerce")
    for key in AMOUNT_KEYS:
        prefix = f"{key}_amount"
        statistics = _prior_numeric_stats(result, key, "TransactionAmt", prefix)
        for name, values in statistics.items():
            result[name] = values
        mean = result[f"{prefix}_prior_mean"]
        std = result[f"{prefix}_prior_std"]
        result[f"{prefix}_difference"] = (amount - mean).astype("float32")
        result[f"{prefix}_ratio"] = (amount / mean.replace(0, np.nan)).astype("float32")
        result[f"{prefix}_zscore"] = ((amount - mean) / std.replace(0, np.nan)).astype("float32")

    for column in UID_D_STAT_COLUMNS:
        if column in result:
            prefix = f"uid_proxy_{column}"
            for name, values in _prior_numeric_stats(result, "uid_proxy", column, prefix).items():
                result[name] = values

    for column in UID_UNIQUE_VALUE_COLUMNS:
        if column in result:
            result[f"uid_proxy_{column}_prior_nunique"] = _prior_unique_count(
                result, "uid_proxy", column
            )

    result.index.name = original_index_name
    return result


@dataclass
class BehavioralFeatureContract:
    """Serializable description required by the future online feature store."""

    version: str = "2.0"
    ordering: tuple[str, str] = (TIME_COLUMN, ID_COLUMN)
    d_normalization_columns: tuple[str, ...] = D_NORMALIZATION_COLUMNS
    count_time_keys: tuple[str, ...] = COUNT_TIME_KEYS
    amount_keys: tuple[str, ...] = AMOUNT_KEYS
    uid_unique_value_columns: tuple[str, ...] = UID_UNIQUE_VALUE_COLUMNS
    uid_d_stat_columns: tuple[str, ...] = UID_D_STAT_COLUMNS
    uses_target: bool = False
    history_rule: str = "strictly_earlier_transactions_only"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "ordering": list(self.ordering),
            "d_normalization_columns": list(self.d_normalization_columns),
            "count_time_keys": list(self.count_time_keys),
            "amount_keys": list(self.amount_keys),
            "uid_unique_value_columns": list(self.uid_unique_value_columns),
            "uid_d_stat_columns": list(self.uid_d_stat_columns),
            "uses_target": self.uses_target,
            "history_rule": self.history_rule,
            "metadata": self.metadata,
        }


def v2_model_columns(frame: pd.DataFrame) -> list[str]:
    """Return model inputs while excluding labels and the row identifier."""
    return [column for column in frame.columns if column not in {TARGET_COLUMN, ID_COLUMN}]


def build_behavioral_reference(frame: pd.DataFrame) -> dict[str, Any]:
    """Build compact label-free lookup state for single-row API inference.

    The hackathon API can use this frozen state. A production bank would keep the
    same statistics in an online feature store and update them after each event.
    """
    history = add_v2_row_features(frame, copy=True).sort_values(
        [TIME_COLUMN, ID_COLUMN], kind="stable"
    )
    if history.empty:
        raise ValueError("Behavioral reference history cannot be empty")
    last_history_row = history.iloc[-1]
    contract = BehavioralFeatureContract(
        metadata={
            "history_end_transaction_dt": float(last_history_row[TIME_COLUMN]),
            "history_end_transaction_id": int(last_history_row[ID_COLUMN]),
            "history_row_count": int(len(history)),
        }
    ).to_dict()
    reference: dict[str, Any] = {
        "contract": contract,
        "counts": {},
        "last_time": {},
        "numeric": {},
        "nunique": {},
        "unique_hashes": {},
        "online_unique_hashes": {},
    }
    for key in COUNT_TIME_KEYS:
        reference["counts"][key] = history[key].value_counts(dropna=False).to_dict()
        reference["last_time"][key] = (
            history.groupby(key, observed=True)[TIME_COLUMN].max().to_dict()
        )

    numeric_pairs = [(key, "TransactionAmt", f"{key}_amount") for key in AMOUNT_KEYS]
    numeric_pairs.extend(
        ("uid_proxy", column, f"uid_proxy_{column}")
        for column in UID_D_STAT_COLUMNS
        if column in history
    )
    for key, value, prefix in numeric_pairs:
        numeric = pd.to_numeric(history[value], errors="coerce")
        summary = (
            pd.DataFrame({"key": history[key], "value": numeric})
            .groupby("key", observed=True)["value"]
            .agg(
                count="count",
                mean="mean",
                # Training's causal implementation uses E[x^2] - E[x]^2,
                # which is population standard deviation (ddof=0).
                std=lambda values: (
                    values.std(ddof=0) if values.count() >= 2 else np.nan
                ),
            )
        )
        reference["numeric"][prefix] = {
            "count": summary["count"].astype("int32").to_dict(),
            "mean": summary["mean"].astype("float32").to_dict(),
            "std": summary["std"].astype("float32").to_dict(),
        }

    for column in UID_UNIQUE_VALUE_COLUMNS:
        if column in history:
            keys = _clean_text(history["uid_proxy"])
            values = _clean_text(history[column])
            reference["nunique"][column] = (
                values.groupby(keys, observed=True).nunique().to_dict()
            )
            pair_hashes = _stable_pair_hashes(keys, values)
            reference["unique_hashes"][column] = np.unique(pair_hashes)
            reference["online_unique_hashes"][column] = set()
    return reference


def apply_behavioral_reference(
    frame: pd.DataFrame, reference: dict[str, Any], *, copy: bool = False
) -> pd.DataFrame:
    """Apply frozen historical lookups to new transactions without target data."""
    result = add_v2_row_features(frame, copy=copy)
    time = pd.to_numeric(result[TIME_COLUMN], errors="coerce")
    for key in COUNT_TIME_KEYS:
        lookup_key = _clean_text(result[key])
        result[f"{key}_prior_count"] = (
            lookup_key.map(reference["counts"][key]).fillna(0).astype("int32")
        )
        previous = lookup_key.map(reference["last_time"][key])
        result[f"{key}_seconds_since_previous"] = (time - previous).astype("float32")

    amount = pd.to_numeric(result["TransactionAmt"], errors="coerce")
    for key in AMOUNT_KEYS:
        prefix = f"{key}_amount"
        summary = reference["numeric"][prefix]
        lookup_key = _clean_text(result[key])
        result[f"{prefix}_prior_numeric_count"] = (
            lookup_key.map(summary["count"]).fillna(0).astype("int32")
        )
        result[f"{prefix}_prior_mean"] = lookup_key.map(summary["mean"]).astype("float32")
        result[f"{prefix}_prior_std"] = lookup_key.map(summary["std"]).astype("float32")
        mean, std = result[f"{prefix}_prior_mean"], result[f"{prefix}_prior_std"]
        result[f"{prefix}_difference"] = (amount - mean).astype("float32")
        result[f"{prefix}_ratio"] = (amount / mean.replace(0, np.nan)).astype("float32")
        result[f"{prefix}_zscore"] = ((amount - mean) / std.replace(0, np.nan)).astype("float32")

    for column in UID_D_STAT_COLUMNS:
        prefix = f"uid_proxy_{column}"
        if column not in result or prefix not in reference["numeric"]:
            continue
        summary = reference["numeric"][prefix]
        lookup_key = _clean_text(result["uid_proxy"])
        result[f"{prefix}_prior_numeric_count"] = (
            lookup_key.map(summary["count"]).fillna(0).astype("int32")
        )
        result[f"{prefix}_prior_mean"] = (
            lookup_key.map(summary["mean"]).astype("float32")
        )
        result[f"{prefix}_prior_std"] = (
            lookup_key.map(summary["std"]).astype("float32")
        )

    for column in UID_UNIQUE_VALUE_COLUMNS:
        if column in result and column in reference["nunique"]:
            result[f"uid_proxy_{column}_prior_nunique"] = (
                _clean_text(result["uid_proxy"])
                .map(reference["nunique"][column])
                .fillna(0)
                .astype("int32")
            )
    return result


def update_behavioral_reference(
    reference: dict[str, Any], frame: pd.DataFrame
) -> None:
    """Update online V2 state after prediction, in chronological FIFO order."""
    if not {"unique_hashes", "online_unique_hashes"}.issubset(reference):
        raise ValueError("Behavioral reference must be regenerated for online updates")
    rows = add_v2_row_features(frame, copy=True).sort_values(
        [TIME_COLUMN, ID_COLUMN], kind="stable"
    )
    for _, row in rows.iterrows():
        row_time = float(row[TIME_COLUMN])
        row_id = int(row[ID_COLUMN])
        metadata = reference["contract"]["metadata"]
        previous_cutoff = (
            float(metadata["history_end_transaction_dt"]),
            int(metadata["history_end_transaction_id"]),
        )
        if (row_time, row_id) <= previous_cutoff:
            raise ValueError("Online behavioral update is not strictly chronological")

        for key in COUNT_TIME_KEYS:
            lookup_key = str(row[key]) if pd.notna(row[key]) else "MISSING"
            reference["counts"][key][lookup_key] = (
                int(reference["counts"][key].get(lookup_key, 0)) + 1
            )
            reference["last_time"][key][lookup_key] = row_time

        numeric_pairs = [
            (key, "TransactionAmt", f"{key}_amount") for key in AMOUNT_KEYS
        ]
        numeric_pairs.extend(
            ("uid_proxy", column, f"uid_proxy_{column}")
            for column in UID_D_STAT_COLUMNS
            if column in rows
        )
        for key, value, prefix in numeric_pairs:
            numeric_value = pd.to_numeric(pd.Series([row[value]]), errors="coerce").iloc[0]
            if pd.isna(numeric_value):
                continue
            lookup_key = str(row[key]) if pd.notna(row[key]) else "MISSING"
            summary = reference["numeric"][prefix]
            count = int(summary["count"].get(lookup_key, 0))
            mean = float(summary["mean"].get(lookup_key, 0.0)) if count else 0.0
            std = float(summary["std"].get(lookup_key, 0.0)) if count >= 2 else 0.0
            m2 = std * std * count
            new_count = count + 1
            delta = float(numeric_value) - mean
            new_mean = mean + delta / new_count
            new_m2 = m2 + delta * (float(numeric_value) - new_mean)
            summary["count"][lookup_key] = new_count
            summary["mean"][lookup_key] = np.float32(new_mean)
            summary["std"][lookup_key] = (
                np.float32(np.sqrt(max(new_m2 / new_count, 0.0)))
                if new_count >= 2
                else np.nan
            )

        uid_key = str(row["uid_proxy"]) if pd.notna(row["uid_proxy"]) else "MISSING"
        for column in UID_UNIQUE_VALUE_COLUMNS:
            if column not in rows:
                continue
            value = str(row[column]) if pd.notna(row[column]) else "MISSING"
            pair_hash = int(
                _stable_pair_hashes(
                    pd.Series([uid_key], dtype="string"),
                    pd.Series([value], dtype="string"),
                )[0]
            )
            baseline = reference["unique_hashes"][column]
            position = int(np.searchsorted(baseline, pair_hash))
            existed_in_baseline = (
                position < len(baseline) and int(baseline[position]) == pair_hash
            )
            online_hashes = reference["online_unique_hashes"][column]
            if not existed_in_baseline and pair_hash not in online_hashes:
                online_hashes.add(pair_hash)
                current = int(reference["nunique"][column].get(uid_key, 0))
                reference["nunique"][column][uid_key] = current + 1

        metadata["history_end_transaction_dt"] = row_time
        metadata["history_end_transaction_id"] = row_id
        metadata["history_row_count"] = int(metadata["history_row_count"]) + 1


def _stable_pair_hashes(keys: pd.Series, values: pd.Series) -> np.ndarray:
    """Return deterministic compact hashes for exact historical membership."""
    key_hashes = pd.util.hash_pandas_object(keys, index=False).to_numpy(dtype="uint64")
    value_hashes = pd.util.hash_pandas_object(values, index=False).to_numpy(dtype="uint64")
    # Boost-style combination keeps order significant and is stable across the
    # batch builder and one-row online updater. A 64-bit collision is possible
    # in theory but negligible for this sub-million-row demonstration state.
    return key_hashes ^ (
        value_hashes
        + np.uint64(0x9E3779B97F4A7C15)
        + (key_hashes << np.uint64(6))
        + (key_hashes >> np.uint64(2))
    )
