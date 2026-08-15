"""Application services for safe single and CSV batch inference."""

from __future__ import annotations

import copy
import io
import json
import logging
import math
import threading
import time
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.fraud_pipeline.inference_engine import InferenceEngine, TransactionPrediction
from src.fraud_pipeline.input_contract import RawInputContract
from src.fraud_pipeline.model_adapters import ModelPredictionError
from src.fraud_pipeline.model_manager import ModelLoadError, ModelManager
from src.fraud_pipeline.registry import ModelRegistry

from .errors import ApiError


LOGGER = logging.getLogger(__name__)


class BehavioralReferenceProvider:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._reference: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def get(self) -> dict[str, Any]:
        with self._lock:
            if self._reference is not None:
                return self._reference
            if not self.path.is_file():
                raise ApiError(
                    503,
                    "v2_reference_unavailable",
                    "The safe V2 behavioral reference has not been prepared",
                )
            reference = joblib.load(self.path)
            metadata = reference.get("contract", {}).get("metadata", {})
            if not {
                "history_end_transaction_dt",
                "history_end_transaction_id",
            }.issubset(metadata):
                raise ApiError(
                    503,
                    "v2_reference_unsafe",
                    "The V2 behavioral reference has no verified chronological cutoff",
                )
            self._reference = reference
            return reference

    def get_copy(self) -> dict[str, Any]:
        """Give each stream isolated mutable online state."""
        return copy.deepcopy(self.get())


class RuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.prediction_requests = 0
        self.transactions_scored = 0
        self.model_predictions = 0
        self.error_count = 0
        self.total_latency_ms = 0.0

    def record_success(self, prediction: TransactionPrediction, latency_ms: float) -> None:
        with self._lock:
            self.prediction_requests += 1
            self.transactions_scored += 1
            self.model_predictions += len(prediction.results)
            self.total_latency_ms += latency_ms

    def record_error(self) -> None:
        with self._lock:
            self.error_count += 1

    def summary(self) -> dict[str, int | float]:
        with self._lock:
            average = (
                self.total_latency_ms / self.transactions_scored
                if self.transactions_scored
                else 0.0
            )
            return {
                "prediction_requests": self.prediction_requests,
                "transactions_scored": self.transactions_scored,
                "model_predictions": self.model_predictions,
                "error_count": self.error_count,
                "average_request_latency_ms": round(average, 3),
            }


