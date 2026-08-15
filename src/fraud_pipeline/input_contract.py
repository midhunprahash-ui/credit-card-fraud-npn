"""Raw joined-transaction validation and version-specific feature preparation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .behavioral import apply_behavioral_reference
from .common import ID_COLUMN, TARGET_COLUMN, TIME_COLUMN, add_shared_features
from .model_contracts import VersionName


@dataclass(frozen=True)
class RawInputContract:
    columns: tuple[str, ...]
    identifier_column: str
    target_column: str

    @classmethod
    def load(cls, path: Path) -> "RawInputContract":
        document = json.loads(path.read_text())
        columns = tuple(document["required_columns"])
        if ID_COLUMN not in columns or TARGET_COLUMN in columns:
            raise ValueError("Raw schema must include TransactionID and exclude isFraud")
        if len(columns) != len(set(columns)):
            raise ValueError("Raw schema contains duplicate columns")
        return cls(columns, document["join"]["key"], document["target"])

    def align(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Validate identifiers, remove the label, and null-fill optional fields."""
        if frame.empty:
            raise ValueError("At least one transaction is required")
        if frame.columns.duplicated().any():
            raise ValueError("Input contains duplicate column names")
        cleaned = frame.drop(columns=[self.target_column], errors="ignore").copy()
        unknown = sorted(set(cleaned) - set(self.columns))
        if unknown:
            raise ValueError(f"Input contains unknown fields: {unknown}")
        for required in (self.identifier_column, TIME_COLUMN):
            if required not in cleaned:
                raise ValueError(f"Missing required field: {required}")
        for column in self.columns:
            if column not in cleaned:
                cleaned[column] = np.nan

        identifiers = pd.to_numeric(cleaned[self.identifier_column], errors="coerce")
        if identifiers.isna().any() or (~np.isfinite(identifiers)).any():
            raise ValueError("TransactionID must be a finite integer")
        if (identifiers <= 0).any() or (identifiers % 1 != 0).any():
            raise ValueError("TransactionID must be a positive integer")
        if identifiers.duplicated().any():
            raise ValueError("Duplicate TransactionID values are not allowed")
        cleaned[self.identifier_column] = identifiers.astype("int64")

        times = pd.to_numeric(cleaned[TIME_COLUMN], errors="coerce")
        if times.isna().any() or (~np.isfinite(times)).any() or (times < 0).any():
            raise ValueError("TransactionDT must be a finite non-negative number")
        cleaned[TIME_COLUMN] = times
        if "TransactionAmt" in cleaned:
            amounts = pd.to_numeric(cleaned["TransactionAmt"], errors="coerce")
            invalid_amount = amounts.notna() & ((~np.isfinite(amounts)) | (amounts < 0))
            if invalid_amount.any():
                raise ValueError("TransactionAmt must be a finite non-negative number")
            cleaned["TransactionAmt"] = amounts
        return cleaned.loc[:, self.columns]


def prepare_model_input(
    raw_frame: pd.DataFrame,
    version_name: VersionName,
    *,
    behavioral_reference: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Apply the matching feature-engineering version and remove protected fields."""
    if TARGET_COLUMN in raw_frame:
        raise ValueError("isFraud must be removed before feature engineering")
    if version_name == "V1":
        # The approved V1 training contract excluded constant source column
        # V107. It must also be absent while num_missing is calculated.
        v1_raw = raw_frame.drop(columns=["V107"], errors="ignore").copy()
        identity_columns = [
            column
            for column in v1_raw
            if column.startswith("id_") or column in {"DeviceType", "DeviceInfo"}
        ]
        # V1 training recorded whether the left join found an identity row.
        # For raw API input the closest reproducible signal is the presence of
        # any identity-table value; Supabase preparation can supply those joined
        # values directly.
        v1_raw["has_identity"] = v1_raw[identity_columns].notna().any(axis=1).astype("int8")
        engineered = add_shared_features(v1_raw, copy=False)
    elif version_name == "V2":
        if behavioral_reference is None:
            raise ValueError("V2 inference requires a chronological behavioral reference")
        _validate_reference_cutoff(behavioral_reference, raw_frame)
        engineered = apply_behavioral_reference(raw_frame, behavioral_reference, copy=True)
    else:  # pragma: no cover - protected by the public literal contract
        raise ValueError(f"Unsupported version: {version_name}")
    return engineered.drop(columns=[TARGET_COLUMN, ID_COLUMN], errors="ignore")


def _validate_reference_cutoff(reference: dict[str, Any], frame: pd.DataFrame) -> None:
    contract = reference.get("contract", {})
    if contract.get("uses_target") is not False:
        raise ValueError("Behavioral reference does not prove target exclusion")
    metadata = contract.get("metadata", {})
    end_time = metadata.get("history_end_transaction_dt")
    end_id = metadata.get("history_end_transaction_id")
    if end_time is None or end_id is None:
        raise ValueError("Behavioral reference is missing its chronological history cutoff")
    first = frame.sort_values([TIME_COLUMN, ID_COLUMN], kind="stable").iloc[0]
    if (float(end_time), int(end_id)) >= (float(first[TIME_COLUMN]), int(first[ID_COLUMN])):
        raise ValueError("Behavioral reference overlaps the transaction being scored")
