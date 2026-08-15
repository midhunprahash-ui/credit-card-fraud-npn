# Cloud deployment architecture

## Platform decision

| Responsibility | Platform |
| --- | --- |
| Train four models | Lightning AI |
| Store private model bundles | Cloudflare R2 |
| Serve Python model inference | FastAPI on Render |
| Host analyst web application | React/Vite on Cloudflare Pages |
| Store stream data and analyst records | Supabase Postgres |
| Source and deployment trigger | GitHub |

Streamlit is not part of the final architecture.

## Runtime flow

```text
React dashboard on Cloudflare Pages
              ↓ HTTPS + direct Render SSE
FastAPI service on Render
              ├── Supabase stream/prediction/alert/action records
              ├── private Cloudflare R2 model bundles
              ↓
Common schema and shared feature builder
              ↓
Four model-specific preprocessors and models in memory
              ↓
Four predictions returned to the dashboard
```

Supabase Realtime is not used for dashboard delivery. Render owns the FIFO queue
and sends live prediction events directly to the browser over SSE.

Held-out labels are stored separately from inference payloads. The backend reads
the next transaction in `TransactionDT`, `TransactionID` order, scores a payload
that cannot contain `isFraud`, and only then reads/reveals the ground truth.

At startup, the service reads the two Git-versioned registries and the
Git-pinned deployment contract. It does not download or load all eight models.
When a selected model is first requested, Render downloads only that immutable
R2 bundle, verifies the pinned manifest plus every file size and SHA-256, and
then loads its adapter. The bounded LRU manager limits in-memory models.

## Why the backend remains on Render

Cloudflare Pages is excellent for the static React frontend, and R2 is suitable
for object storage. The four models require Python, native ML libraries, and
more memory than a lightweight edge function. Render runs the native FastAPI
process with pinned inference libraries and CPU-only PyTorch.

## Core API endpoints

```text
GET  /health
GET  /models
GET  /input-schema
GET  /demo-transactions
GET  /transactions/{transaction_id}
POST /predict
POST /predict/batch
POST /stream/start
GET  /stream/events
```

`POST /predict` accepts one raw transaction, creates missing optional fields,
applies the selected V1/V2 features separately, and returns independent
fraud-risk scores plus visual agreement metadata.

## Frontend pages

- Overview, Live Analysis, Fraud Alerts, Batch Analysis, Model Comparison, and
  Monitoring.
- Real transaction, simplified form, complete JSON, one-row CSV, batch CSV, and
  strict FIFO replay inputs.
- Independent V1/V2 scores, thresholds, agreement, completeness, and health.

## Secrets

Render stores the private R2 credentials and permitted frontend origins.
Lightning stores upload credentials. Cloudflare Pages receives only the public
API base URL; R2 secrets must never be shipped to the browser.

## Deployment order

1. Produce and compare valid model runs.
2. Approve one run per model in both V1/V2 registries.
3. Upload approved bundles to private R2.
4. Verify all eight adapters and the deployment artifact contract locally.
5. Build the FastAPI container and deploy it to Render.
6. Build the React/Vite dashboard and deploy it to Cloudflare Pages.
7. Verify health, CORS, single prediction, batch prediction, and failure states.
