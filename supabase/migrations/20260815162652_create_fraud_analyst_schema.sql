-- Fraud analyst application storage.
--
-- The browser talks to Render, never directly to these tables. Held-out labels
-- live in a separate table so inference code cannot accidentally include them
-- in a model payload.

create table public.stream_datasets (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    description text,
    supported_versions text[] not null default array['V1', 'V2']::text[],
    row_count integer not null check (row_count >= 0),
    status text not null default 'ready'
        check (status in ('preparing', 'ready', 'archived')),
    created_at timestamptz not null default now(),
    check (
        cardinality(supported_versions) > 0
        and supported_versions <@ array['V1', 'V2']::text[]
    )
);

create table public.stream_transactions (
    id bigint generated always as identity primary key,
    dataset_id uuid not null references public.stream_datasets(id) on delete cascade,
    sequence_no integer not null check (sequence_no >= 0),
    transaction_id bigint not null,
    transaction_dt double precision not null,
    model_payload jsonb not null,
    created_at timestamptz not null default now(),
    unique (dataset_id, sequence_no),
    unique (dataset_id, transaction_id),
    check (not model_payload ? 'isFraud')
);

create table public.stream_ground_truth (
    stream_transaction_id bigint primary key
        references public.stream_transactions(id) on delete cascade,
    is_fraud boolean not null,
    revealed_at timestamptz,
    created_at timestamptz not null default now()
);

create table public.prediction_history (
    id uuid primary key default gen_random_uuid(),
    stream_transaction_id bigint references public.stream_transactions(id) on delete set null,
    source_transaction_id bigint,
    model_name text not null check (
        model_name in (
            'Logistic Regression.V1',
            'LightGBM.V1',
            'CatBoost.V1',
            'Neural Network.V1',
            'Logistic Regression.V2',
            'LightGBM.V2',
            'CatBoost.V2',
            'Neural Network.V2'
        )
    ),
    version_name text not null check (version_name in ('V1', 'V2')),
    input_mode text not null check (input_mode in ('Manual', 'Real-time')),
    manual_mode text check (
        manual_mode is null or manual_mode in ('Single Transaction', 'CSV Upload')
    ),
    risk_score double precision not null check (risk_score between 0 and 1),
    decision_threshold double precision not null
        check (decision_threshold between 0 and 1),
    predicted_fraud boolean not null,
    latency_ms double precision not null check (latency_ms >= 0),
    run_id text not null,
    created_at timestamptz not null default now(),
    check (
        (input_mode = 'Manual' and manual_mode is not null)
        or (input_mode = 'Real-time' and manual_mode is null)
    ),
    check (model_name like '%.' || version_name)
);

create table public.alerts (
    id uuid primary key default gen_random_uuid(),
    prediction_id uuid not null unique
        references public.prediction_history(id) on delete cascade,
    severity text not null check (severity in ('LOW', 'MEDIUM', 'HIGH')),
    status text not null default 'OPEN'
        check (status in ('OPEN', 'IN_REVIEW', 'RESOLVED', 'DISMISSED')),
    reason text not null,
    created_at timestamptz not null default now(),
    resolved_at timestamptz
);

create table public.analyst_actions (
    id uuid primary key default gen_random_uuid(),
    alert_id uuid references public.alerts(id) on delete set null,
    prediction_id uuid references public.prediction_history(id) on delete set null,
    analyst_subject text not null,
    action text not null check (
        action in ('OPENED', 'ASSIGNED', 'CONFIRMED_FRAUD', 'MARKED_LEGITIMATE', 'ESCALATED', 'NOTE_ADDED')
    ),
    notes text,
    created_at timestamptz not null default now(),
    check (alert_id is not null or prediction_id is not null)
);

create index stream_transactions_fifo_idx
    on public.stream_transactions (dataset_id, transaction_dt, transaction_id);
create index prediction_history_created_idx
    on public.prediction_history (created_at desc);
create index prediction_history_transaction_idx
    on public.prediction_history (source_transaction_id, created_at desc);
create index alerts_status_created_idx
    on public.alerts (status, created_at desc);
create index analyst_actions_alert_idx
    on public.analyst_actions (alert_id, created_at desc);

alter table public.stream_datasets enable row level security;
alter table public.stream_transactions enable row level security;
alter table public.stream_ground_truth enable row level security;
alter table public.prediction_history enable row level security;
alter table public.alerts enable row level security;
alter table public.analyst_actions enable row level security;

revoke all on table public.stream_datasets from anon, authenticated;
revoke all on table public.stream_transactions from anon, authenticated;
revoke all on table public.stream_ground_truth from anon, authenticated;
revoke all on table public.prediction_history from anon, authenticated;
revoke all on table public.alerts from anon, authenticated;
revoke all on table public.analyst_actions from anon, authenticated;

grant select, insert, update, delete on table public.stream_datasets to service_role;
grant select, insert, update, delete on table public.stream_transactions to service_role;
grant select, insert, update, delete on table public.stream_ground_truth to service_role;
grant select, insert, update, delete on table public.prediction_history to service_role;
grant select, insert, update, delete on table public.alerts to service_role;
grant select, insert, update, delete on table public.analyst_actions to service_role;
grant usage, select on all sequences in schema public to service_role;
