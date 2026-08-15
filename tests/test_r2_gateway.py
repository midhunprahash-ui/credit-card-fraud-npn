import asyncio

from api.r2 import R2Gateway
from api.settings import Settings


def test_r2_gateway_lists_private_bucket_with_auto_region(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class StubS3Client:
        def head_bucket(self, **kwargs):
            captured["request"] = kwargs

    def stub_client(**kwargs):
        captured["client"] = kwargs
        return StubS3Client()

    monkeypatch.setattr("api.r2.boto3.client", stub_client)
    gateway = R2Gateway(
        Settings(
            r2_endpoint_url="https://example.r2.cloudflarestorage.com",
            r2_access_key_id="access-test-only",
            r2_secret_access_key="secret-test-only",
            r2_bucket_name="fraud-model-artifacts",
        )
    )

    result = asyncio.run(gateway.check_connection())

    assert result == {
        "configured": True,
        "reachable": True,
        "detail": "ok",
    }
    client_options = captured["client"]
    assert isinstance(client_options, dict)
    config = client_options.pop("config")
    assert client_options == {
        "service_name": "s3",
        "endpoint_url": "https://example.r2.cloudflarestorage.com",
        "aws_access_key_id": "access-test-only",
        "aws_secret_access_key": "secret-test-only",
        "region_name": "auto",
    }
    assert config.connect_timeout == 3
    assert config.read_timeout == 5
    assert config.retries == {"max_attempts": 1, "mode": "standard"}
    assert captured["request"] == {"Bucket": "fraud-model-artifacts"}


def test_r2_gateway_reports_unconfigured_without_network_access() -> None:
    result = asyncio.run(R2Gateway(Settings()).check_connection())

    assert result == {
        "configured": False,
        "reachable": False,
        "detail": "credentials not configured",
    }
