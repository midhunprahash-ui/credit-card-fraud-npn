# Milestone 4: Fraud Intelligence Console

## Outcome

The repository now contains a responsive React/TypeScript console for bank
fraud analysts. It exposes the eight independently selectable V1/V2 pipelines,
manual and real-time prediction, CSV analysis, alert investigation, model
comparison, and operational monitoring. It is a static Vite application ready
for Cloudflare Pages; it does not contain a Pages Function or a cloud secret.

The backend also exposes investigation-safe alert endpoints and richer saved
model metrics required by the console. Cloud deployment remains Milestone 5.

## Pages and analyst workflow

| Page | Main purpose |
| --- | --- |
| Overview | Current volume, alerts, latency, risk distribution, agreement, and recent high-risk work |
| Live Analysis | Sticky filters, single prediction, and direct-SSE FIFO replay controls |
| Fraud Alerts | Searchable prioritized queue, investigation drawer, notes, and audited actions |
| Batch Analysis | Validated CSV upload, progress, sortable results, and result/error downloads |
| Model Comparison | V1/V2 metrics, thresholds, confusion matrices, timing, and saved global importance |
| Monitoring | Backend, Supabase, R2, loaded-model, stream, queue, latency, and error health |

The shared Version filter accepts V1, V2, or both. The Models control displays
only models in the selected versions and always uses `ModelName.VersionName`.
Internal API values remain stable identifiers such as `catboost.v2`. The model
selection is an agreement view, not an ensemble.

## Manual prediction

Single Transaction supports four honest inputs:

1. choose a real held-out demonstration `TransactionID`;
2. enter the simplified transaction fields;
3. paste complete JSON; or
4. upload one one-row CSV.

The browser sends raw fields to FastAPI. FastAPI removes `isFraud`, aligns each
request to the saved raw schema, runs every selected pipeline independently,
and returns its saved threshold. The UI labels outputs as fraud-risk scores,
not calibrated probabilities. It shows completeness, latency, champion status,
decision, and a visual model-agreement summary.

Batch Analysis sends an accepted CSV to the existing chunked API. It reports
valid, invalid, processed, failed, suspicious-value, and per-model fraud counts.
Analysts can search and sort results, then download prediction and invalid-row
CSV reports. The server remains authoritative for file size, row limit, schema,
identifier, duplicate, and type validation.

## Real-time replay

The console lists ready Supabase datasets and supports 1, 2, or 5 transactions
per second. Start, pause, resume, stop, and confirmed restart call the FastAPI
stream controls. Active filters lock while a run is loading, running, or
stopping. A paused or stopped run may be reconfigured.

One `EventSource` connects directly to `/stream/events` on Render. Transaction
arrival and completion events update the live queue, prediction table, counts,
throughput, average/p95 latency, alert count, risk distribution, and agreement.
The queue is never truncated by the backend; if inference falls behind, the
visible backlog grows. Actual labels appear only in completed demonstration
events, after prediction.

## Alerts and analyst actions

FastAPI adds these server-only Supabase-backed routes:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/alerts` | Fixed risk-ordered alert list with safe filters |
| GET | `/alerts/{alert_id}` | Alert, model results, masked transaction details, and action history |
| POST | `/alerts/{alert_id}/actions` | Confirm fraud, mark legitimate, escalate, note, or close |

Every action requires a nonblank analyst identifier. Status-changing actions
update the alert and append an immutable audit record. Migration
`20260815185931_analyst_action_close.sql` adds `CLOSED` to the allowed audit
actions. RLS remains enabled and browser roles receive no raw-table access.

## Model comparison and explainability

`GET /models` now reads the approved local artifact metadata and returns saved
validation/test metrics, training duration, measured test prediction latency,
and up to eight global features when a saved importance or coefficient file is
available. It never calculates new test metrics or performs model selection.

PR-AUC is highlighted because fraud is rare. CatBoost.V2 is marked as the
frozen champion and Logistic Regression as the interpretable baseline. Test
metrics are clearly labelled as final-report evidence, not tuning data. Feature
names are shown without inventing meanings for anonymized IEEE-CIS `V*` fields.

## Frontend structure

```text
frontend/src/
  api/          typed requests, responses, errors, and SSE subscription
  components/   shell, filters, result cards, batch panel, and shared UI
  config/       the eight stable model identifiers and display names
  pages/        six analyst-facing pages
  test/         shared Vitest/DOM setup
  utils/        safe formatting helpers
```

Hash navigation keeps all pages compatible with a static Cloudflare Pages
deployment. The application avoids a chart dependency: lightweight semantic
HTML/CSS bars keep the bundle small and readable. Loading, empty, error, and
offline states are present. Controls have labels, focus styles, keyboard access,
and text/icons in addition to green, amber, and red risk colours. Close and
restart actions require confirmation.

## Configuration and security

The only frontend environment setting is public:

```dotenv
VITE_API_URL=http://localhost:8000
```

For Cloudflare Pages set it to the HTTPS Render origin. Never add the Supabase
secret, R2 credentials, or model objects to a `VITE_*` variable. The browser
uses FastAPI for Supabase and R2 operations. FastAPI CORS must contain the exact
Pages origin. `_headers` supplies CSP, frame, MIME, referrer, permissions, and
immutable asset-cache headers. Transaction displays mask sensitive-looking
card, email, address, device, and identity values.

## Local verification

Run the API and frontend in separate terminals:

```bash
PYTHONPATH=. .venv/bin/uvicorn api.main:app --reload --port 8000

cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Run the Milestone 4 acceptance checks:

```bash
PYTHONPATH=. .venv/bin/python -m compileall -q api src scripts tests
PYTHONPATH=. .venv/bin/pytest -q

cd frontend
npm run format:check
npm test
npm run type-check
npm run build
```

The checked tests cover the complete backend suite, alert API/repository action
contracts, shared version/model filter behavior, agreement rendering, and model
comparison evidence. The Vite production build verifies the Cloudflare Pages
artifact. Live cloud credentials, full stream data, and deployed browser-to-API
verification are intentionally deferred to Milestone 5.

## Troubleshooting

- API shown offline: check `VITE_API_URL`, `/health`, Render status, and CORS.
- Alert or stream unavailable: set server-only Supabase variables on FastAPI and
  upload a ready demonstration dataset.
- Stream events do not move: confirm the Pages CSP permits the Render origin and
  that `/stream/events` remains open as `text/event-stream`.
- Model unavailable: run the eight-model verification gate and check local/R2
  artifact hashes; do not bypass validation.
- Empty model comparison evidence: the approved artifact may not include a
  saved importance/coefficients file; the UI reports that honestly.
