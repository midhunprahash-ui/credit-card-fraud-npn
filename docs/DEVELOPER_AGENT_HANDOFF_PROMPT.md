# CYPHER developer-agent handoff prompt

Last updated: 16 August 2026 (Asia/Kolkata)

Copy the prompt below into the coding agent used by the next developer. Do not
add secret values to the prompt. Share account access and credentials separately
through an approved secure method.

---

You are taking over development of the CYPHER fraud-classification application.

Repository:
<https://github.com/midhunprahash-ui/credit-card-fraud-npn.git>

## Ownership and safety rules

- Work only on the `develop` branch.
- Preserve all existing user changes.
- Never print, log, expose, or commit credentials.
- Never commit `.env`, `.env.local`, Kaggle datasets, processed full datasets,
  model binaries, runtime caches, virtual environments, uploaded CSVs, or cloud
  credentials.
- Do not create new cloud projects, buckets, databases, or services unless the
  owner explicitly requests it.
- Do not upgrade Render or enable paid infrastructure without approval.
- Do not perform destructive database or Git operations.
- Use relevant Supabase, Cloudflare, Wrangler, and Render skills/instructions
  before modifying those integrations.
- Verify current official platform documentation before changing cloud
  configuration.
- Do not deploy until the relevant local end-to-end flow passes.

## Clone and select the working branch

```bash
git clone https://github.com/midhunprahash-ui/credit-card-fraud-npn.git
cd credit-card-fraud-npn
git fetch --all --prune
git switch develop
git pull --ff-only origin develop
git status --short --branch
```

Always pull the latest branches and treat the remote `develop` branch as the
current development source of truth.

## Read before changing code

Read these files completely:

- `README.md`
- `docs/DOCUMENTATION_INDEX.md`
- `docs/PROJECT_GUIDE.md`
- `docs/SIMPLIFIED_APPLICATION_GUIDE.md`
- `docs/INTEGRATION_SETUP.md`
- `docs/DEPLOYMENT_ARCHITECTURE.md`
- `docs/PROJECT_ASSET_INVENTORY.md`
- `docs/MODEL_ARTIFACT_CONTRACT.md`
- `docs/MODEL_VERIFICATION_GATE.md`
- `docs/FINAL_MODEL_SELECTION.md`
- `docs/FEATURE_ENGINEERING_GUIDE.md`
- `docs/CLASS_IMBALANCE_AND_DATA_LEAKAGE.md`
- `docs/KAGGLE_INFERENCE_SAMPLE.md`
- `config/model_registry.json`
- `config/model_registry_v2.json`
- `config/deployment_artifacts.json`
- `config/model_catalog.json`
- `render.yaml`
- `frontend/wrangler.jsonc`
- `.env.example`
- `frontend/.env.example`
- `api/*`
- `src/fraud_pipeline/*`
- `tests/*`
- `frontend/src/*`

Historical warning:

- `docs/MILESTONE_3_STREAMING_GUIDE.md` describes the older labelled replay.
- `docs/MILESTONE_4_FRONTEND_GUIDE.md` describes the older six-page analyst UI.
- These are historical records, not the current public product specification.

## Current application

Product name: **CYPHER**.

It is a focused one-page ML inference application, not an analyst
case-management application.

Frontend:

- React 19, TypeScript and Vite.
- Cloudflare Pages compatible.
- Complete light theme with a Cloudflare-inspired visual style.
- Square corners and no rounded cards.
- Responsive spreadsheet-style prediction results.

Backend:

- Python 3.12.
- FastAPI, Pydantic and Uvicorn.
- Structured operational logging.
- Render-compatible startup.
- Direct Server-Sent Events for live updates.

Cloud architecture:

```text
Browser
  -> React/Vite on Cloudflare Pages
  -> HTTPS and SSE to FastAPI on Render
  -> Supabase for stream datasets, state and history
  -> private Cloudflare R2 for approved model artifacts
```

Supabase Realtime is not used for frontend delivery. FastAPI owns the FIFO
controller and sends browser updates directly through SSE.

## Model pipelines

There are eight independently selectable pipelines:

