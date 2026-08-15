from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.fraud_pipeline.behavioral import build_behavioral_reference
from src.fraud_pipeline.inference_engine import InferenceEngine
from src.fraud_pipeline.input_contract import RawInputContract, prepare_model_input
from src.fraud_pipeline.model_adapters import ModelPrediction
from src.fraud_pipeline.registry import ModelRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def write_schema(path: Path) -> RawInputContract:
    path.write_text(
        json.dumps(
            {
                "required_columns": [
                    "TransactionID",
                    "TransactionDT",
                    "TransactionAmt",
                    "card1",
                    "addr1",
                    "D1",
                    "D4",
                    "D10",
                    "D15",
                    "P_emaildomain",
                    "DeviceInfo",
                    "DeviceType",
                ],
                "target": "isFraud",
                "join": {"type": "left", "key": "TransactionID"},
            }
        )
    )
    return RawInputContract.load(path)


def transaction(transaction_id: int = 2, transaction_dt: int = 200) -> dict[str, object]:
    return {
        "TransactionID": transaction_id,
        "TransactionDT": transaction_dt,
        "TransactionAmt": 25.5,
        "card1": 1001,
        "addr1": 10,
        "D1": 0,
        "D4": 0,
        "D10": 0,
        "D15": 0,
        "P_emaildomain": "bank.test",
        "DeviceInfo": "device",
        "DeviceType": "desktop",
    }


def test_raw_contract_drops_label_and_null_fills_optional_fields(tmp_path: Path) -> None:
    contract = write_schema(tmp_path / "schema.json")
    payload = transaction()
    payload.pop("DeviceInfo")
    payload["isFraud"] = 1

    aligned = contract.align(pd.DataFrame([payload]))

    assert list(aligned) == list(contract.columns)
    assert "isFraud" not in aligned
    assert pd.isna(aligned.iloc[0]["DeviceInfo"])


@pytest.mark.parametrize(
    "change, message",
    [
        ({"TransactionID": "invalid"}, "TransactionID"),
        ({"TransactionDT": -1}, "TransactionDT"),
        ({"TransactionAmt": -1}, "TransactionAmt"),
        ({"unknown_field": 1}, "unknown fields"),
    ],
)
def test_raw_contract_rejects_invalid_values(
    tmp_path: Path, change: dict[str, object], message: str
) -> None:
    contract = write_schema(tmp_path / "schema.json")
    payload = transaction()
    payload.update(change)
    with pytest.raises(ValueError, match=message):
        contract.align(pd.DataFrame([payload]))


def test_v2_rejects_missing_or_overlapping_history(tmp_path: Path) -> None:
    contract = write_schema(tmp_path / "schema.json")
    current = contract.align(pd.DataFrame([transaction()]))
    with pytest.raises(ValueError, match="chronological behavioral reference"):
        prepare_model_input(current, "V2")

    overlapping = build_behavioral_reference(current)
    with pytest.raises(ValueError, match="overlaps"):
        prepare_model_input(current, "V2", behavioral_reference=overlapping)


def test_inference_engine_keeps_v1_v2_feature_paths_separate(tmp_path: Path) -> None:
    contract = write_schema(tmp_path / "schema.json")
    history = contract.align(pd.DataFrame([transaction(1, 100)]))
    reference = build_behavioral_reference(history)
    seen: dict[str, set[str]] = {}

    class StubAdapter:
        def __init__(self, spec) -> None:
            self.spec = spec

        def predict(self, frame: pd.DataFrame) -> list[ModelPrediction]:
            seen[self.spec.version_name] = set(frame)
            score = 0.9 if self.spec.version_name == "V2" else 0.1
            return [
                ModelPrediction(
                    model_identifier=self.spec.identifier,
                    model_name=self.spec.model_name,
                    model_version=self.spec.version_name,
                    run_id=self.spec.run_id,
                    risk_score=score,
                    threshold=0.5,
                    decision=score >= 0.5,
                    latency_ms=1.0,
                    champion=self.spec.champion,
                )
            ]

    engine = InferenceEngine(
        ModelRegistry.load(PROJECT_ROOT),
        contract,
        behavioral_reference=reference,
        adapter_loader=StubAdapter,
    )
    result = engine.predict_one(
        transaction(), ["logistic_regression.v1", "catboost.v2"]
    )

    assert "uid_proxy_prior_count" not in seen["V1"]
    assert "uid_proxy_prior_count" in seen["V2"]
    assert result.transaction_id == 2
    assert result.agreement.fraud_vote_count == 1
    assert result.agreement.selected_model_count == 2
    assert result.agreement.unanimous is False
    assert all("isFraud" not in columns for columns in seen.values())
