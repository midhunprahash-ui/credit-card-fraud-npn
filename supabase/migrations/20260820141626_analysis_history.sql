-- Browser-scoped, server-only analysis history for single JSON, CSV batches,
-- and real-time replays. The browser never receives a Supabase key; all access
-- is mediated by the FastAPI service using the service role.

create table public.analysis_runs (
    id uuid primary key default gen_random_uuid(),
    client_id uuid not null,
    input_mode text not null check (input_mode in ('single', 'csv', 'realtime')),
    source_name text,
    stream_run_id uuid unique references public.stream_runs(id) on delete set null,
    selected_models text[] not null,
    status text not null default 'PROCESSING'
        check (status in ('PROCESSING', 'COMPLETED', 'PARTIAL', 'FAILED')),
    total_transactions integer not null default 0 check (total_transactions >= 0),
    successful_transactions integer not null default 0
        check (successful_transactions >= 0),
    failed_transactions integer not null default 0 check (failed_transactions >= 0),
    summary jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (cardinality(selected_models) between 1 and 8),
    check (successful_transactions + failed_transactions <= total_transactions)
);

create table public.analysis_transactions (
    id uuid primary key default gen_random_uuid(),
    analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
    ordinal integer not null check (ordinal >= 0),
    transaction_id bigint,
    raw_transaction_id text,
    input_payload jsonb not null default '{}'::jsonb,
    status text not null check (status in ('COMPLETED', 'FAILED')),
    error_code text,
    error_message text,
    created_at timestamptz not null default now(),
    unique (analysis_run_id, ordinal),
    check (
        (status = 'COMPLETED' and error_code is null and error_message is null)
        or status = 'FAILED'
    )
);

create table public.analysis_prediction_results (
    id uuid primary key default gen_random_uuid(),
    analysis_transaction_id uuid not null
        references public.analysis_transactions(id) on delete cascade,
    model_identifier text not null,
    model_name text not null,
    model_version text not null check (model_version in ('V1', 'V2')),
    model_run_id text not null,
    risk_score double precision not null check (risk_score between 0 and 1),
    threshold double precision not null check (threshold between 0 and 1),
    decision boolean not null,
    latency_ms double precision not null check (latency_ms >= 0),
    explanation_status text not null default 'NOT_GENERATED'
        check (explanation_status in ('NOT_GENERATED', 'COMPLETED', 'FAILED')),
    explanation_technique text,
    explanation_technique_label text,
    top_contributed_features jsonb,
    reasoning text,
    reasoning_source text check (
        reasoning_source is null or reasoning_source in ('openrouter', 'template')
    ),
    explanation_error text,
    explained_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (analysis_transaction_id, model_identifier)
);

create index analysis_runs_client_mode_created_idx
    on public.analysis_runs (client_id, input_mode, created_at desc);
create index analysis_transactions_run_ordinal_idx
    on public.analysis_transactions (analysis_run_id, ordinal);
create index analysis_transactions_transaction_id_idx
    on public.analysis_transactions (transaction_id, created_at desc);
create index analysis_prediction_results_transaction_idx
    on public.analysis_prediction_results (analysis_transaction_id, model_identifier);

alter table public.analysis_runs enable row level security;
alter table public.analysis_transactions enable row level security;
alter table public.analysis_prediction_results enable row level security;

revoke all on table public.analysis_runs from public, anon, authenticated;
revoke all on table public.analysis_transactions from public, anon, authenticated;
revoke all on table public.analysis_prediction_results from public, anon, authenticated;

grant select, insert, update, delete on table public.analysis_runs to service_role;
grant select, insert, update, delete on table public.analysis_transactions to service_role;
grant select, insert, update, delete on table public.analysis_prediction_results to service_role;
