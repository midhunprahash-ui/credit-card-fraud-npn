import asyncio

from api.demo_repository import SupabaseDemoTransactionRepository
from api.stream_repository import SupabaseStreamRepository


class FakeClient:
    def __init__(self) -> None:
        self.calls = []

    async def request(self, method, table, **kwargs):
        self.calls.append((method, table, kwargs))
        if table == "stream_datasets":
            return [{"id": "dataset-1"}]
        if kwargs["params"]["select"] == "transaction_payload":
            return [{"transaction_payload": {"TransactionID": 10, "isFraud": 1}}]
        return [
            {
                "transaction_id": 10,
                "transaction_dt": 100.0,
                "transaction_payload": {
                    "TransactionID": 10,
                    "TransactionAmt": 25.0,
                    "ProductCD": "W",
                    "DeviceType": "mobile",
                },
            }
        ]


def test_supabase_demo_repository_never_returns_hidden_label() -> None:
    async def scenario() -> None:
        client = FakeClient()
        repository = SupabaseDemoTransactionRepository(
            SupabaseStreamRepository(client)
        )

        summary = await repository.list(limit=10, offset=0)
        payload = await repository.get(10)

        assert summary == [
            {
                "transaction_id": 10,
                "transaction_dt": 100.0,
                "transaction_amount": 25.0,
                "product_code": "W",
                "has_identity": True,
            }
        ]
        assert payload == {"TransactionID": 10}
        dataset_calls = [call for call in client.calls if call[1] == "stream_datasets"]
        assert len(dataset_calls) == 1

    asyncio.run(scenario())
