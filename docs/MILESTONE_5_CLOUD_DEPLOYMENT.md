# Milestone 5: Cloud deployment and verified artifacts

## Outcome

The repository has a reproducible cloud contract for React/Vite on Cloudflare
Pages, FastAPI on Render, eight approved private model bundles in Cloudflare R2,
and chronological demonstration/history data in Supabase.

Secrets remain in Render or ignored local environment files. Pages receives
only `VITE_API_URL`. Model binaries and full datasets remain outside Git.

## R2 object contract

Only the eight enabled registry runs are eligible for upload. Experiments,
archives, replicated runs, and processed datasets are excluded.

```text
models/
  v1/<model-key>/<run-id>/<manifest files>
  v2/<model-key>/<run-id>/<manifest files>
  runtime/v2/behavioral_reference.joblib
```

`config/deployment_artifacts.json` records the immutable object prefix, run ID,
manifest SHA-256, file count, and byte count for every model. It also pins the
target-free V2 reference. `config/model_catalog.json` contains only safe public
evaluation metadata, so model comparison does not load large binaries.

Regenerate both contracts only after an approved registry changes:

```bash
PYTHONPATH=. .venv/bin/python scripts/build_deployment_contracts.py
git diff -- config/deployment_artifacts.json config/model_catalog.json
```

Dry-run the approved inventory:

```bash
PYTHONPATH=. .venv/bin/python scripts/upload_r2_artifacts.py \
  --transport wrangler --dry-run
```

Wrangler supports the signed-in Cloudflare user for ordinary objects. The 471
MB CatBoost.V2 file exceeds Wrangler's 300 MiB CLI limit and requires S3
multipart upload. Configure a separate bucket-scoped Object Read & Write key in
the ignored `.env`, then run:

```bash
set -a
source .env
set +a
PYTHONPATH=. .venv/bin/python scripts/upload_r2_artifacts.py catboost.v2 \
  --transport s3 --exclude-runtime
```

Uploads perform a download round trip and verify size plus SHA-256. The
`--no-round-trip` option is for controlled recovery, not acceptance.

Restore selected bundles with:

```bash
PYTHONPATH=. .venv/bin/python scripts/download_r2_artifacts.py \
  logistic_regression.v1 catboost.v2 --include-runtime
```

Downloads use a temporary sibling directory. The cache becomes visible only
after the pinned manifest and every declared file pass validation. An existing
invalid cache is rejected rather than silently overwritten.

## Lazy model cache on Render

Render starts without model binaries in its Git checkout. On first selection:

1. resolve the approved run from the registry;
2. verify the remote manifest against the Git-pinned hash;
3. download and SHA-256 check every declared file;
4. atomically publish the ephemeral bundle;
5. load the matching adapter; and
6. retain it in the bounded LRU memory cache.

The V2 behavioral reference follows the same lazy checksum boundary. Render's
filesystem is ephemeral, so downloads repeat after redeploy, restart, or free
instance spin-down. R2 remains the durable source.

The Blueprint uses:

```text
Build: requirements-render.txt, then PyTorch's CPU-only wheel
Start: uvicorn api.main:app --host 0.0.0.0 --port $PORT
Health: /health
Branch: main
```

Secrets in `render.yaml` use `sync: false`. Existing services do not
automatically receive newly declared secret values; update those in the Render
dashboard. The current API is:

```text
https://credit-card-fraud-npn.onrender.com
```

### Memory boundary

The free Render instance provides 512 MB RAM. CatBoost.V2 is a 471 MB file and
can require substantially more memory after loading. Do not claim that pipeline
is cloud-verified on the free plan. Keep lazy loading enabled and move to a
Standard 2 GB or larger instance only after budget approval and memory testing.
No paid upgrade is performed automatically.

## Cloudflare Pages

| Setting | Value |
| --- | --- |
| Project | `npn-fraud-analyst` |
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Output | `dist` |
| Public environment | `VITE_API_URL=https://credit-card-fraud-npn.onrender.com` |

Deploy the tested static output:

```bash
cd frontend
npm ci
npm run format:check
npm test
npm run type-check
npm run deploy
```

`_headers` restricts `connect-src` to the exact Render origin plus local
development. There is no R2 binding, Supabase secret, or Pages Function.

## Supabase cloud data

All migrations are applied and RLS is enabled. Browser roles have no raw table
grants. FastAPI uses the server secret and returns label-free transaction
payloads before inference.

`demo_chronological` contains the first 600 naturally ordered held-out rows:

| Rows | Fraud | Fraud rate | Rebalanced? |
| ---: | ---: | ---: | --- |
| 600 | 21 | 3.5000% | No |

The API uses this Supabase dataset for Manual demonstration and FIFO streaming
when local ignored Parquet is unavailable. `held_out_full` remains an optional
reproducible upload because 88,581 wide JSON payloads may exceed a free
project's storage budget.

## Verification

Local acceptance:

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python scripts/verify_selected_models.py --sample-size 4
render blueprints validate

cd frontend
npm run format:check
npm test
npm run type-check
npm run build
```

After both deployments are live:

```bash
PYTHONPATH=. .venv/bin/python scripts/verify_cloud_deployment.py
```

The verifier checks Render health, all eight catalog identifiers, Supabase and
R2 reachability, exact-origin CORS, and the Pages application. A health/catalog
check is not proof that a large model loaded within the free memory limit.

Run Supabase validation after data or schema changes:

```bash
npx supabase db lint --linked --level warning
npx supabase db advisors --linked --type security
npx supabase db advisors --linked --type performance
```

## Troubleshooting

- `model_unavailable`: check R2 keys, the pinned manifest, object permissions,
  and Render memory. Never bypass hash validation.
- `v2_reference_unavailable`: upload the contract-pinned runtime reference.
- R2 `AccessDenied`: the runtime key may intentionally be read-only; use a
  separate bucket-scoped deployment writer rather than broadening browser or
  runtime permissions.
- Pages cannot call Render: verify `VITE_API_URL`, CORS, and the CSP origin.
- Free Render cold start: the cache is lost after spin-down, so a model's first
  request includes its verified R2 download.