| Stable identifier | Display name |
| --- | --- |
| `logistic_regression.v1` | `LogisticRegression.V1` |
| `lightgbm.v1` | `LightGBM.V1` |
| `catboost.v1` | `CatBoost.V1` |
| `neural_network.v1` | `NeuralNetwork.V1` |
| `logistic_regression.v2` | `LogisticRegression.V2` |
| `lightgbm.v2` | `LightGBM.V2` |
| `catboost.v2` | `CatBoost.V2` |
| `neural_network.v2` | `NeuralNetwork.V2` |

No models are selected by default. Version is a multi-select supporting V1,
V2, or both. Only models belonging to selected versions are displayed.

CatBoost.V2 is the frozen overall champion. Logistic Regression remains the
interpretable baseline. Multiple selected models produce independent
predictions; their comparison is not an ensemble.

## Input modes

The current UI contains:

1. Single JSON
2. CSV Upload
3. Real-time

Single JSON:

- Accepts one raw joined transaction.
- `TransactionID` and `TransactionDT` are required by the API.
- Missing optional fields are added as null.
- Unknown or invalid fields are rejected.
- `isFraud` is always removed.
- Each selected model uses its own versioned features, schema, preprocessor,
  model, and saved threshold.

CSV Upload:

- Uses raw transaction rows.
- Validates file type, size, row count, identifiers, duplicates, and values.
- Processes valid rows in chunks.
- The tracked demonstration file is
  `data/samples/kaggle_inference_sample_100.csv`.
- It contains 100 real Kaggle test rows and all 433 raw input columns.
- It contains no `isFraud` column.

Real-time:

- Offers only the Supabase dataset named `kaggle_inference_sample`.
- It contains 100 official unlabelled IEEE-CIS Kaggle test transactions.
- It processes rows chronologically using strict FIFO ordering.
- Supported arrival rates are 1, 2, and 5 transactions per second.
- One consumer guarantees completion ordering.
- Events are never silently dropped; the queue grows if inference is slower.
- Controls are Start, Pause, Resume, Stop, and Restart.
- Model/version selection is locked while a stream is active.
- Ground truth is not shown because this dataset is genuinely unlabelled.
- The historical 600-row labelled dataset remains stored but is hidden from the
  simplified UI.

## Output contract

Single JSON, CSV Upload, and Real-time use the same spreadsheet-style output.
Each selected model creates one row containing:

- Transaction ID
- Model
- Fraud
- Not Fraud
- Score
- Threshold

Presentation rules:

- Fraud is highlighted red.
- Not Fraud is highlighted green.
- Score means fraud-risk score, not a guaranteed calibrated probability.
- `score >= saved model threshold` means Fraud.
- `score < saved model threshold` means Not Fraud.
- Thresholds are model-specific and must not be replaced with one global `0.5`
  threshold.

Clicking a row reveals its non-null supplied transaction inputs and up to five
strongest local feature contributions.

Explanation methods:

- LightGBM: native per-row contributions.
- CatBoost: native per-row contributions.
- Logistic Regression: leave-one-feature-out score sensitivity.
- Neural Network: leave-one-feature-out score sensitivity.

Positive contributions move the score toward Fraud. Negative contributions move
it toward Not Fraud. They explain model behaviour, not causation. Explanations
are requested on demand through `POST /explain`; they are not run in the normal
prediction or FIFO hot path.

## Important API routes

```text
GET  /
GET  /health
GET  /integrations
GET  /models
GET  /input-schema
GET  /demo-transactions
GET  /transactions/{transaction_id}
POST /predict
POST /explain
POST /predict/file
POST /predict/batch
GET  /metrics/summary
GET  /stream/datasets
POST /stream/start
POST /stream/pause
POST /stream/resume
POST /stream/stop
POST /stream/restart
GET  /stream/status
GET  /stream/events
```

Historical alert routes remain in the backend, but the simplified frontend does
not show analyst alert or case-management pages.

## Local prerequisites and installation

Install Git, Python 3.12, Node.js 22.12 or newer, and npm.

Python setup from the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install \
  -r requirements-api.txt \
  -r requirements-inference.txt \
  -r requirements-test.txt
