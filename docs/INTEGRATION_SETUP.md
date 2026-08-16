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
- historical alert and analyst-action tables retained by the backend; and
- stream-run and FIFO lifecycle tables.

Milestone 3 additionally creates `stream_runs`, FIFO lifecycle events,
model-specific `prediction_events`, and one investigation-ready `fraud_alert`
per flagged transaction. See
[MILESTONE_3_STREAMING_GUIDE.md](MILESTONE_3_STREAMING_GUIDE.md) for the data
preparation, queue, SSE, and persistence contracts.

All tables have RLS enabled. `anon` and `authenticated` have no table grants.
Render uses a server-only Supabase secret key. This is deliberate because the
frontend communicates through FastAPI rather than the Supabase Data API. The
current application therefore does not need a browser publishable key. If a
future browser feature uses Supabase directly, expose only an
`sb_publishable_...` key and add a narrowly scoped RLS policy first. New
`sb_secret_...` keys are sent in Supabase's `apikey` header and are never used
as bearer tokens or placed in a `VITE_*` variable.

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

The current free plan is suitable for health checks and the integration shell,
but not reliable full inference with the larger approved artifacts. The service
loads models lazily and keeps at most two by default; that reduces memory but
does not make a 471 MB CatBoost bundle fit safely in 512 MB RAM. Use local
FastAPI for full inference until a host with enough memory is available.
Render also spins down a free web service after 15 minutes without inbound
traffic, so its next request can take about a minute to wake it. These limits
make the free service a development/demo target, not an always-hot production
backend.

## Cloudflare Pages

The React/Vite project is in `frontend/`. The existing `npn-fraud-analyst`
Pages project uses Direct Upload, not Git integration. A push to GitHub does
**not** update the website. Direct Upload projects cannot later be converted to
Git integration; automatic deployment would require a new Pages project or a
CI workflow that invokes Wrangler.

The static build contract is:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Environment variable | `VITE_API_URL=https://<render-service>.onrender.com` |

Deploy the tested production build explicitly. `VITE_API_URL` must be present
when Vite builds because it is embedded into the static application:

```bash
cd frontend
npx wrangler login
npm ci
npm run format:check
npm test
npm run type-check
VITE_API_URL=https://credit-card-fraud-npn.onrender.com npm run build
npx wrangler pages deploy dist --project-name npn-fraud-analyst --branch main
npx wrangler pages deployment list --project-name npn-fraud-analyst
```

The production URL is `https://npn-fraud-analyst.pages.dev`. Do not publish a
build made with the local fallback URL: it would make visitors' browsers call
their own `localhost:8000`.

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

The production build contains the focused CYPHER prediction interface with
Single JSON, CSV Upload, and Real-time modes. No model is selected by default.
All modes use the common spreadsheet result table and on-demand `/explain`
details. It uses only the public `VITE_API_URL`, talks to FastAPI for every
operation, and receives active-stream updates directly from Render SSE. No
Supabase or R2 server credential belongs in the Cloudflare Pages environment.

Run the current workflow in
[SIMPLIFIED_APPLICATION_GUIDE.md](SIMPLIFIED_APPLICATION_GUIDE.md) before
deploying. The original six-page UI is preserved as a historical record in
[MILESTONE_4_FRONTEND_GUIDE.md](MILESTONE_4_FRONTEND_GUIDE.md).
Milestone 5 implementation and verification are recorded in
[MILESTONE_5_CLOUD_DEPLOYMENT.md](MILESTONE_5_CLOUD_DEPLOYMENT.md).

## Official platform references

- [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)
- [Render free-service limits](https://render.com/docs/free)
- [Render Blueprint reference](https://render.com/docs/blueprint-spec)
- [Cloudflare Pages Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/)
- [Cloudflare Wrangler Pages commands](https://developers.cloudflare.com/workers/wrangler/commands/pages/)
