from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings


ALERT_ID = "11111111-1111-4111-8111-111111111111"


class FakeAlertRepository:
    def __init__(self) -> None:
        self.actions = []

    async def list_alerts(self, **filters):
        return [{"id": ALERT_ID, "transaction_id": 3488959, "status": "OPEN"}]

    async def get_alert(self, alert_id):
        if alert_id != ALERT_ID:
            return None
        return {"id": ALERT_ID, "transaction_id": 3488959, "predictions": []}

    async def add_alert_action(self, alert_id, **values):
        action = {"id": "action-1", "fraud_alert_id": alert_id, **values}
        self.actions.append(action)
        return action


def test_alert_queue_detail_and_action_contracts() -> None:
    repository = FakeAlertRepository()
    client = TestClient(create_app(Settings(), alert_repository=repository))

    queue = client.get("/alerts", params={"status": "OPEN", "limit": 10})
    assert queue.status_code == 200
    assert queue.json()["alerts"][0]["transaction_id"] == 3488959

    detail = client.get(f"/alerts/{ALERT_ID}")
    assert detail.status_code == 200
    assert detail.json()["id"] == ALERT_ID

    action = client.post(
        f"/alerts/{ALERT_ID}/actions",
        json={
            "action": "ESCALATED",
            "analyst_identifier": " analyst-7 ",
            "note": "Device pattern requires review",
        },
    )
    assert action.status_code == 200
    assert repository.actions[0]["analyst_identifier"] == "analyst-7"
    assert repository.actions[0]["action"] == "ESCALATED"


def test_alert_contract_rejects_invalid_status_uuid_and_action() -> None:
    client = TestClient(
        create_app(Settings(), alert_repository=FakeAlertRepository())
    )
    assert client.get("/alerts", params={"status": "ANYTHING"}).status_code == 422
    assert client.get("/alerts/not-a-uuid").status_code == 422
    response = client.post(
        f"/alerts/{ALERT_ID}/actions",
        json={"action": "DELETE", "analyst_identifier": "analyst"},
    )
    assert response.status_code == 422


def test_alert_store_requires_server_supabase_configuration() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get("/alerts")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "alert_store_unavailable"
