# Kaggle inference sample

## Purpose

`kaggle_inference_sample` contains 100 real transactions from the official
IEEE-CIS Kaggle competition test files. It is for production-style inference,
TransactionID lookup, CSV testing, and FIFO replay.

The sample is not an accuracy test. Kaggle does not provide `isFraud` for these
transactions. The simplified application does not show a Ground Truth column;
it shows only the model's Fraud or Not Fraud classification, risk score, and
saved threshold.

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

Create the ready-to-upload 100-row CSV:

```bash
.venv/bin/python scripts/upload_kaggle_inference_sample.py \
  --csv-output data/samples/kaggle_inference_sample_100.csv
```

The exported CSV contains all 433 raw model-input columns in schema order.
Missing values are blank, and `isFraud` is not included. It can be uploaded
directly in the application's CSV Upload mode.

Upload with server-side Supabase settings in the local environment:

```bash
.venv/bin/python scripts/upload_kaggle_inference_sample.py
```

## Application behavior

- Single JSON mode loads a complete stored payload from a TransactionID.
- CSV Upload accepts `data/samples/kaggle_inference_sample_100.csv` directly.
- Real-time exposes this as the only selectable dataset and processes all 100
  rows in strict chronological FIFO order.
- Predictions include model, Fraud/Not Fraud decision, score, and threshold in
  the common results table.
- Opening a row shows its non-null inputs and on-demand local contributions.
- Ground truth is never inferred from the model prediction.
- The labelled `demo_chronological` dataset remains available separately for
  controlled evaluation, but is hidden from the simplified UI.
