# CYPHER prediction application

## Purpose

CYPHER is a focused interface for running the saved fraud-classification
models. The trained model makes the Fraud or Not Fraud decision. The user does
not confirm labels, escalate alerts, manage cases, or add analyst notes.

## One-page workflow

1. Select V1, V2, or both.
2. Select one or more matching model pipelines. No model is selected by
   default.
3. Choose Single JSON, CSV Upload, or Real-time.
4. Submit the input or start the replay.
5. Read each model's classification, fraud-risk score, and saved threshold in
   the common spreadsheet-style results table.
6. Open a result row to inspect its supplied inputs and strongest local model
   contributions.

Selecting several models produces independent classifications. The displayed
fraud count is a simple comparison, not a trained ensemble.

The decision rule is always model-specific:

```text
risk score >= saved threshold  → Fraud
risk score <  saved threshold  → Not Fraud
```

The user cannot edit that threshold in the current UI. It was selected on the
validation partition and stored with the approved model artifact.

## Inputs

### Single JSON

Paste one raw joined transaction object. `TransactionID` is required. FastAPI
removes `isFraud`, aligns missing optional fields, applies the selected model's
matching feature engineering and preprocessor, and returns one result per
pipeline.

### CSV Upload

Upload multiple raw transactions in one CSV file. The backend validates the
file and rows, processes accepted rows in chunks, and displays the same result
columns used by Single JSON and Real-time. Prediction and invalid-row reports
remain downloadable.

### Real-time

Replay the 100 official unlabelled Kaggle test transactions in chronological
FIFO order at 1, 2, or 5 transactions per second. The older 600-row labelled
demonstration dataset is not offered in the simplified interface. The
interface shows stream controls, queue state, throughput, latency, and the same
completed-classification table used by the manual modes.

## Common results table

Every selected model produces one independent row with:

- Transaction ID
- Model name and version
- Fraud indicator, highlighted red
- Not-fraud indicator, highlighted green
- Fraud-risk score
- Saved model-specific threshold

Opening a row shows only the non-null inputs supplied for that transaction and
calculates up to five local feature contributions on demand through
`POST /explain`. LightGBM and CatBoost use native per-row contribution support.
Logistic Regression and Neural Network use leave-one-feature-out score
sensitivity. Positive values move the score toward Fraud; negative values move
it toward Not Fraud. Explanations are not calculated during initial prediction,
so they do not slow the FIFO stream. They describe model behaviour and must not
be interpreted as causal reasons for fraud.

`isFraud` is removed before validation, feature engineering, prediction, and
display. The unlabelled Kaggle sample therefore demonstrates the intended use:
classifying transactions whose true outcome is unknown.

## Intentionally not shown

- Alert investigation and prioritisation
- Confirm-fraud or mark-legitimate actions
- Escalation, case status, notes, and analyst audit history
- Overview, model-comparison, and infrastructure-monitoring pages

The underlying API and historical implementation remain available in Git, but
the public interface stays focused on ML classification.