class PredictionService:
    def __init__(
        self,
        registry: ModelRegistry,
        raw_contract: RawInputContract,
        model_manager: ModelManager,
        reference_provider: BehavioralReferenceProvider,
        metrics: RuntimeMetrics,
    ) -> None:
        self.registry = registry
        self.raw_contract = raw_contract
        self.model_manager = model_manager
        self.reference_provider = reference_provider
        self.metrics = metrics

    def predict(
        self,
        transaction: dict[str, Any],
        model_identifiers: list[str],
        *,
        behavioral_reference: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            specs = [self.registry.get(identifier) for identifier in model_identifiers]
            reference = (
                behavioral_reference
                if behavioral_reference is not None
                else self.reference_provider.get()
                if any(spec.version_name == "V2" for spec in specs)
                else None
            )
            engine = InferenceEngine(
                self.registry,
                self.raw_contract,
                behavioral_reference=reference,
                adapter_loader=self.model_manager.get,
            )
            prediction = engine.predict_one(transaction, model_identifiers)
        except ApiError:
            self.metrics.record_error()
            raise
        except ModelLoadError as error:
            self.metrics.record_error()
            LOGGER.error(
                "model_load_failed",
                extra={"error_type": error.error_type},
            )
            raise ApiError(
                503,
                "model_unavailable",
                f"Selected model {error.model_identifier} could not be loaded",
            ) from error
        except ModelPredictionError as error:
            self.metrics.record_error()
            LOGGER.error(
                "model_prediction_failed",
                extra={"error_type": error.error_type},
            )
            raise ApiError(
                500,
                "model_prediction_failed",
                f"Selected model {error.model_identifier} could not score the transaction",
            ) from error
        except ValueError as error:
            self.metrics.record_error()
            raise ApiError(422, "invalid_prediction_input", str(error)) from error
        except Exception as error:
            self.metrics.record_error()
            LOGGER.exception(
                "prediction_failed", extra={"error_type": type(error).__name__}
            )
            raise ApiError(500, "prediction_failed", "Prediction processing failed") from error
        elapsed_ms = (time.perf_counter() - started) * 1_000
        self.metrics.record_success(prediction, elapsed_ms)
        return _prediction_response(prediction)


class BatchPredictionService:
    ALLOWED_CONTENT_TYPES = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }

    def __init__(
        self,
        prediction_service: PredictionService,
        *,
        max_file_bytes: int,
        max_rows: int,
        chunk_size: int,
    ) -> None:
        self.prediction_service = prediction_service
        self.max_file_bytes = max_file_bytes
        self.max_rows = max_rows
        self.chunk_size = chunk_size

    def process(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        content: bytes,
        model_identifiers: list[str],
    ) -> dict[str, Any]:
        self._validate_file(filename, content_type, content)
        try:
            frame = pd.read_csv(io.BytesIO(content))
        except (pd.errors.ParserError, UnicodeDecodeError) as error:
            raise ApiError(422, "invalid_csv", "The uploaded file is not a valid CSV") from error
        if frame.empty:
            raise ApiError(422, "empty_csv", "The uploaded CSV has no transaction rows")
        if len(frame) > self.max_rows:
            raise ApiError(
                413,
                "batch_row_limit_exceeded",
                f"CSV row count exceeds the limit of {self.max_rows}",
            )
        missing = sorted({"TransactionID", "TransactionDT"} - set(frame))
        if missing:
            raise ApiError(
                422,
                "missing_required_columns",
                f"CSV is missing required columns: {missing}",
            )

        duplicate_mask = frame["TransactionID"].duplicated(keep=False)
        invalid: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []
        fraud_counts = {identifier: 0 for identifier in model_identifiers}
        agreement_count = 0
        suspicious_value = 0.0

        for start in range(0, len(frame), self.chunk_size):
            chunk = frame.iloc[start : start + self.chunk_size]
            for index, row in chunk.iterrows():
                row_number = int(index) + 2
                transaction_id = _json_scalar(row.get("TransactionID"))
                if bool(duplicate_mask.loc[index]):
                    invalid.append(
                        {
                            "row_number": row_number,
                            "transaction_id": transaction_id,
                            "error_code": "duplicate_transaction_id",
                            "message": "TransactionID is duplicated in the uploaded CSV",
                        }
                    )
                    continue
                payload = {
                    column: _json_scalar(value) for column, value in row.items()
                }
                try:
                    prediction = self.prediction_service.predict(
                        payload, model_identifiers
                    )
                except ApiError as error:
                    if error.status_code != 422:
                        raise
                    invalid.append(
                        {
                            "row_number": row_number,
                            "transaction_id": transaction_id,
                            "error_code": error.code,
                            "message": error.message,
                        }
                    )
                    continue
                flat = _flatten_batch_prediction(prediction)
                results.append(flat)
                for model in prediction["results"]:
                    fraud_counts[model["model_identifier"]] += int(model["decision"])
                votes = prediction["agreement"]["fraud_vote_count"]
                count = prediction["agreement"]["selected_model_count"]
                agreement_count += int(votes in {0, count})
                if votes > 0:
                    amount = pd.to_numeric(row.get("TransactionAmt"), errors="coerce")
                    if pd.notna(amount):
                        suspicious_value += float(amount)

        summary = {
            "total_rows": int(len(frame)),
            "valid_rows": len(results),
            "invalid_rows": len(invalid),
            "processed_rows": len(results),
            "failed_rows": 0,
            "fraud_count_by_model": fraud_counts,
            "model_agreement_count": agreement_count,
            "suspicious_transaction_value": round(suspicious_value, 2),
        }
        return {
            "summary": summary,
            "results": results,
            "invalid_row_report": invalid,
            "processing_status": "completed",
        }

    def process_one(
        self,
        *,
        filename: str | None,
        content_type: str | None,
        content: bytes,
        model_identifiers: list[str],
    ) -> dict[str, Any]:
        self._validate_file(filename, content_type, content)
        try:
            frame = pd.read_csv(io.BytesIO(content))
        except (pd.errors.ParserError, UnicodeDecodeError) as error:
            raise ApiError(422, "invalid_csv", "The uploaded file is not a valid CSV") from error
        if len(frame) != 1:
            raise ApiError(
                422,
                "single_csv_row_count",
                "Single-transaction CSV input must contain exactly one data row",
            )
        missing = sorted({"TransactionID", "TransactionDT"} - set(frame))
        if missing:
            raise ApiError(
                422,
                "missing_required_columns",
                f"CSV is missing required columns: {missing}",
            )
        payload = {
            column: _json_scalar(value)
            for column, value in frame.iloc[0].items()
        }
        return self.prediction_service.predict(payload, model_identifiers)

    def _validate_file(
        self, filename: str | None, content_type: str | None, content: bytes
    ) -> None:
        if not filename or not filename.lower().endswith(".csv"):
            raise ApiError(415, "invalid_file_type", "Upload a file with a .csv extension")
        if (
            content_type
            and content_type.split(";", 1)[0].lower()
            not in self.ALLOWED_CONTENT_TYPES
        ):
            raise ApiError(415, "invalid_content_type", "The uploaded file must be CSV")
        if len(content) > self.max_file_bytes:
            raise ApiError(
                413,
                "batch_file_too_large",
                f"CSV exceeds the {self.max_file_bytes}-byte upload limit",
            )


