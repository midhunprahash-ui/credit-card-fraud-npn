import asyncio

import httpx

from api.settings import Settings
from api.supabase import SupabaseGateway


def test_secret_key_is_sent_only_as_supabase_apikey(monkeypatch) -> None:
    captured_headers: dict[str, str] = {}

    class StubAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 5.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def get(self, url, *, headers, params):
            captured_headers.update(headers)
            request = httpx.Request("GET", url, headers=headers)
            return httpx.Response(200, request=request, json=[])

    monkeypatch.setattr("api.supabase.httpx.AsyncClient", StubAsyncClient)
    gateway = SupabaseGateway(
        Settings(
            supabase_url="https://example.supabase.co",
            supabase_secret_key="sb_secret_test-only",
        )
    )

    result = asyncio.run(gateway.check_connection())

    assert result == {"configured": True, "reachable": True, "detail": "ok"}
    assert captured_headers == {"apikey": "sb_secret_test-only"}
