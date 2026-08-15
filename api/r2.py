"""Server-side Cloudflare R2 connectivity checks."""

from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .settings import Settings


def create_r2_client(settings: Settings, *, healthcheck: bool = False):
    endpoint = settings.r2_endpoint_url
    access_key = settings.r2_access_key_id
    secret_key = settings.r2_secret_access_key
    assert endpoint is not None
    assert access_key is not None
    assert secret_key is not None
    return boto3.client(
        service_name="s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key.get_secret_value(),
        aws_secret_access_key=secret_key.get_secret_value(),
        region_name="auto",
        config=(
            Config(
                connect_timeout=3,
                read_timeout=5,
                retries={"max_attempts": 1, "mode": "standard"},
            )
            if healthcheck
            else Config(
                connect_timeout=10,
                read_timeout=120,
                retries={"max_attempts": 3, "mode": "standard"},
            )
        ),
    )


class R2Gateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _check_connection_sync(self) -> dict[str, Any]:
        endpoint = self._settings.r2_endpoint_url
        access_key = self._settings.r2_access_key_id
        secret_key = self._settings.r2_secret_access_key
        bucket = self._settings.r2_bucket_name
        assert endpoint is not None
        assert access_key is not None
        assert secret_key is not None
        assert bucket is not None

        client = create_r2_client(self._settings, healthcheck=True)
        client.head_bucket(Bucket=bucket)
        return {
            "configured": True,
            "reachable": True,
            "detail": "ok",
        }

    async def check_connection(self) -> dict[str, Any]:
        if not self._settings.r2_configured:
            return {
                "configured": False,
                "reachable": False,
                "detail": "credentials not configured",
            }

        try:
            return await asyncio.to_thread(self._check_connection_sync)
        except (BotoCoreError, ClientError, ValueError) as exc:
            return {
                "configured": True,
                "reachable": False,
                "detail": type(exc).__name__,
            }
