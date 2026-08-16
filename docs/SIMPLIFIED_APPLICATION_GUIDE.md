# CYPHER prediction application

## Purpose

CYPHER is a focused interface for running the saved fraud-classification
models. The trained model makes the Fraud or Legitimate decision. The user does
not confirm labels, escalate alerts, manage cases, or add analyst notes.

## One-page workflow

1. Select V1, V2, or both.
2. Select one or more matching model pipelines.
3. Choose Single JSON, CSV Upload, or Real-time.
4. Submit the input or start the replay.
5. Read each model's classification, fraud-risk score, saved threshold, and
   prediction latency.

Selecting several models produces independent classifications. The displayed
fraud count is a simple comparison, not a trained ensemble.

## Inputs

### Single JSON

Paste one raw joined transaction object. `TransactionID` is required. FastAPI
removes `isFraud`, aligns missing optional fields, applies the selected model's
matching feature engineering and preprocessor, and returns one result per
pipeline.

### CSV Upload

Upload multiple raw transactions in one CSV file. The backend validates the
file and rows, processes accepted rows in chunks, and returns versioned score,
threshold, and decision columns. Prediction and invalid-row reports remain
downloadable.

### Real-time

Replay labelled held-out transactions in chronological FIFO order at 1, 2, or
5 transactions per second. Labels stay hidden during inference. The interface
shows stream controls, queue state, throughput, latency, completed
classifications, and the actual demonstration label after prediction.

## Intentionally not shown

- Alert investigation and prioritisation
- Confirm-fraud or mark-legitimate actions
- Escalation, case status, notes, and analyst audit history
- Overview, model-comparison, and infrastructure-monitoring pages

The underlying API and historical implementation remain available in Git, but
the public interface stays focused on ML classification.
