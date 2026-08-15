# Supabase, Render and Cloudflare setup

This document explains the platform boundary in simple terms. It contains no
credentials and is safe to commit.

## Runtime boundary

```text
Cloudflare Pages React app
        |
        | HTTPS and Render SSE
        v
Render FastAPI service
        |-- Supabase: stream rows, predictions, alerts, analyst actions
        `-- Cloudflare R2: approved private model bundles
```

The browser never receives a Supabase secret/service key or an R2 credential.
Only `VITE_API_URL` is public in the Cloudflare Pages build.

## Supabase

The repository pins Supabase CLI `2.114.0` for commands documented here. The
project configuration is in `supabase/config.toml`; version-controlled database
changes are in `supabase/migrations/`.

The hosted project is `credit-card-fraud-npn` (`dsiqmudbeaarrnxuaujf`) in the
Tokyo region. The repository is linked to it, and all three committed migrations
have been applied. Project references are identifiers, not credentials; no
database password or API key is stored in Git.

The migrations create:

- `stream_datasets` and FIFO-ordered `stream_transactions`;
- `stream_ground_truth`, separate from model payloads;
- `prediction_history` with exact `ModelName.VersionName` values;
- `alerts`; and
- `analyst_actions`.

Milestone 3 additionally creates `stream_runs`, FIFO lifecycle events,
model-specific `prediction_events`, and one investigation-ready `fraud_alert`
per flagged transaction. See
[MILESTONE_3_STREAMING_GUIDE.md](MILESTONE_3_STREAMING_GUIDE.md) for the data
preparation, queue, SSE, and persistence contracts.

All tables have RLS enabled. `anon` and `authenticated` have no table grants.
Render uses a server-only Supabase secret key. This is deliberate because the
frontend communicates through FastAPI rather than the Supabase Data API.
New `sb_secret_...` keys are sent in Supabase's `apikey` header and are never
used as bearer tokens.

To link and apply the migration after authenticating:

```bash
npx --yes supabase@2.114.0 login
npx --yes supabase@2.114.0 link --project-ref <project-ref>
npx --yes supabase@2.114.0 db push
```

Run database advisors after applying the migration:

```bash
npx --yes supabase@2.114.0 db advisors --linked --type security
npx --yes supabase@2.114.0 db advisors --linked --type performance
```

Do not put the access token, project secret key or database password in Git.

## Render

`render.yaml` defines the FastAPI service. It deploys from `main`, binds Uvicorn
to Render's `$PORT`, and checks `/health`.

Authenticate and validate before creating the Blueprint:

```bash
render login
render blueprints validate render.yaml
```

The Blueprint asks for these values in the Render Dashboard:

- `CORS_ORIGINS`: the final Cloudflare Pages origin;
- `SUPABASE_URL` and `SUPABASE_SECRET_KEY`;
- `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`; and
- `R2_BUCKET_NAME`.

The `/integrations` endpoint performs a bounded, read-only `HeadBucket` request.
This verifies the R2 endpoint, credentials and bucket scope without listing or
downloading an object.

The current free plan is suitable only for the integration shell. Model memory
profiling must select a larger plan or a version-scoped loading strategy before
the eight real artifacts are enabled.

## Cloudflare Pages

The React/Vite project is in `frontend/`. For Git-based Pages deployment use:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Environment variable | `VITE_API_URL=https://<render-service>.onrender.com` |

Wrangler configuration is also versioned for command-line deployment:

```bash
cd frontend
npx wrangler login
npm run deploy
```

The `public/_headers` file adds baseline browser security headers. Update its
`connect-src` rule if the API later moves from `onrender.com` to a custom domain.

## Local verification

```bash
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
.venv/bin/uvicorn api.main:app --reload --port 8000

cd frontend
npm ci
npm run type-check
npm run build
npm run dev
```

The readiness screen is only an integration shell. Manual transaction, CSV and
real-time analyst workflows begin after the automated eight-model verification
gate is committed and passing.
