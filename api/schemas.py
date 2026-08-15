"""Pydantic contracts for manual and batch fraud-risk inference."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_identifiers: list[str] = Field(min_length=1, max_length=8)
    transaction: dict[str, Any]

    @field_validator("model_identifiers")
    @classmethod
    def unique_models(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("model_identifiers must be unique")
        return value


class ModelPredictionResponse(BaseModel):
    model_identifier: str
    model_name: str
    model_version: str
    run_id: str
    risk_score: float
    threshold: float
    decision: bool
    decision_label: str
    latency_ms: float
    champion: bool
    processing_status: str
    important_features: list[dict[str, Any]] | None = None


class AgreementResponse(BaseModel):
    fraud_vote_count: int
    selected_model_count: int
    unanimous: bool
    agreement_label: str


class PredictionResponse(BaseModel):
    transaction_id: int
    input_completeness: float
    results: list[ModelPredictionResponse]
    agreement: AgreementResponse


class InvalidBatchRow(BaseModel):
    row_number: int
    transaction_id: int | float | str | None = None
    error_code: str
    message: str


class BatchSummary(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    processed_rows: int
    failed_rows: int
    fraud_count_by_model: dict[str, int]
    model_agreement_count: int
    suspicious_transaction_value: float


class BatchPredictionResponse(BaseModel):
    summary: BatchSummary
    results: list[dict[str, Any]]
    invalid_row_report: list[InvalidBatchRow]
    processing_status: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class StreamStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    selected_models: list[str] = Field(min_length=1, max_length=8)
    transactions_per_second: Literal[1, 2, 5]

    @field_validator("selected_models")
    @classmethod
    def unique_stream_models(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("selected_models must be unique")
        return value
