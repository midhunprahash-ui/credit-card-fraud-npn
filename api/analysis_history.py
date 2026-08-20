"""Server-only Supabase repository for browser-scoped analysis history."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from .errors import ApiError
from .stream_repository import CompletedStreamRecord, SupabaseRepositoryError


AnalysisMode = Literal["single", "csv", "realtime"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _model_metadata(identifier: str) -> tuple[str, str]:
    key, version = identifier.rsplit(".", 1)
    names = {
        "logistic_regression": "Logistic Regression",
        "lightgbm": "LightGBM",
        "catboost": "CatBoost",
        "neural_network": "Neural Network",
    }
    return f"{names.get(key, key.replace('_', ' ').title())}.{version.upper()}", version.upper()


def _safe_transaction_id(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if str(parsed) == str(value).split(".0", 1)[0] else None


class AnalysisHistoryRepository:
    """Persists immutable prediction facts and mutable cached explanations."""

    PAGE_SIZE = 1_000

    def __init__(self, client: Any) -> None:
        self.client = client

    async def persist_single(
        self,
        *,
        client_id: uuid.UUID,
        mode: Literal["single"],
        selected_models: list[str],
        input_payload: dict[str, Any],
        prediction: dict[str, Any],
    ) -> dict[str, str]:
        run_id = str(uuid.uuid4())
        await self._insert_run(
            run_id=run_id,
            client_id=client_id,
            mode=mode,
            selected_models=selected_models,
            source_name=None,
            total_transactions=1,
        )
        transaction_rows = await self.client.request(
            "POST",
            "analysis_transactions",
            body={
                "analysis_run_id": run_id,
                "ordinal": 0,
                "transaction_id": prediction["transaction_id"],
                "raw_transaction_id": str(prediction["transaction_id"]),
                "input_payload": self._clean_input(input_payload),
                "status": "COMPLETED",
            },
            prefer="return=representation",
        )
        if len(transaction_rows) != 1:
            raise SupabaseRepositoryError("Supabase did not return the analysis transaction")
        prediction_ids = await self._insert_predictions(
            str(transaction_rows[0]["id"]), prediction["results"]
        )
        await self._complete_run(
            run_id,
            status="COMPLETED",
            successful=1,
            failed=0,
            summary={"input_completeness": prediction["input_completeness"], **prediction["agreement"]},
        )
        return {"run_id": run_id, **prediction_ids}

    async def persist_batch(
        self,
        *,
        client_id: uuid.UUID,
        selected_models: list[str],
        source_name: str | None,
        report: dict[str, Any],
    ) -> tuple[str, dict[tuple[int, str], str]]:
        run_id = str(uuid.uuid4())
        summary = report["summary"]
        await self._insert_run(
            run_id=run_id,
            client_id=client_id,
            mode="csv",
            selected_models=selected_models,
            source_name=source_name,
            total_transactions=int(summary["total_rows"]),
        )
        completed_rows: list[dict[str, Any]] = []
        for ordinal, row in enumerate(report["results"]):
            source_ordinal = int(row.get("history_ordinal", ordinal))
            completed_rows.append(
                {
                    "analysis_run_id": run_id,
                    "ordinal": source_ordinal,
                    "transaction_id": _safe_transaction_id(row.get("TransactionID")),
                    "raw_transaction_id": str(row.get("TransactionID", "")),
                    "input_payload": self._clean_input(dict(row.get("input_payload") or {})),
                    "status": "COMPLETED",
                }
            )
        for offset, row in enumerate(report["invalid_row_report"]):
            completed_rows.append(
                {
                    "analysis_run_id": run_id,
                    "ordinal": int(row.get("row_number", offset + 2)) - 2,
                    "transaction_id": _safe_transaction_id(row.get("transaction_id")),
                    "raw_transaction_id": str(row.get("transaction_id") or ""),
                    "input_payload": self._clean_input(
                        dict(row.get("input_payload") or {})
                    ),
                    "status": "FAILED",
                    "error_code": row["error_code"],
                    "error_message": row["message"],
                }
            )
        stored_transactions = await self.client.request(
            "POST",
            "analysis_transactions",
            body=completed_rows,
            prefer="return=representation",
        )
        if len(stored_transactions) != len(completed_rows):
            raise SupabaseRepositoryError("Not every batch transaction was persisted")
        stored_by_ordinal = {int(row["ordinal"]): str(row["id"]) for row in stored_transactions}
        prediction_id_map: dict[tuple[int, str], str] = {}
        for ordinal, row in enumerate(report["results"]):
            source_ordinal = int(row.get("history_ordinal", ordinal))
            identifiers = await self._insert_predictions(
                stored_by_ordinal[source_ordinal], list(row.get("model_results") or [])
            )
            for identifier, prediction_id in identifiers.items():
                prediction_id_map[(source_ordinal, identifier)] = prediction_id
        await self._complete_run(
            run_id,
            status="COMPLETED" if not summary["failed_rows"] else "PARTIAL",
            successful=int(summary["processed_rows"]),
            failed=int(summary["invalid_rows"]) + int(summary["failed_rows"]),
            summary=summary,
        )
        return run_id, prediction_id_map

    async def create_realtime_run(
        self,
        *,
        client_id: uuid.UUID,
        stream_run_id: str,
        selected_models: list[str],
        dataset_id: str,
    ) -> str:
        run_id = str(uuid.uuid4())
        await self._insert_run(
            run_id=run_id,
            client_id=client_id,
            mode="realtime",
            selected_models=selected_models,
            source_name=dataset_id,
            total_transactions=0,
            stream_run_id=stream_run_id,
        )
        return run_id

    async def persist_stream_batch(
        self,
        stream_run_id: str,
        records: list[CompletedStreamRecord],
        run_values: dict[str, Any],
    ) -> None:
        runs = await self.client.request(
            "GET",
            "analysis_runs",
            params={
                "select": "id",
                "stream_run_id": f"eq.{stream_run_id}",
                "limit": "1",
            },
        )
        if not runs:
            return
        run_id = str(runs[0]["id"])
        source_ids = [record.stream_transaction_id for record in records]
        stored_inputs = await self.client.request(
            "GET",
            "stream_transactions",
            params={
                "select": "id,transaction_payload",
                "id": f"in.({','.join(str(value) for value in source_ids)})",
            },
        )
        input_by_id = {int(row["id"]): dict(row["transaction_payload"]) for row in stored_inputs}
        transaction_body = [
            {
                "analysis_run_id": run_id,
                "ordinal": record.sequence_number,
                "transaction_id": record.transaction_id,
                "raw_transaction_id": str(record.transaction_id),
                "input_payload": self._clean_input(input_by_id.get(record.stream_transaction_id, {})),
                "status": record.status,
                "error_code": record.error_code,
                "error_message": (
                    "The real-time transaction could not be scored"
                    if record.error_code
                    else None
                ),
            }
            for record in records
        ]
        stored_transactions = await self.client.request(
            "POST",
            "analysis_transactions",
            params={"on_conflict": "analysis_run_id,ordinal"},
            body=transaction_body,
            prefer="resolution=merge-duplicates,return=representation",
        )
        transaction_by_ordinal = {
            int(row["ordinal"]): str(row["id"]) for row in stored_transactions
        }
        prediction_body: list[dict[str, Any]] = []
        for record in records:
            transaction_record_id = transaction_by_ordinal.get(record.sequence_number)
            if not transaction_record_id:
                continue
            for prediction in record.predictions:
                model_name, version = _model_metadata(prediction.model_identifier)
                prediction_body.append(
                    {
                        "analysis_transaction_id": transaction_record_id,
                        "model_identifier": prediction.model_identifier,
                        "model_name": model_name,
                        "model_version": version,
                        "model_run_id": prediction.model_run_id,
                        "risk_score": prediction.risk_score,
                        "threshold": prediction.threshold,
                        "decision": prediction.decision,
                        "latency_ms": prediction.latency_ms,
                    }
                )
        if prediction_body:
            await self.client.request(
                "POST",
                "analysis_prediction_results",
                params={"on_conflict": "analysis_transaction_id,model_identifier"},
                body=prediction_body,
                prefer="resolution=merge-duplicates,return=minimal",
            )
        await self.update_stream_run(stream_run_id, run_values)

    async def update_stream_run(
        self, stream_run_id: str, values: dict[str, Any]
    ) -> None:
        status = str(values.get("status", "RUNNING"))
        mapped_status = {
            "COMPLETED": "COMPLETED",
            "STOPPED": "PARTIAL",
            "FAILED": "FAILED",
        }.get(status, "PROCESSING")
        received = int(values.get("received_count", 0))
        processed = int(values.get("processed_count", 0))
        failed = int(values.get("failed_count", 0))
        await self.client.request(
            "PATCH",
            "analysis_runs",
            params={"stream_run_id": f"eq.{stream_run_id}"},
            body={
                "status": mapped_status,
                "total_transactions": max(received, processed + failed),
                "successful_transactions": processed,
                "failed_transactions": failed,
                "summary": values,
                "updated_at": _now_iso(),
            },
            prefer="return=minimal",
        )

    async def list_runs(
        self,
        *,
        client_id: uuid.UUID,
        mode: AnalysisMode,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        return await self.client.request(
            "GET",
            "analysis_runs",
            params={
                "select": (
                    "id,input_mode,source_name,stream_run_id,selected_models,status,"
                    "total_transactions,successful_transactions,failed_transactions,"
                    "summary,created_at,updated_at"
                ),
                "client_id": f"eq.{client_id}",
                "input_mode": f"eq.{mode}",
                "order": "created_at.desc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )

    async def get_run(
        self, *, client_id: uuid.UUID, run_id: str
    ) -> dict[str, Any] | None:
        runs = await self.client.request(
            "GET",
            "analysis_runs",
            params={
                "select": (
                    "id,input_mode,source_name,stream_run_id,selected_models,status,"
                    "total_transactions,successful_transactions,failed_transactions,"
                    "summary,created_at,updated_at"
                ),
                "id": f"eq.{run_id}",
                "client_id": f"eq.{client_id}",
                "limit": "1",
            },
        )
        if not runs:
            return None
        transactions = await self._all_rows(
            "analysis_transactions",
            {
                "select": (
                    "id,ordinal,transaction_id,raw_transaction_id,input_payload,status,"
                    "error_code,error_message,created_at"
                ),
                "analysis_run_id": f"eq.{run_id}",
                "order": "ordinal.asc",
            },
        )
        transaction_ids = [str(row["id"]) for row in transactions]
        predictions: list[dict[str, Any]] = []
        for start in range(0, len(transaction_ids), 100):
            chunk = transaction_ids[start : start + 100]
            predictions.extend(
                await self.client.request(
                    "GET",
                    "analysis_prediction_results",
                    params={
                        "select": (
                            "id,analysis_transaction_id,model_identifier,model_name,"
                            "model_version,model_run_id,risk_score,threshold,decision,latency_ms,"
                            "explanation_status,explanation_technique,"
                            "explanation_technique_label,top_contributed_features,reasoning,"
                            "reasoning_source,explanation_error,explained_at,created_at"
                        ),
                        "analysis_transaction_id": f"in.({','.join(chunk)})",
                        "order": "model_identifier.asc",
                    },
                )
            )
        predictions_by_transaction: dict[str, list[dict[str, Any]]] = {}
        for prediction in predictions:
            predictions_by_transaction.setdefault(
                str(prediction["analysis_transaction_id"]), []
            ).append(prediction)
        return {
            "run": runs[0],
            "transactions": [
                {
                    **transaction,
                    "predictions": predictions_by_transaction.get(str(transaction["id"]), []),
                }
                for transaction in transactions
            ],
        }

    async def explain_prediction(
        self,
        *,
        client_id: uuid.UUID,
        prediction_id: str,
        prediction_service: Any,
    ) -> dict[str, Any]:
        predictions = await self.client.request(
            "GET",
            "analysis_prediction_results",
            params={
                "select": "*",
                "id": f"eq.{prediction_id}",
                "limit": "1",
            },
        )
        if not predictions:
            raise ApiError(404, "history_prediction_not_found", "Prediction history was not found")
        prediction = predictions[0]
        transactions = await self.client.request(
            "GET",
            "analysis_transactions",
            params={
                "select": "id,analysis_run_id,transaction_id,input_payload",
                "id": f"eq.{prediction['analysis_transaction_id']}",
                "limit": "1",
            },
        )
        if not transactions:
            raise ApiError(404, "history_transaction_not_found", "Transaction history was not found")
        transaction = transactions[0]
        owners = await self.client.request(
            "GET",
            "analysis_runs",
            params={
                "select": "id",
                "id": f"eq.{transaction['analysis_run_id']}",
                "client_id": f"eq.{client_id}",
                "limit": "1",
            },
        )
        if not owners:
            raise ApiError(404, "history_prediction_not_found", "Prediction history was not found")
        if prediction["explanation_status"] == "COMPLETED":
            return self._explanation_response(
                prediction, int(transaction["transaction_id"] or 0)
            )
        try:
            explanation = prediction_service.explain(
                dict(transaction["input_payload"]),
                str(prediction["model_identifier"]),
                bool(prediction["decision"]),
            )
        except Exception as error:
            await self.client.request(
                "PATCH",
                "analysis_prediction_results",
                params={"id": f"eq.{prediction_id}"},
                body={
                    "explanation_status": "FAILED",
                    "explanation_error": "Explanation generation failed",
                    "updated_at": _now_iso(),
                },
                prefer="return=minimal",
            )
            raise error
        values = {
            "explanation_status": "COMPLETED",
            "explanation_technique": explanation["explanation_technique"],
            "explanation_technique_label": explanation["explanation_technique_label"],
            "top_contributed_features": explanation["important_features"],
            "reasoning": explanation["behavioral_explanation"],
            "reasoning_source": explanation["behavioral_explanation_source"],
            "explanation_error": None,
            "explained_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await self.client.request(
            "PATCH",
            "analysis_prediction_results",
            params={"id": f"eq.{prediction_id}"},
            body=values,
            prefer="return=minimal",
        )
        return {
            "transaction_id": explanation["transaction_id"],
            "model_identifier": prediction["model_identifier"],
            "method": "local_feature_contribution",
            **values,
            "important_features": values["top_contributed_features"],
            "behavioral_explanation": values["reasoning"],
            "behavioral_explanation_source": values["reasoning_source"],
        }

    async def export_csv(self, *, client_id: uuid.UUID, mode: AnalysisMode) -> bytes:
        runs = await self._all_rows(
            "analysis_runs",
            {
                "select": "id,created_at",
                "client_id": f"eq.{client_id}",
                "input_mode": f"eq.{mode}",
                "order": "created_at.desc",
            },
        )
        output = io.StringIO(newline="")
        fields = [
            "analysis_run_id",
            "analysis_mode",
            "analysed_at",
            "transaction_id",
            "input_columns",
            "model_identifier",
            "predicted_output",
            "risk_score",
            "threshold",
            "top_contributed_features",
            "reasoning",
            "explanation_status",
            "transaction_status",
            "error_code",
            "error_message",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            detail = await self.get_run(client_id=client_id, run_id=str(run["id"]))
            if detail is None:
                continue
            for transaction in detail["transactions"]:
                base = {
                    "analysis_run_id": run["id"],
                    "analysis_mode": mode,
                    "analysed_at": run["created_at"],
                    "transaction_id": transaction["raw_transaction_id"] or transaction["transaction_id"] or "",
                    "input_columns": json.dumps(transaction["input_payload"], separators=(",", ":"), sort_keys=True),
                    "transaction_status": transaction["status"],
                    "error_code": transaction["error_code"] or "",
                    "error_message": transaction["error_message"] or "",
                }
                if not transaction["predictions"]:
                    writer.writerow(
                        {
                            **base,
                            "model_identifier": "",
                            "predicted_output": "",
                            "risk_score": "",
                            "threshold": "",
                            "top_contributed_features": "Not generated",
                            "reasoning": "Not generated",
                            "explanation_status": "NOT_GENERATED",
                        }
                    )
                    continue
                for prediction in transaction["predictions"]:
                    explanation_status = prediction["explanation_status"]
                    writer.writerow(
                        {
                            **base,
                            "model_identifier": prediction["model_identifier"],
                            "predicted_output": "Fraud" if prediction["decision"] else "Legitimate",
                            "risk_score": prediction["risk_score"],
                            "threshold": prediction["threshold"],
                            "top_contributed_features": (
                                json.dumps(prediction["top_contributed_features"], separators=(",", ":"))
                                if explanation_status == "COMPLETED"
                                else "Not generated"
                            ),
                            "reasoning": (
                                prediction["reasoning"] or "No behavioral reasoning available"
                                if explanation_status == "COMPLETED"
                                else "Not generated"
                            ),
                            "explanation_status": explanation_status,
                        }
                    )
        return output.getvalue().encode("utf-8-sig")

    async def _insert_run(
        self,
        *,
        run_id: str,
        client_id: uuid.UUID,
        mode: AnalysisMode,
        selected_models: list[str],
        source_name: str | None,
        total_transactions: int,
        stream_run_id: str | None = None,
    ) -> None:
        rows = await self.client.request(
            "POST",
            "analysis_runs",
            body={
                "id": run_id,
                "client_id": str(client_id),
                "input_mode": mode,
                "source_name": source_name,
                "stream_run_id": stream_run_id,
                "selected_models": selected_models,
                "status": "PROCESSING",
                "total_transactions": total_transactions,
            },
            prefer="return=representation",
        )
        if len(rows) != 1:
            raise SupabaseRepositoryError("Supabase did not return the analysis run")

    async def _insert_predictions(
        self, transaction_record_id: str, predictions: list[dict[str, Any]]
    ) -> dict[str, str]:
        body = [
            {
                "analysis_transaction_id": transaction_record_id,
                "model_identifier": prediction["model_identifier"],
                "model_name": prediction["model_name"],
                "model_version": prediction["model_version"],
                "model_run_id": prediction["run_id"],
                "risk_score": prediction["risk_score"],
                "threshold": prediction["threshold"],
                "decision": prediction["decision"],
                "latency_ms": prediction["latency_ms"],
            }
            for prediction in predictions
        ]
        if not body:
            return {}
        rows = await self.client.request(
            "POST",
            "analysis_prediction_results",
            body=body,
            prefer="return=representation",
        )
        if len(rows) != len(body):
            raise SupabaseRepositoryError("Not every model prediction was persisted")
        return {str(row["model_identifier"]): str(row["id"]) for row in rows}

    async def _complete_run(
        self,
        run_id: str,
        *,
        status: str,
        successful: int,
        failed: int,
        summary: dict[str, Any],
    ) -> None:
        await self.client.request(
            "PATCH",
            "analysis_runs",
            params={"id": f"eq.{run_id}"},
            body={
                "status": status,
                "successful_transactions": successful,
                "failed_transactions": failed,
                "summary": summary,
                "updated_at": _now_iso(),
            },
            prefer="return=minimal",
        )

    async def _all_rows(
        self, table: str, params: dict[str, str]
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = await self.client.request(
                "GET",
                table,
                params={**params, "limit": str(self.PAGE_SIZE), "offset": str(offset)},
            )
            rows.extend(page)
            if len(page) < self.PAGE_SIZE:
                return rows
            offset += self.PAGE_SIZE

    @staticmethod
    def _clean_input(input_payload: dict[str, Any]) -> dict[str, Any]:
        clean = dict(input_payload)
        clean.pop("isFraud", None)
        return clean

    @staticmethod
    def _explanation_response(
        prediction: dict[str, Any], transaction_id: int
    ) -> dict[str, Any]:
        return {
            "transaction_id": transaction_id,
            "model_identifier": prediction["model_identifier"],
            "method": "local_feature_contribution",
            "explanation_technique": prediction["explanation_technique"],
            "explanation_technique_label": prediction["explanation_technique_label"],
            "important_features": prediction["top_contributed_features"] or [],
            "behavioral_explanation": prediction["reasoning"],
            "behavioral_explanation_source": prediction["reasoning_source"],
        }
