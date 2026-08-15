"""Common raw-transaction inference orchestration for selected model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from .input_contract import RawInputContract, prepare_model_input
from .model_adapters import ModelAdapter, ModelPrediction, load_model_adapter
from .registry import ModelRegistry, ModelSpec


@dataclass(frozen=True)
class AgreementSummary:
    fraud_vote_count: int
    selected_model_count: int
    unanimous: bool


@dataclass(frozen=True)
class TransactionPrediction:
    transaction_id: int
    input_completeness: float
    results: tuple[ModelPrediction, ...]
    agreement: AgreementSummary


class InferenceEngine:
    """Validates raw input and routes each model through its own saved pipeline."""

    def __init__(
        self,
        registry: ModelRegistry,
        raw_contract: RawInputContract,
        *,
        behavioral_reference: dict[str, Any] | None = None,
        adapter_loader: Callable[[ModelSpec], ModelAdapter] = load_model_adapter,
    ) -> None:
        self.registry = registry
        self.raw_contract = raw_contract
        self.behavioral_reference = behavioral_reference
        self.adapter_loader = adapter_loader

    def predict_one(
        self,
        transaction: dict[str, Any] | pd.Series,
        model_identifiers: list[str],
    ) -> TransactionPrediction:
        if not model_identifiers:
            raise ValueError("Select at least one model")
        if len(model_identifiers) != len(set(model_identifiers)):
            raise ValueError("Selected model identifiers must be unique")
        source = transaction.to_dict() if isinstance(transaction, pd.Series) else transaction
        aligned = self.raw_contract.align(pd.DataFrame([source]))
        input_completeness = float(aligned.notna().sum(axis=1).iloc[0] / len(aligned.columns))
        by_version: dict[str, pd.DataFrame] = {}
        results: list[ModelPrediction] = []
        for identifier in model_identifiers:
            spec = self.registry.get(identifier)
            if spec.version_name not in by_version:
                by_version[spec.version_name] = prepare_model_input(
                    aligned,
                    spec.version_name,
                    behavioral_reference=self.behavioral_reference,
                )
            # Loading and preprocessing remain adapter-specific. Sharing only the
            # deterministic V1/V2 feature frame does not mix saved preprocessors.
            adapter = self.adapter_loader(spec)
            results.extend(adapter.predict(by_version[spec.version_name]))
        votes = sum(result.decision for result in results)
        return TransactionPrediction(
            transaction_id=int(aligned.iloc[0][self.raw_contract.identifier_column]),
            input_completeness=input_completeness,
            results=tuple(results),
            agreement=AgreementSummary(
                fraud_vote_count=votes,
                selected_model_count=len(results),
                unanimous=votes in {0, len(results)},
            ),
        )
