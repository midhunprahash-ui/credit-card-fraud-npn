import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import upload_stream_datasets


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
