# Cloud deployment architecture

## Platform decision

| Responsibility | Platform |
| --- | --- |
| Train four models | Lightning AI |
| Store private model bundles | Cloudflare R2 |
| Serve Python model inference | FastAPI on Render |
| Host analyst web application | React/Vite on Cloudflare Pages |
| Store stream data and prediction history | Supabase Postgres |
| Backend source and deployment trigger | GitHub `main` through Render |
| Frontend release mechanism | Cloudflare Pages Direct Upload through Wrangler |

Streamlit is not part of the final architecture.

## Runtime flow

```text
React/Vite inference UI on Cloudflare Pages
              ↓ HTTPS + direct Render SSE
FastAPI service on Render
              ├── Supabase stream datasets, state, and prediction history
              ├── private Cloudflare R2 model bundles
              ↓
Common schema and shared feature builder
              ↓
Requested model-specific preprocessors and models in a bounded cache
              ↓
Independent prediction rows returned to the UI
```

Supabase Realtime is not used for dashboard delivery. Render owns the FIFO queue
and sends live prediction events directly to the browser over SSE.

The current public Real-time flow uses the 100-row unlabelled
`kaggle_inference_sample`. The backend reads it in `TransactionDT`,
`TransactionID` order, queues one event at a time, and scores payloads that do
not contain `isFraud`. The older labelled held-out datasets keep labels in a
separate table for controlled evaluation, but those labels are not displayed in
the simplified UI.

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
POST /explain
POST /stream/start
POST /stream/pause
POST /stream/resume
POST /stream/stop
GET  /stream/status
GET  /stream/events
```

`POST /predict` accepts one raw transaction, creates missing optional fields,
applies the selected V1/V2 features separately, and returns independent
fraud-risk scores plus visual agreement metadata. `POST /explain` calculates a
local explanation only after the user opens a result row, so ordinary and FIFO
prediction latency is not inflated by explanation work.

## Current frontend

- One focused CYPHER prediction page.
- V1/V2 multi-select and version-aware model selection with no models selected
  by default.
- Single JSON, CSV Upload, and 100-row strict-FIFO Real-time modes.
- A common spreadsheet-style table showing Transaction ID, Model, Fraud,
  Not Fraud, Score, and Threshold.
- Click-to-open transaction inputs and on-demand local model contributions.

The earlier six-page analyst console remains documented as a historical
Milestone 4 implementation, not the current public product.

## Secrets

Render stores the private R2 credentials and permitted frontend origins.
Lightning stores upload credentials. Cloudflare Pages receives only the public
API base URL; R2 secrets must never be shipped to the browser.

## Deployment and operating notes

1. Produce and compare valid model runs.
2. Approve one run per model in both V1/V2 registries.
3. Upload approved bundles to private R2.
4. Verify all eight adapters and the deployment artifact contract locally.
5. Build the FastAPI container and deploy it to Render.
6. Build React with the production `VITE_API_URL` and deploy `frontend/dist`
   explicitly to the Direct Upload Pages project with Wrangler.
7. Verify health, CORS, single prediction, batch prediction, and failure states.

The current Render Blueprint uses the free plan. It is useful for health and
integration checks, but its memory is insufficient for reliable loading of the
largest approved models. Full local inference works when artifacts are present.
An always-on cloud backend with enough RAM requires a suitable host or paid
instance; the frontend cannot perform Python model inference by itself.
