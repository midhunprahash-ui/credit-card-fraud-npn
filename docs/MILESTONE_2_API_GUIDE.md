# Milestone 2: FastAPI manual prediction and CSV batch API

> Status: API foundation retained and extended. The current one-page product is
> documented in [SIMPLIFIED_APPLICATION_GUIDE.md](SIMPLIFIED_APPLICATION_GUIDE.md).

## Outcome

The backend now exposes the verified Milestone 1 inference contract through
typed FastAPI endpoints. It supports real held-out demonstration lookup, JSON
single prediction, one-row CSV prediction, and chunked CSV batch prediction.

This document covers the Milestone 2 manual surface plus the later on-demand
explanation addition. Supabase FIFO streaming is documented in Milestone 3, and
R2/Render/Pages integration is documented in Milestone 5.

## Local setup

Install the API and all four native model runtimes:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-api.txt -r requirements-inference.txt
```

The following ignored local assets are required for real inference:

- `data/processed/v2/test.parquet`
- `data/processed/v2/train.parquet`
- `data/processed/v2/validation.parquet`
- the eight selected artifact directories from the registries

Generate the safe V2 starting reference from train and validation history:

```bash
PYTHONPATH=. .venv/bin/python scripts/prepare_behavioral_reference.py
```

The script records the reference cutoff and writes only to the ignored
`data/processed/` directory. The API refuses V2 inference when this metadata is
missing or overlaps the transaction being scored.

Start FastAPI with the same command used by Render:

```bash
.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Sparse JSON is aligned to the complete 433-column raw contract with one pandas
`reindex` operation. This restores absent optional fields as null and preserves
training-time column order without repeatedly inserting columns or fragmenting
the DataFrame.

Open `http://localhost:8000/docs` for the generated OpenAPI interface.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Process health and local artifact availability |
| GET | `/models` | Eight canonical models, metrics, thresholds, and loading state |
| GET | `/input-schema` | Raw fields, required identifiers, and upload limits |
| GET | `/demo-transactions` | Chronological held-out choices without labels |
| GET | `/transactions/{transaction_id}` | Complete joined raw input without `isFraud` |
| POST | `/predict` | Single JSON transaction through selected models |
| POST | `/explain` | On-demand local explanation for one transaction/model pair |
| POST | `/predict/file` | Exactly one raw CSV row through selected models |
| POST | `/predict/batch` | Chunked raw CSV scoring and row-level validation |
| GET | `/metrics/summary` | In-process counts, latency, errors, and model-cache state |

See [MILESTONE_3_STREAMING_GUIDE.md](MILESTONE_3_STREAMING_GUIDE.md) for the
stream endpoints added after this manual API milestone.

## Single JSON request

```json
{
  "model_identifiers": [
    "logistic_regression.v1",
    "catboost.v2"
  ],
  "transaction": {
    "TransactionID": 3488959,
    "TransactionDT": 13151880,
    "TransactionAmt": 108.5
  }
}
```

Only `TransactionID` and `TransactionDT` are mandatory at the API boundary.
Other saved raw-input fields are added as null when absent. Unknown fields,
invalid IDs, negative times or amounts, and duplicate model identifiers are
rejected. If `isFraud` is supplied, it is removed before feature engineering.

The response contains one independent result per selected model:

- stable identifier and display name;
- V1 or V2 version and immutable run ID;
- fraud-risk score and saved threshold;
- fraud/legitimate decision;
- model prediction latency and processing status;
- champion flag and input completeness; and
- agreement vote summary.

Agreement is a visual comparison, not an ensemble. Scores are not described as
calibrated probabilities.

The current UI names the negative class **Not Fraud**. The API retains the
machine-readable legacy `decision_label: "legitimate"` value for compatibility;
clients should use the boolean `decision` as authoritative.

## Local explanation request

`POST /explain` accepts one model identifier and one raw transaction. It returns
up to five features, their signed contribution or sensitivity, and a direction
of `toward_fraud` or `toward_not_fraud`. LightGBM and CatBoost use native SHAP
feature contributions. Logistic Regression and Neural Network use
leave-one-feature-out score sensitivity, which is explicitly labelled as not
SHAP. The API returns the explanation technique and its display label so the UI
does not misidentify the method. The result explains model behaviour, not
causation.

Explanations are intentionally requested only after the user opens a result
row. They are not part of the normal `/predict`, batch, or FIFO hot path.

## CSV input

`POST /predict/file` and `POST /predict/batch` use multipart form data:

- `file`: a `.csv` file;
- `models`: a JSON string array of stable model identifiers; and
- `response_format`: `json` or `zip` for batch requests.

CSV validation covers extension, content type, byte limit, row limit, required
columns, duplicate TransactionIDs, unknown fields, identifiers, times, amounts,
and row-level model-input errors. Valid rows are processed in configured chunks.
Invalid rows do not prevent other valid rows from being scored.

The JSON batch response includes counts, suspicious transaction value, model
fraud counts, unanimous-agreement count, invalid-row details, and flattened
versioned fields such as:

```text
CatBoost.V2_score
CatBoost.V2_threshold
CatBoost.V2_decision
LightGBM.V1_score
LightGBM.V1_decision
fraud_vote_count
processing_status
```

Each JSON result also contains `input_payload`, which lets the UI open a row and
show the exact non-null input supplied for that transaction. This field is
excluded from downloadable files to keep exports focused and avoid duplicating
wide raw input data.

With `response_format=zip`, the response downloads:

- `prediction_results.csv`
- `invalid_rows.csv`
- `summary.json`

Uploaded files and generated downloads are processed in memory and are not
written into the repository or retained by the server.

## Model loading

The application never loads all eight models at startup. A thread-safe bounded
LRU manager verifies a selected bundle before loading it and records:

- loading/not-loaded/failed state;
- load time;
- trusted bundle size; and
- process RSS and measured RSS change during loading; and
- the active cache order.

The default cache contains at most two models. Loading CatBoost.V2 therefore
does not require keeping all other models resident. A failed model load is
isolated and does not prevent unrelated models from loading.

## Errors and security

Application errors use one structure:

```json
{
  "error": {
    "code": "invalid_prediction_input",
    "message": "...",
    "details": null
  }
}
```

Request logs contain only method, route, status, duration, request ID, and safe
error type. Raw transaction bodies, CSV contents, labels, and secrets are never
logged. CORS continues to come only from `CORS_ORIGINS`.

The API can start without ignored data or model artifacts so `/health` remains
available. Affected data or prediction endpoints then return a clear 503 error.
R2 artifact download and full cloud inference dependencies are deferred to the
cloud-integration milestone.

## Verification

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python scripts/verify_selected_models.py
```

The API integration test selects the first real chronological held-out
transaction, confirms that its label is hidden, and reproduces the saved V1 and
V2 Logistic Regression scores through HTTP.
