"""Environment-only application settings; secrets are never stored in source."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    raw_input_schema_path: Path = Path("config/raw_input_schema.json")
    demo_dataset_path: Path = Path("data/processed/v2/test.parquet")
    behavioral_reference_path: Path = Path(
        "data/processed/v2/behavioral_reference.joblib"
    )
    deployment_artifact_contract_path: Path = Path(
        "config/deployment_artifacts.json"
    )
    model_cache_size: int = Field(default=2, ge=1, le=8)
    model_cpu_threads: int = Field(default=1, ge=1, le=16)
    batch_max_file_bytes: int = Field(default=5_000_000, ge=1)
    batch_max_rows: int = Field(default=1_000, ge=1, le=10_000)
    batch_chunk_size: int = Field(default=100, ge=1, le=1_000)

    supabase_url: str | None = None
    supabase_secret_key: SecretStr | None = None

    r2_endpoint_url: str | None = None
    r2_access_key_id: SecretStr | None = None
    r2_secret_access_key: SecretStr | None = None
    r2_bucket_name: str | None = None

    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = "openrouter/free"
    openrouter_timeout_seconds: float = Field(default=30.0, ge=1.0, le=30.0)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_secret_key)

    @property
    def r2_configured(self) -> bool:
        return bool(
            self.r2_endpoint_url
            and self.r2_access_key_id
            and self.r2_secret_access_key
            and self.r2_bucket_name
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
