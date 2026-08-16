from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


class FakeStreamController:
    def __init__(self) -> None:
        self.status = "IDLE"

    async def list_datasets(self):
        return [{"id": "dataset-1", "name": "demo_chronological"}]

    async def start(self, **configuration):
        self.status = "RUNNING"
        return {"status": self.status, **configuration}

    async def pause(self):
        self.status = "PAUSED"
        return self.snapshot()

    async def resume(self):
        self.status = "RUNNING"
        return self.snapshot()

    async def stop(self):
        self.status = "STOPPED"
        return self.snapshot()

    async def restart(self):
        self.status = "RUNNING"
        return self.snapshot()

    def snapshot(self):
        return {"status": self.status}


def test_stream_control_endpoints_use_typed_configuration() -> None:
    controller = FakeStreamController()
    client = TestClient(
        create_app(Settings(_env_file=None), stream_controller=controller)
    )

    datasets = client.get("/stream/datasets")
    assert datasets.status_code == 200
    assert datasets.json()["datasets"][0]["name"] == "demo_chronological"

    started = client.post(
        "/stream/start",
        json={
            "dataset_id": "dataset-1",
            "selected_models": ["catboost.v2"],
            "transactions_per_second": 2,
        },
    )
    assert started.status_code == 200
    assert started.json() == {
        "status": "RUNNING",
        "dataset_id": "dataset-1",
        "selected_models": ["catboost.v2"],
        "transactions_per_second": 2,
    }
    assert client.post("/stream/pause").json()["status"] == "PAUSED"
    assert client.post("/stream/resume").json()["status"] == "RUNNING"
    assert client.get("/stream/status").json()["status"] == "RUNNING"
    assert client.post("/stream/stop").json()["status"] == "STOPPED"


def test_stream_start_rejects_unsupported_rate_and_duplicate_models() -> None:
    client = TestClient(
        create_app(
            Settings(_env_file=None), stream_controller=FakeStreamController()
        )
    )
    response = client.post(
        "/stream/start",
        json={
            "dataset_id": "dataset-1",
            "selected_models": ["catboost.v2", "catboost.v2"],
            "transactions_per_second": 3,
        },
    )
    assert response.status_code == 422


def test_streaming_is_unavailable_without_server_supabase_configuration() -> None:
    client = TestClient(create_app(Settings(_env_file=None)))
    response = client.get("/stream/status")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "streaming_unavailable"