```

Frontend setup:

```bash
cd frontend
npm ci
cd ..
```

## Local environment

Create the ignored backend environment file:

```bash
cp .env.example .env
```

Configure it without committing or displaying secret values:

```dotenv
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173

RAW_INPUT_SCHEMA_PATH=config/raw_input_schema.json
DEMO_DATASET_PATH=data/processed/v2/test.parquet
BEHAVIORAL_REFERENCE_PATH=data/processed/v2/behavioral_reference.joblib
DEPLOYMENT_ARTIFACT_CONTRACT_PATH=config/deployment_artifacts.json

MODEL_CACHE_SIZE=2
MODEL_CPU_THREADS=1
BATCH_MAX_FILE_BYTES=5000000
BATCH_MAX_ROWS=1000
BATCH_CHUNK_SIZE=100

SUPABASE_URL=https://dsiqmudbeaarrnxuaujf.supabase.co
SUPABASE_SECRET_KEY=<SERVER-ONLY-SUPABASE-SECRET>

R2_ENDPOINT_URL=https://<CLOUDFLARE-ACCOUNT-ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<SERVER-ONLY-R2-ACCESS-KEY>
R2_SECRET_ACCESS_KEY=<SERVER-ONLY-R2-SECRET>
R2_BUCKET_NAME=fraud-model-artifacts
```

Confirm the actual R2 bucket name with the owner before changing it.

Create the ignored frontend environment file:

```bash
cp frontend/.env.example frontend/.env.local
```

It should contain only:

```dotenv
VITE_API_URL=http://localhost:8000
```

Never place a Supabase secret, R2 credential, Render key, Cloudflare API token,
or model-storage credential in a `VITE_*` variable. Vite variables are public.

## Model artifacts

Large model artifacts are not stored in Git. Cloudflare R2 contains only the
eight approved deployment bundles and the V2 behavioural reference. Expected
object names and SHA-256 values are pinned in
`config/deployment_artifacts.json`.

To download all approved artifacts and the runtime reference, export the
ignored `.env` values into the shell:

```bash
set -a
source .env
set +a
```

Then run:

```bash
PYTHONPATH=. .venv/bin/python scripts/download_r2_artifacts.py --include-runtime
```

This downloads roughly 830 MB. CatBoost.V2 is the largest bundle at
approximately 497 MB.

For a lightweight first test:

```bash
PYTHONPATH=. .venv/bin/python scripts/download_r2_artifacts.py \
  logistic_regression.v1 --include-runtime
```

The downloader validates the pinned manifest, file sizes, and SHA-256 hashes.
Never bypass this validation.

## Local startup

Terminal 1, from the repository root:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=. \
  .venv/bin/uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Do not add `--reload` while running the approved model artifacts. Explicitly
restart the API after backend edits so PyTorch and tree-model native thread
pools are initialized in a clean process.

Verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/integrations
```

Open the API documentation at <http://localhost:8000/docs>.

Terminal 2:

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>.

Real-time mode requires valid Supabase server settings. Manual inference also
requires the selected model artifact. V2 inference requires the verified
behavioural reference.

## Supabase connection

Existing project:

- Project name: `credit-card-fraud-npn`
- Project reference: `dsiqmudbeaarrnxuaujf`
- Region: Tokyo
- URL: `https://dsiqmudbeaarrnxuaujf.supabase.co`
- Five version-controlled migrations are in `supabase/migrations/`.

The migrations have already been applied to the hosted project. Do not blindly
reapply or rewrite them.

For Codex MCP:

```bash
codex mcp add supabase \
  --url "https://mcp.supabase.com/mcp?project_ref=dsiqmudbeaarrnxuaujf&features=docs%2Caccount%2Cdatabase%2Cdebugging%2Cdevelopment%2Cfunctions%2Cbranching"
codex mcp login supabase
```

For another coding agent, configure the official Supabase MCP server using that
agent's supported OAuth method and the same project reference. The owner must
authenticate access in the browser.

CLI setup and verification:

