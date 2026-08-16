import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import upload_kaggle_inference_sample, upload_stream_datasets


FIXTURE = Path(__file__).parent / "fixtures/stream_sample.json"


def test_safe_stream_fixture_is_fifo_and_keeps_labels_outside_payloads() -> None:
    document = json.loads(FIXTURE.read_text())
    rows = document["transactions"]
    keys = [
        (row["transaction_dt"], row["transaction_id"])
        for row in rows
    ]
    assert keys == sorted(keys)
    assert [row["sequence_number"] for row in rows] == list(range(len(rows)))
    assert all("isFraud" not in row["transaction_payload"] for row in rows)
    assert all(isinstance(row["actual_label"], bool) for row in rows)
    assert document["distribution_changed"] is False


def test_upload_preparation_strips_target_and_numbers_fifo_rows(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "held_out.parquet"
    pd.DataFrame(
        {
            "TransactionID": [10, 11, 12],
            "TransactionDT": [1.0, 2.0, 2.0],
            "TransactionAmt": [5.0, 6.0, 7.0],
            "isFraud": [0, 1, 0],
        }
    ).to_parquet(source, index=False)
    monkeypatch.setattr(upload_stream_datasets, "EXPECTED_HELD_OUT_ROWS", 3)
    monkeypatch.setattr(
        upload_stream_datasets,
        "raw_columns",
        lambda: ["TransactionID", "TransactionDT", "TransactionAmt"],
    )

    batches = list(
        upload_stream_datasets.iter_source_rows(
            source, row_limit=3, batch_size=2
        )
    )
    rows = [row for batch in batches for row in batch]
    assert [row["sequence_number"] for row in rows] == [0, 1, 2]
    assert [row["actual_label"] for row in rows] == [False, True, False]
    assert all("isFraud" not in row["transaction_payload"] for row in rows)


def test_upload_preparation_rejects_non_chronological_source(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "unordered.parquet"
    pd.DataFrame(
        {
            "TransactionID": [10, 11],
            "TransactionDT": [2.0, 1.0],
            "isFraud": [0, 0],
        }
    ).to_parquet(source, index=False)
    monkeypatch.setattr(upload_stream_datasets, "EXPECTED_HELD_OUT_ROWS", 2)
    monkeypatch.setattr(
        upload_stream_datasets,
        "raw_columns",
        lambda: ["TransactionID", "TransactionDT"],
    )

    with pytest.raises(ValueError, match="chronological FIFO order"):
        list(
            upload_stream_datasets.iter_source_rows(
                source, row_limit=2, batch_size=2
            )
        )


def test_kaggle_sample_joins_identity_and_has_no_ground_truth(
    tmp_path: Path, monkeypatch
) -> None:
    transactions = tmp_path / "test_transaction.csv"
    identities = tmp_path / "test_identity.csv"
    pd.DataFrame(
        {
            "TransactionID": [20, 21],
            "TransactionDT": [2.0, 1.0],
            "TransactionAmt": [50.0, 75.0],
        }
    ).to_csv(transactions, index=False)
    pd.DataFrame(
        {
            "TransactionID": [20],
            "id-01": [3.5],
        }
    ).to_csv(identities, index=False)
    monkeypatch.setattr(
        upload_kaggle_inference_sample,
        "raw_columns",
        lambda: ["TransactionID", "TransactionDT", "TransactionAmt", "id_01"],
    )

    rows = upload_kaggle_inference_sample.prepare_rows(
        transactions, identities, row_limit=2
    )

    assert [row["transaction_id"] for row in rows] == [21, 20]
    assert [row["sequence_number"] for row in rows] == [0, 1]
    assert rows[1]["transaction_payload"]["id_01"] == 3.5
    assert "id_01" not in rows[0]["transaction_payload"]
    assert all("isFraud" not in row["transaction_payload"] for row in rows)
    assert all("actual_label" not in row for row in rows)

    output = tmp_path / "kaggle_sample.csv"
    upload_kaggle_inference_sample.export_csv(rows, output)
    exported = pd.read_csv(output)

    assert list(exported.columns) == [
        "TransactionID",
        "TransactionDT",
        "TransactionAmt",
        "id_01",
    ]
    assert exported["TransactionID"].tolist() == [21, 20]
    assert pd.isna(exported.loc[0, "id_01"])
    assert exported.loc[1, "id_01"] == 3.5
