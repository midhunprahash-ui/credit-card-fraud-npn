"""FastAPI entry point for the fraud analyst application."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .catalog import VersionName, load_model_catalog
from .r2 import R2Gateway
from .settings import Settings, get_settings
from .supabase import SupabaseGateway


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    catalog = load_model_catalog()
    r2 = R2Gateway(active_settings)
    supabase = SupabaseGateway(active_settings)

    app = FastAPI(
        title="NPN Fraud Analyst API",
        version="0.1.0",
        description="V1/V2 fraud model orchestration for manual and real-time analysis.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "NPN Fraud Analyst API", "docs": "/docs"}

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "environment": active_settings.environment,
            "models_registered": len(catalog),
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
        selected = [item for item in catalog if version is None or item["version_name"] == version]
        return {"versions": ["V1", "V2"], "models": selected}

    return app


app = create_app()
