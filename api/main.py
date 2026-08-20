"""FastAPI entry point for manual fraud-risk analysis."""

from __future__ import annotations

import inspect
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, Path as ApiPath, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

from src.fraud_pipeline.deployment_artifacts import (
    DeploymentArtifactContract,
    R2ArtifactStore,
)
from src.fraud_pipeline.input_contract import RawInputContract
from src.fraud_pipeline.model_adapters import load_model_adapter
from src.fraud_pipeline.model_manager import ModelManager
from src.fraud_pipeline.registry import ModelRegistry

from .catalog import PROJECT_ROOT, VersionName, load_model_catalog
from .demo_repository import (
    DemoTransactionRepository,
    SupabaseDemoTransactionRepository,
)
from .errors import ApiError
from .logging_config import configure_logging
from .r2 import R2Gateway, create_r2_client
from .schemas import (
    AlertActionRequest,
    BatchPredictionResponse,
    ExplanationRequest,
    ExplanationResponse,
    PredictionRequest,
    PredictionResponse,
    StreamStartRequest,
)
from .services import (
    BatchPredictionService,
    BehavioralReferenceProvider,
    PredictionService,
    RuntimeMetrics,
    build_batch_download,
    parse_model_identifiers,
)
from .settings import Settings, get_settings
from .stream_repository import (
    SupabaseRepositoryError,
    SupabaseRestClient,
    SupabaseStreamRepository,
)
from .streaming import StreamController
from .supabase import SupabaseGateway


LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    prediction_service: PredictionService | Any | None = None,
    batch_service: BatchPredictionService | Any | None = None,
    demo_repository: DemoTransactionRepository | Any | None = None,
    stream_controller: StreamController | Any | None = None,
    alert_repository: SupabaseStreamRepository | Any | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    registry = ModelRegistry.load(PROJECT_ROOT)
    catalog = load_model_catalog()
    raw_contract = RawInputContract.load(
        _resolve_project_path(active_settings.raw_input_schema_path)
    )
    artifact_store: R2ArtifactStore | None = None
    if active_settings.r2_configured:
        contract = DeploymentArtifactContract.load(
            _resolve_project_path(active_settings.deployment_artifact_contract_path),
            PROJECT_ROOT,
        )
        assert active_settings.r2_bucket_name is not None
        artifact_store = R2ArtifactStore(
            client=create_r2_client(active_settings),
            bucket=active_settings.r2_bucket_name,
            contract=contract,
        )

    def model_loader(spec):
        if artifact_store is not None:
            artifact_store.ensure_model(spec)
            return load_model_adapter(
                spec,
                verify_manifest=False,
                model_cpu_threads=active_settings.model_cpu_threads,
            )
        return load_model_adapter(
            spec,
            model_cpu_threads=active_settings.model_cpu_threads,
        )

    model_manager = ModelManager(
        registry,
        max_loaded_models=active_settings.model_cache_size,
        loader=model_loader,
    )
    metrics = RuntimeMetrics()
    reference_provider = BehavioralReferenceProvider(
        _resolve_project_path(active_settings.behavioral_reference_path),
        ensure_available=(
            lambda: artifact_store.ensure_runtime("behavioral_reference.v2")
            if artifact_store is not None
            else None
        ),
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
    active_demo_repository = demo_repository
    supabase_rest_client: SupabaseRestClient | None = None
    active_stream_controller = stream_controller
    active_alert_repository = alert_repository
    if active_settings.supabase_configured and (
        active_stream_controller is None or active_alert_repository is None
    ):
        supabase_rest_client = SupabaseRestClient(active_settings)
        repository = SupabaseStreamRepository(supabase_rest_client)
        if active_stream_controller is None:
            active_stream_controller = StreamController(
                repository,
                registry,
                model_manager,
                active_prediction_service,
                reference_provider,
                raw_contract,
            )
        if active_alert_repository is None:
            active_alert_repository = repository
        if active_demo_repository is None:
            active_demo_repository = SupabaseDemoTransactionRepository(repository)
    if active_demo_repository is None:
        active_demo_repository = DemoTransactionRepository(
            _resolve_project_path(active_settings.demo_dataset_path), raw_contract
        )
    r2 = R2Gateway(active_settings)
    supabase = SupabaseGateway(active_settings)

    app = FastAPI(
        title="NPN Fraud Intelligence API",
        version="0.5.0",
        description="Cloud-ready verified V1/V2 fraud intelligence API.",
    )
    app.state.model_manager = model_manager
    app.state.metrics = metrics
    app.state.stream_controller = active_stream_controller
    app.state.alert_repository = active_alert_repository
    if supabase_rest_client is not None:
        app.router.add_event_handler("shutdown", supabase_rest_client.close)
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
            "artifact_source": "r2_lazy_cache" if artifact_store else "local",
            "behavioral_reference_available": reference_provider.path.is_file(),
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
        transactions = await _repository_call(
            active_demo_repository.list, limit=limit, offset=offset
        )
        return {
            "dataset": getattr(active_demo_repository, "dataset_name", "held_out_full"),
            "split": getattr(active_demo_repository, "split", "chronological_test"),
            "labels_available": getattr(
                active_demo_repository, "labels_available", True
            ),
            "labels_hidden": True,
            "transactions": transactions,
        }

    @app.get("/transactions/{transaction_id}")
    async def transaction(
        transaction_id: int = ApiPath(ge=1),
    ) -> dict[str, object]:
        payload = await _repository_call(active_demo_repository.get, transaction_id)
        return {
            "transaction_id": transaction_id,
            "labels_available": getattr(
                active_demo_repository, "labels_available", True
            ),
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

    @app.post("/explain", response_model=ExplanationResponse)
    async def explain(request: ExplanationRequest) -> dict[str, Any]:
        return await run_in_threadpool(
            active_prediction_service.explain,
            request.transaction,
            request.model_identifier,
            request.decision,
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
            "stream": (
                active_stream_controller.snapshot()
                if active_stream_controller is not None
                else {"status": "UNAVAILABLE"}
            ),
        }

    @app.get("/stream/datasets")
    async def stream_datasets() -> dict[str, object]:
        controller = _require_stream_controller(active_stream_controller)
        return {"datasets": await controller.list_datasets()}

    @app.post("/stream/start")
    async def stream_start(request: StreamStartRequest) -> dict[str, Any]:
        controller = _require_stream_controller(active_stream_controller)
        return await controller.start(
            dataset_id=request.dataset_id,
            selected_models=request.selected_models,
            transactions_per_second=request.transactions_per_second,
        )

    @app.post("/stream/pause")
    async def stream_pause() -> dict[str, Any]:
        return await _require_stream_controller(active_stream_controller).pause()

    @app.post("/stream/resume")
    async def stream_resume() -> dict[str, Any]:
        return await _require_stream_controller(active_stream_controller).resume()

    @app.post("/stream/stop")
    async def stream_stop() -> dict[str, Any]:
        return await _require_stream_controller(active_stream_controller).stop()

    @app.post("/stream/restart")
    async def stream_restart() -> dict[str, Any]:
        return await _require_stream_controller(active_stream_controller).restart()

    @app.get("/stream/status")
    async def stream_status() -> dict[str, Any]:
        return _require_stream_controller(active_stream_controller).snapshot()

    @app.get("/stream/events")
    async def stream_events(request: Request) -> StreamingResponse:
        controller = _require_stream_controller(active_stream_controller)

        async def event_source():
            yield _format_sse("stream_status", controller.snapshot())
            async for event in controller.broker.subscribe():
                if await request.is_disconnected():
                    break
                yield _format_sse(event["event"], event["data"])

        return StreamingResponse(
            event_source(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/alerts")
    async def alerts(
        status: Literal[
            "OPEN",
            "IN_REVIEW",
            "CONFIRMED_FRAUD",
            "LEGITIMATE",
            "ESCALATED",
            "CLOSED",
        ]
        | None = Query(default=None),
        transaction_id: int | None = Query(default=None, ge=1),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        repository = _require_alert_repository(active_alert_repository)
        try:
            items = await repository.list_alerts(
                limit=limit,
                status=status,
                transaction_id=transaction_id,
            )
        except SupabaseRepositoryError as error:
            raise ApiError(
                503, "alert_store_unavailable", "Fraud alert history is unavailable"
            ) from error
        return {"alerts": items}

    @app.get("/alerts/{alert_id}")
    async def alert_detail(alert_id: uuid.UUID) -> dict[str, Any]:
        repository = _require_alert_repository(active_alert_repository)
        try:
            item = await repository.get_alert(str(alert_id))
        except SupabaseRepositoryError as error:
            raise ApiError(
                503, "alert_store_unavailable", "Fraud alert history is unavailable"
            ) from error
        if item is None:
            raise ApiError(404, "fraud_alert_not_found", "Fraud alert was not found")
        return item

    @app.post("/alerts/{alert_id}/actions")
    async def alert_action(
        alert_id: uuid.UUID, request: AlertActionRequest
    ) -> dict[str, Any]:
        repository = _require_alert_repository(active_alert_repository)
        try:
            action = await repository.add_alert_action(
                str(alert_id),
                action=request.action,
                analyst_identifier=request.analyst_identifier,
                note=request.note,
            )
        except SupabaseRepositoryError as error:
            raise ApiError(
                503, "alert_store_unavailable", "The analyst action could not be saved"
            ) from error
        return {"analyst_action": action}

    return app


def _resolve_project_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


async def _repository_call(method, *args, **kwargs):
    if inspect.iscoroutinefunction(method):
        return await method(*args, **kwargs)
    return await run_in_threadpool(method, *args, **kwargs)


def _validated_form_models(value: str, registry: ModelRegistry) -> list[str]:
    identifiers = parse_model_identifiers(value)
    try:
        for identifier in identifiers:
            registry.get(identifier)
    except ValueError as error:
        raise ApiError(422, "invalid_model_selection", str(error)) from error
    return identifiers


def _require_stream_controller(controller: StreamController | Any | None):
    if controller is None:
        raise ApiError(
            503,
            "streaming_unavailable",
            "Streaming requires server-side Supabase credentials",
        )
    return controller


def _require_alert_repository(repository: SupabaseStreamRepository | Any | None):
    if repository is None:
        raise ApiError(
            503,
            "alert_store_unavailable",
            "Alert history requires server-side Supabase credentials",
        )
    return repository


def _format_sse(event_type: str, data: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


app = create_app()
