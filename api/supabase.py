"""Minimal server-side Supabase Data API client."""

from __future__ import annotations

from typing import Any

import httpx

from .settings import Settings


class SupabaseGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check_connection(self) -> dict[str, Any]:
        if not self._settings.supabase_configured:
            return {"configured": False, "reachable": False, "detail": "credentials not configured"}

        secret = self._settings.supabase_secret_key
        assert secret is not None
        # Supabase's sb_secret_* keys authenticate through ``apikey``. They are
        # not JWTs and must not be presented as Authorization bearer tokens.
        headers = {"apikey": secret.get_secret_value()}
        url = f"{self._settings.supabase_url.rstrip('/')}/rest/v1/stream_datasets"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"select": "id", "limit": "1"},
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return {
                "configured": True,
                "reachable": False,
                "detail": type(exc).__name__,
            }
        return {"configured": True, "reachable": True, "detail": "ok"}
