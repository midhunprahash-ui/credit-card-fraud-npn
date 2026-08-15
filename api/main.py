"""FastAPI entry point for manual fraud-risk analysis."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Path as ApiPath, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from src.fraud_pipeline.input_contract import RawInputContract
from src.fraud_pipeline.model_manager import ModelManager
from src.fraud_pipeline.registry import ModelRegistry

from .catalog import PROJECT_ROOT, VersionName, load_model_catalog
from .demo_repository import DemoTransactionRepository
from .errors import ApiError
from .logging_config import configure_logging
from .r2 import R2Gateway
from .schemas import BatchPredictionResponse, PredictionRequest, PredictionResponse
from .services import (
    BatchPredictionService,
    BehavioralReferenceProvider,
    PredictionService,
    RuntimeMetrics,
    build_batch_download,
    parse_model_identifiers,
)
from .settings import Settings, get_settings
from .supabase import SupabaseGateway


LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    prediction_service: PredictionService | Any | None = None,
    batch_service: BatchPredictionService | Any | None = None,
    demo_repository: DemoTransactionRepository | Any | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    registry = ModelRegistry.load(PROJECT_ROOT)
    catalog = load_model_catalog()
    raw_contract = RawInputContract.load(
        _resolve_project_path(active_settings.raw_input_schema_path)
    )
    model_manager = ModelManager(
        registry, max_loaded_models=active_settings.model_cache_size
    )
    metrics = RuntimeMetrics()
    reference_provider = BehavioralReferenceProvider(
        _resolve_project_path(active_settings.behavioral_reference_path)
    )
    active_prediction_service = prediction_service or PredictionService(
        registry,
        raw_contract,
        model_manager,
        reference_provider,
        metrics,
    )
    active_batch_service = batch_service or BatchPredictionService(
        active_prediction_service,
        max_file_bytes=active_settings.batch_max_file_bytes,
        max_rows=active_settings.batch_max_rows,
        chunk_size=active_settings.batch_chunk_size,
    )
    active_demo_repository = demo_repository or DemoTransactionRepository(
        _resolve_project_path(active_settings.demo_dataset_path), raw_contract
    )
    r2 = R2Gateway(active_settings)
    supabase = SupabaseGateway(active_settings)

    app = FastAPI(
        title="NPN Fraud Intelligence API",
        version="0.2.0",
        description="Verified V1/V2 fraud-risk inference for manual analyst workflows.",
    )
    app.state.model_manager = model_manager
    app.state.metrics = metrics
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            LOGGER.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1_000, 3),
            },
        )
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "The request does not match the API contract",
                    "details": jsonable_encoder(error.errors()),
                }
            },
        )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "NPN Fraud Intelligence API", "docs": "/docs"}

    @app.get("/health")
    async def health() -> dict[str, object]:
        available_artifacts = sum(
            spec.artifact_directory.is_dir() for spec in registry
        )
        return {
            "status": "ok",
            "environment": active_settings.environment,
            "models_registered": len(catalog),
            "model_artifacts_available": available_artifacts,
            "supabase_configured": active_settings.supabase_configured,
            "r2_configured": active_settings.r2_configured,
        }

    @app.get("/integrations")
    async def integrations() -> dict[str, object]:
        return {
            "supabase": await supabase.check_connection(),
            "cloudflare_r2": await r2.check_connection(),
        }

    @app.get("/models")
    async def models(
        version: VersionName | None = Query(default=None),
    ) -> dict[str, object]:
        selected = [
            item
            for item in catalog
            if version is None or item["version_name"] == version
        ]
        status = {
            item["model_identifier"]: item
            for item in model_manager.status()["models"]
        }
        return {
            "versions": ["V1", "V2"],
            "models": [
                {**item, "loading_status": status[item["model_identifier"]]["status"]}
                for item in selected
            ],
        }

    @app.get("/input-schema")
    async def input_schema() -> dict[str, object]:
        return {
            "join": {"type": "left", "key": raw_contract.identifier_column},
            "target_excluded": raw_contract.target_column,
            "required_fields": [raw_contract.identifier_column, "TransactionDT"],
            "optional_fields": [
                column
                for column in raw_contract.columns
                if column not in {raw_contract.identifier_column, "TransactionDT"}
            ],
            "accepted_input_modes": ["json", "one_row_csv", "batch_csv"],
            "batch_limits": {
                "maximum_file_bytes": active_settings.batch_max_file_bytes,
                "maximum_rows": active_settings.batch_max_rows,
                "chunk_size": active_settings.batch_chunk_size,
            },
        }

    @app.get("/demo-transactions")
    async def demo_transactions(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        transactions = await run_in_threadpool(
            active_demo_repository.list, limit=limit, offset=offset
        )
        return {
            "dataset": "held_out_full",
            "split": "chronological_test",
            "labels_hidden": True,
            "transactions": transactions,
        }

    @app.get("/transactions/{transaction_id}")
    async def transaction(
        transaction_id: int = ApiPath(ge=1),
    ) -> dict[str, object]:
        payload = await run_in_threadpool(
            active_demo_repository.get, transaction_id
        )
        return {
            "transaction_id": transaction_id,
            "labels_hidden": True,
            "transaction_payload": payload,
        }

    @app.post("/predict", response_model=PredictionResponse)
    async def predict(request: PredictionRequest) -> dict[str, Any]:
        return await run_in_threadpool(
            active_prediction_service.predict,
            request.transaction,
            request.model_identifiers,
        )

    @app.post("/predict/file", response_model=PredictionResponse)
    async def predict_single_csv(
        file: UploadFile = File(...),
        models: str = Form(...),
    ) -> dict[str, Any]:
        model_identifiers = _validated_form_models(models, registry)
        content = await file.read(active_settings.batch_max_file_bytes + 1)
        await file.close()
        return await run_in_threadpool(
            active_batch_service.process_one,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
            model_identifiers=model_identifiers,
        )

    @app.post("/predict/batch", response_model=BatchPredictionResponse)
    async def predict_batch(
        file: UploadFile = File(...),
        models: str = Form(...),
        response_format: str = Form(default="json", pattern="^(json|zip)$"),
    ) -> dict[str, Any] | Response:
        model_identifiers = _validated_form_models(models, registry)
        content = await file.read(active_settings.batch_max_file_bytes + 1)
        await file.close()
        report = await run_in_threadpool(
            active_batch_service.process,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
            model_identifiers=model_identifiers,
        )
        if response_format == "zip":
            content = await run_in_threadpool(build_batch_download, report)
            return Response(
                content=content,
                media_type="application/zip",
                headers={
                    "Content-Disposition": 'attachment; filename="fraud_batch_results.zip"'
                },
            )
        return report

    @app.get("/metrics/summary")
    async def metrics_summary() -> dict[str, object]:
        return {
            "runtime": metrics.summary(),
            "model_manager": model_manager.status(),
        }

    return app


def _resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _validated_form_models(value: str, registry: ModelRegistry) -> list[str]:
    identifiers = parse_model_identifiers(value)
    try:
        for identifier in identifiers:
            registry.get(identifier)
    except ValueError as error:
        raise ApiError(422, "invalid_model_selection", str(error)) from error
    return identifiers


app = create_app()
