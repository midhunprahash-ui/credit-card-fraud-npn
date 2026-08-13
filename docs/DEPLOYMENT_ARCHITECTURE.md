# Cloud deployment architecture

## Platform decision

| Responsibility | Platform |
| --- | --- |
| Train four models | Lightning AI |
| Store private model bundles | Cloudflare R2 |
| Serve Python model inference | FastAPI on Render |
| Host analyst web application | React/Vite on Cloudflare Pages |
| Source and deployment trigger | GitHub |

Streamlit is not part of the final architecture.

## Runtime flow

```text
React dashboard on Cloudflare Pages
              ↓ HTTPS
FastAPI service on Render
              ↓
Common schema and shared feature builder
              ↓
Four model-specific preprocessors and models in memory
              ↓
Four predictions returned to the dashboard
```

At API startup, the service reads a registry from private R2 storage, downloads
the approved bundles, verifies SHA-256 checksums, loads all four models, and
runs smoke predictions. `/health` becomes ready only after every enabled model
passes.

## Why the backend remains on Render

Cloudflare Pages is excellent for the static React frontend, and R2 is suitable
for object storage. The four models require Python, native ML libraries, and
more memory than a lightweight edge function. Render will run the containerized
FastAPI process with pinned training-compatible package versions.

## Planned API endpoints

```text
GET  /health
GET  /models
GET  /schema
POST /predict
POST /predict-batch
```

`POST /predict` accepts one normalized transaction, creates missing optional
fields, applies shared features, invokes all four wrappers, and returns four
separate probabilities plus agreement metadata.

## Planned frontend pages

- Single-transaction form for understandable demo fields.
- Full JSON input for the complete schema.
- CSV batch upload and analyst queue.
- Four side-by-side model cards and probability chart.
- Input completeness and identity availability.
- Model evaluation and EDA reference pages.

## Secrets

Render stores the private R2 credentials and permitted frontend origins.
Lightning stores upload credentials. Cloudflare Pages receives only the public
API base URL; R2 secrets must never be shipped to the browser.

## Deployment order

1. Produce and compare valid model runs.
2. Approve one run per model and write `registry.json`.
3. Upload approved bundles to private R2.
4. Implement and test the four model wrappers locally.
5. Build the FastAPI container and deploy it to Render.
6. Build the React/Vite dashboard and deploy it to Cloudflare Pages.
7. Verify health, CORS, single prediction, batch prediction, and failure states.