```bash
npx --yes supabase@2.114.0 login
npx --yes supabase@2.114.0 link \
  --project-ref dsiqmudbeaarrnxuaujf
npx --yes supabase@2.114.0 migration list --linked
```

Only run `db push` after reviewing an actually pending migration:

```bash
npx --yes supabase@2.114.0 db push
```

After any schema or RLS change:

```bash
npx --yes supabase@2.114.0 db lint --linked --level warning
npx --yes supabase@2.114.0 db advisors --linked --type security
npx --yes supabase@2.114.0 db advisors --linked --type performance
```

Supabase security state:

- RLS is enabled on exposed tables.
- `anon` and `authenticated` do not have raw table access.
- The frontend does not connect directly to Supabase.
- FastAPI uses the server-only `sb_secret_...` key.
- New Supabase secret and publishable keys are not JWTs.
- Do not send an `sb_secret_...` value as a browser bearer token.
- Do not create permissive RLS policies just to make a request work.
- Hidden labels must never be exposed to the browser before inference.

The 100-row Kaggle sample is already expected in Supabase. Verify
`GET /stream/datasets` before attempting to upload it again.

## Render connection

Existing service:

- Service name: `credit-card-fraud-npn`
- URL: <https://credit-card-fraud-npn.onrender.com>
- Runtime: Python 3.12
- Deployment branch: `main`
- Blueprint: `render.yaml`
- Health path: `/health`
- Auto-deploy: enabled from `main`

Start command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

The collaborator must be added to the correct Render workspace or authenticate
using an owner-approved account.

```bash
render login
render whoami -o json
render blueprints validate render.yaml
```

Render production environment variables:

```dotenv
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://npn-fraud-analyst.pages.dev
MODEL_CACHE_SIZE=2
MODEL_CPU_THREADS=1
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
VECLIB_MAXIMUM_THREADS=1
DEPLOYMENT_ARTIFACT_CONTRACT_PATH=config/deployment_artifacts.json

SUPABASE_URL=https://dsiqmudbeaarrnxuaujf.supabase.co
SUPABASE_SECRET_KEY=<SERVER-ONLY-SECRET>

R2_ENDPOINT_URL=https://<ACCOUNT-ID>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<SERVER-ONLY-READ-KEY>
R2_SECRET_ACCESS_KEY=<SERVER-ONLY-READ-SECRET>
R2_BUCKET_NAME=fraud-model-artifacts
```

Do not retrieve or paste existing secret values into logs or chat. If the agent
cannot access them, ask the owner to enter them directly in Render Dashboard.

Important Render limitations:

- The configured free service has 512 MB RAM.
- It spins down after 15 minutes without inbound traffic.
- Waking can take about one minute.
- Its filesystem and downloaded model cache are ephemeral.
- CatBoost.V2 is too large to load reliably on this plan.
- Do not claim all eight models are cloud-verified on the free service.
- Full local inference is currently the reliable path.
- Do not upgrade the service without owner approval.

Official reference:
<https://render.com/docs/free>

## Cloudflare Pages connection

Existing Pages project:

- Project: `npn-fraud-analyst`
- Production URL: <https://npn-fraud-analyst.pages.dev>
- Build directory: `frontend`
- Build command: `npm run build`
- Output directory: `frontend/dist`
- Public build variable:
  `VITE_API_URL=https://credit-card-fraud-npn.onrender.com`

The Pages project uses Direct Upload. Git pushes do not publish the frontend.
Cloudflare does not allow this existing Direct Upload project to be converted
to Git integration. A new Pages project would be required for native Git
integration.

Official reference:
<https://developers.cloudflare.com/pages/get-started/direct-upload/>

Authenticate and verify access:

```bash
cd frontend
npx wrangler login
npx wrangler whoami
npx wrangler pages project list
```

Do not create a replacement Pages project if the existing project is not
visible. Ask the owner for Cloudflare account access.

## Production frontend release

Only deploy a frontend change after it passes locally and has been finalized on
`main`.

From `frontend/`:

```bash
npm ci
npm run format:check
npm test
npm run type-check
VITE_API_URL=https://credit-card-fraud-npn.onrender.com npm run build
npx wrangler pages deploy dist \
  --project-name npn-fraud-analyst \
  --branch main
npx wrangler pages deployment list \
  --project-name npn-fraud-analyst
```

