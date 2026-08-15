# Milestone 3: Supabase-backed FIFO streaming

## Outcome

The FastAPI backend can now replay real labelled held-out transactions in strict
chronological order. Labels are stored separately, hidden during inference, and
revealed only on the completed demonstration event. Render publishes live state
directly to the future React client through Server-Sent Events (SSE); Supabase
stores durable run, prediction, alert, and analyst-workflow records.

Cloudflare R2 artifact transfer and the final React console remain later
milestones. The stream does not use random transactions or the unlabelled Kaggle
competition test set.

## Runtime flow

```text
Supabase stream_transactions (ordered, batches of 100)
              + separate stream_ground_truth lookup
                              |
                              v
                 in-memory arrival buffer
                    1, 2, or 5 TPS
                              |
                              v
                  unbounded FIFO queue
                              |
                              v
              one prediction consumer only
                 |                    |
                 | SSE immediately    | batched asynchronous writes
                 v                    v
          React/Cloudflare       Supabase history + alerts
```

One consumer is intentional: it guarantees that completion order matches
arrival order. When scoring is slower than arrivals, the queue grows and the
backlog remains visible. Accepted events are never silently dropped. Stop halts
new arrivals and drains already accepted events.

## Stream API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/stream/datasets` | List ready replay datasets without labels |
| POST | `/stream/start` | Validate configuration, preload models, and start |
| POST | `/stream/pause` | Freeze new work after the current prediction finishes |
| POST | `/stream/resume` | Continue the same FIFO run |
| POST | `/stream/stop` | Stop arrivals and drain accepted events |
| POST | `/stream/restart` | Start the last configuration from sequence zero |
| GET | `/stream/status` | Current counts, queue, throughput, and latency |
| GET | `/stream/events` | Direct Render SSE feed with 15-second heartbeats |

Start request:

```json
{
  "dataset_id": "<Supabase dataset UUID>",
  "selected_models": [
    "logistic_regression.v1",
    "catboost.v2"
  ],
  "transactions_per_second": 2
}
```

Models and versions cannot change during a run. Every selected model is checked
and loaded before the run becomes `RUNNING`. If a selection exceeds
`MODEL_CACHE_SIZE`, startup fails clearly instead of evicting a model needed by
the active stream. Increase the bounded cache only after confirming the Render
instance has enough memory; models are still loaded on request, never all at
application startup.

## FIFO and V2 feature state

Every completed lifecycle record contains sequence number, transaction ID,
arrival time, arrival-time queue position, processing start, completion time,
and status. The producer verifies strictly increasing `(sequence_number)` values
across every Supabase batch.

Each stream gets a private copy of the V2 pre-held-out behavioral reference. A
transaction is scored against history first; only then is its label-free state
added for the next transaction. Unique-value membership uses sorted stable
64-bit pair hashes plus a small per-run delta set. This avoids keeping hundreds
of thousands of Python strings in memory while retaining exact behavior apart
from the negligible theoretical risk of a 64-bit collision.

Generate the ignored local reference with:

```bash
PYTHONPATH=. .venv/bin/python scripts/prepare_behavioral_reference.py
```

The builder reads only the 12 raw fields used by the behavioral state. Loading
all 433 raw inputs would increase peak memory without changing any lookup.

## Supabase schema and security

Migration `20260815182654_milestone_3_streaming_contract.sql` adds:

- dataset split, schema, fraud-count, and fraud-rate metadata;
- canonical `sequence_number` and `transaction_payload` names;
- `stream_runs` for controls and counters;
- `stream_transaction_events` for FIFO lifecycle records;
- `prediction_events` for model-specific scores and thresholds; and
- `fraud_alerts` plus links from `analyst_actions`.

Indexes cover dataset/sequence prefetch, run/sequence history, transaction
lookup, and open-alert risk ordering. Writes use conflict-safe bulk upserts so a
retry after a partial network failure does not duplicate an event.

RLS is enabled on every table. `public`, `anon`, and `authenticated` receive no
table grants or permissive policies. Only FastAPI uses the server secret. Raw
ground truth is not available to the browser, and no secret belongs in a
`VITE_*` variable. The linked hosted migration passed schema lint plus Supabase
security and performance advisors on 2026-08-16.

## Reproducible demonstration data

The source is `data/processed/v2/test.parquet`, the labelled chronological 15%
held-out partition derived from the training dataset. It is Git-ignored.

| Dataset | Rows | Fraud rows | Fraud rate | Selection |
| --- | ---: | ---: | ---: | --- |
| `held_out_full` | 88,581 | 3,083 | 3.4804% | Entire held-out partition |
| `demo_chronological` | 600 | 21 | 3.5000% | First 600 rows in natural order |

The demo is not oversampled or reordered. Its small fraud-rate difference is a
consequence of taking the first natural window, not changing class balance. At
one TPS it runs for approximately ten minutes.

Validate without cloud access:

```bash
.venv/bin/python scripts/upload_stream_datasets.py all --dry-run
```

Upload after setting `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the ignored
local `.env`:

```bash
.venv/bin/python scripts/upload_stream_datasets.py demo_chronological
.venv/bin/python scripts/upload_stream_datasets.py held_out_full
```

Transactions and labels are uploaded in batches of at most 100. Uploads are
idempotent, and a dataset is not marked `ready` until all payload and label
batches succeed. The safe three-row fixture in `tests/fixtures/` is a minimized
real sample for repository tests; it is not a substitute for model inference.

## Verification

```bash
PYTHONPATH=. .venv/bin/pytest -q
PYTHONPATH=. .venv/bin/python scripts/verify_selected_models.py --sample-size 4
npx --yes supabase db lint --linked --level warning
npx --yes supabase db advisors --linked --type security
npx --yes supabase db advisors --linked --type performance
```

Automated coverage includes ordered prefetch, hidden labels, bulk persistence,
retry-safe writes, FIFO order, pause/resume, stop-and-drain, persistence failure,
V2 sequential-state parity, typed stream controls, and unavailable-integration
errors.

## Troubleshooting

- `streaming_unavailable`: configure the two server-only Supabase variables.
- `model_cache_too_small`: raise `MODEL_CACHE_SIZE` within 1–8 after checking
  memory, or select fewer models.
- `v2_reference_unavailable`: run the reference preparation command.
- `persistence_failed` SSE event: scoring finished but durable storage failed
  after three attempts; the run ends `FAILED` and reports the unpersisted count.
- Growing queue: expected when prediction latency exceeds the selected arrival
  rate; pause or stop rather than dropping transactions.