def parse_model_identifiers(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(parsed, list) or not all(
        isinstance(item, str) for item in parsed
    ):
        raise ApiError(422, "invalid_model_selection", "models must be a JSON string array")
    if not parsed or len(parsed) > 8 or len(parsed) != len(set(parsed)):
        raise ApiError(
            422,
            "invalid_model_selection",
            "Select between one and eight unique models",
        )
    return parsed


def build_batch_download(report: dict[str, Any]) -> bytes:
    """Package prediction and invalid-row CSVs without persisting uploads."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "prediction_results.csv",
            pd.DataFrame(report["results"]).to_csv(index=False),
        )
        archive.writestr(
            "invalid_rows.csv",
            pd.DataFrame(report["invalid_row_report"]).to_csv(index=False),
        )
        archive.writestr(
            "summary.json",
            json.dumps(report["summary"], indent=2, sort_keys=True),
        )
    return buffer.getvalue()


def _prediction_response(prediction: TransactionPrediction) -> dict[str, Any]:
    results = []
    for model_result in prediction.results:
        item = asdict(model_result)
        item["decision_label"] = "fraud" if model_result.decision else "legitimate"
        item["important_features"] = None
        results.append(item)
    votes = prediction.agreement.fraud_vote_count
    count = prediction.agreement.selected_model_count
    if prediction.agreement.unanimous:
        agreement_label = "all_flag_fraud" if votes == count else "all_flag_legitimate"
    else:
        agreement_label = "disagreement"
    return {
        "transaction_id": prediction.transaction_id,
        "input_completeness": prediction.input_completeness,
        "results": results,
        "agreement": {
            **asdict(prediction.agreement),
            "agreement_label": agreement_label,
        },
    }


def _flatten_batch_prediction(prediction: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "TransactionID": prediction["transaction_id"],
        "input_completeness": prediction["input_completeness"],
    }
    for model in prediction["results"]:
        prefix = model["model_name"]
        row[f"{prefix}_score"] = model["risk_score"]
        row[f"{prefix}_threshold"] = model["threshold"]
        row[f"{prefix}_decision"] = model["decision"]
    row["fraud_vote_count"] = prediction["agreement"]["fraud_vote_count"]
    row["processing_status"] = "completed"
    return row


def _json_scalar(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value