Do not run a production build without `VITE_API_URL`; otherwise Vite can embed
`localhost:8000` into the deployed application.

## Cloudflare R2 connection

R2 is private model storage, not public frontend storage.

- Expected bucket: `fraud-model-artifacts`.
- Objects follow `config/deployment_artifacts.json`.
- Runtime credentials should be bucket-scoped and read-only where possible.
- Upload credentials should be separate from runtime read credentials.
- Never expose R2 credentials in frontend code.
- Never make model objects publicly accessible.
- Do not upload every experiment; only approved registry runs belong in R2.
- Do not re-upload artifacts unless an approved model or deployment contract has
  intentionally changed.

## Tests

Backend:

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

Baseline at handoff: 76 backend tests passed.

Frontend:

```bash
cd frontend
npm run format:check
npm test
npm run type-check
VITE_API_URL=https://credit-card-fraud-npn.onrender.com npm run build
```

Baseline at handoff:

- Four frontend test files passed.
- Seven frontend tests passed.
- Formatting passed.
- Type checking passed.
- Production build passed.

## Full eight-model golden verification

```bash
PYTHONPATH=. .venv/bin/python scripts/verify_selected_models.py
```

This requires Git-ignored processed datasets:

- `data/processed/v2/train.parquet`
- `data/processed/v2/validation.parquet`
- `data/processed/v2/test.parquet`

These are not in Git and are not model artifacts. If absent, ask the owner for
a private transfer or reproduce them with the documented notebooks. Do not
fabricate substitutes and do not commit them.

The recorded accepted result is PASS for all eight models.

## Known limitations

- Render free RAM is insufficient for reliable large-model inference.
- Render free instances cold-start and lose their local model cache.
- Cloudflare Pages can remain online while Render is asleep or unavailable.
- Cloudflare Pages deployment is manual.
- The official Kaggle test sample is unlabelled and cannot measure accuracy.
- Local explanations describe model sensitivity or contribution, not causation.
- V1 and V2 preprocessing must never be mixed.
- Scores must not be described as calibrated probabilities.
- Model agreement must not be described as an ensemble.
- The full eight-model verifier needs private processed data.

## Git and release workflow

For every coherent unit:

1. Confirm the branch is `develop`.
2. Check Git status and preserve unrelated changes.
3. Implement only the requested scope.
4. Update simple documentation.
5. Run relevant backend and frontend tests.
6. Review `git diff` and `git diff --check`.
7. Commit on `develop`.
8. Push `develop`.
9. Switch to `main`.
10. Pull `main` with `--ff-only`.
11. Merge `develop` using a normal non-destructive merge.
12. Push `main`.
13. For a frontend release, deploy the tested `main` content to Cloudflare
    Pages with the explicit production `VITE_API_URL`.
14. Return to `develop`.
15. Confirm the working tree is clean.

Typical commands:

```bash
git switch develop
git pull --ff-only origin develop
git status --short --branch

git add <explicit-files>
git commit -m "<clear message>"
git push origin develop

git switch main
git pull --ff-only origin main
git merge --no-ff develop -m "merge: <completed unit>"
git push origin main

git switch develop
git status --short --branch
```

Never force-push or use destructive reset or checkout commands.

## First task after receiving this prompt

Do not immediately redesign the application.

First:

1. Clone and switch to `develop`.
2. Confirm the working tree is clean.
3. Read the required documentation and configuration.
4. Check available local model/data assets without printing secrets.
5. Verify Python and Node versions.
6. Install dependencies.
7. Configure ignored local environment files.
8. Verify Supabase, R2, Render, and Cloudflare access separately.
9. Start FastAPI and React locally.
10. Run the test suites.
11. Report:
    - what works locally;
    - which cloud accounts are connected;
    - which required secrets or assets are missing;
    - whether the 100-row stream dataset is reachable;
    - which model pipelines can load;
    - current Render and Pages health; and
    - any mismatch between repository and cloud state.

Do not make a major architectural change until this audit is reported.
