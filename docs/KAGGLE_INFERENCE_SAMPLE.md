# Kaggle inference sample

## Purpose

`kaggle_inference_sample` contains 100 real transactions from the official
IEEE-CIS Kaggle competition test files. It is for production-style inference,
TransactionID lookup, CSV testing, and FIFO replay.

The sample is not an accuracy test. Kaggle does not provide `isFraud` for these
transactions, so the application displays ground truth as **Not available**.

## Preparation

The upload script:

1. Reads the first 100 `test_transaction.csv` rows.
2. Finds matching `test_identity.csv` rows using `TransactionID`.
3. Renames Kaggle identity fields such as `id-01` to the training schema form
   `id_01`.
4. Performs a validated left join.
5. Aligns the result with all 433 raw input columns.
6. Orders rows by `TransactionDT`, then `TransactionID`.
7. Omits null JSON values and never adds `isFraud`.

The source CSV files remain ignored and are never committed.

Validate locally:

```bash
.venv/bin/python scripts/upload_kaggle_inference_sample.py --dry-run
```

Upload with server-side Supabase settings in the local environment:

```bash
.venv/bin/python scripts/upload_kaggle_inference_sample.py
```

## Application behavior

- Single JSON mode loads a complete stored payload from a TransactionID.
- Real-time mode identifies the dataset as unlabelled.
- Predictions still include model score, threshold, decision, and latency.
- Ground truth is never inferred from the model prediction.
- The labelled `demo_chronological` dataset remains available separately for
  evaluation demonstrations.
