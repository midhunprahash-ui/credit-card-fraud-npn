-- Milestone 3 streaming contract.
--
-- All application access is server-side through the service_role/secret key.
-- Browser roles receive no grants or policies. Ground-truth labels remain in
-- stream_ground_truth and are read only after prediction in demonstration mode.

alter table public.stream_datasets
    add column split text not null default 'chronological_test'
        check (split in ('chronological_test', 'demo_chronological')),
    add column schema_version text not null default 'raw-v1',
    add column fraud_count integer check (fraud_count is null or fraud_count >= 0),
    add column fraud_rate double precision
        check (fraud_rate is null or fraud_rate between 0 and 1);

alter table public.stream_transactions
    rename column sequence_no to sequence_number;
alter table public.stream_transactions
    rename column model_payload to transaction_payload;

drop index if exists public.stream_transactions_fifo_idx;

create index stream_transactions_dataset_sequence_idx
    on public.stream_transactions (dataset_id, sequence_number);
create index stream_transactions_transaction_id_idx
    on public.stream_transactions (transaction_id);

create table public.stream_runs (
    id uuid primary key default gen_random_uuid(),
    dataset_id uuid not null
        references public.stream_datasets(id) on delete restrict,
    selected_versions text[] not null,
    selected_models text[] not null,
    transactions_per_second integer not null
        check (transactions_per_second in (1, 2, 5)),
    status text not null default 'LOADING'
        check (status in (
            'LOADING', 'RUNNING', 'PAUSED', 'STOPPED', 'COMPLETED', 'FAILED'
        )),
    current_sequence integer not null default -1 check (current_sequence >= -1),
    received_count integer not null default 0 check (received_count >= 0),
    processed_count integer not null default 0 check (processed_count >= 0),
    fraud_count integer not null default 0 check (fraud_count >= 0),
    failed_count integer not null default 0 check (failed_count >= 0),
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (
        cardinality(selected_versions) > 0
        and selected_versions <@ array['V1', 'V2']::text[]
    ),
    check (
        cardinality(selected_models) > 0
        and selected_models <@ array[
            'logistic_regression.v1',
            'lightgbm.v1',
            'catboost.v1',
            'neural_network.v1',
            'logistic_regression.v2',
            'lightgbm.v2',
            'catboost.v2',
            'neural_network.v2'
        ]::text[]
    ),
    check (processed_count + failed_count <= received_count)
);

create table public.stream_transaction_events (
    id bigint generated always as identity primary key,
    stream_run_id uuid not null references public.stream_runs(id) on delete cascade,
    stream_transaction_id bigint not null
        references public.stream_transactions(id) on delete restrict,
    sequence_number integer not null check (sequence_number >= 0),
    transaction_id bigint not null,
    arrival_time timestamptz not null,
    queue_position integer not null check (queue_position >= 0),
    processing_started_at timestamptz,
    completed_at timestamptz,
    status text not null check (status in ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')),
    error_code text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (stream_run_id, sequence_number),
    unique (stream_run_id, stream_transaction_id),
    check (
        (status = 'QUEUED' and processing_started_at is null and completed_at is null)
        or (status = 'PROCESSING' and processing_started_at is not null and completed_at is null)
        or (status in ('COMPLETED', 'FAILED') and processing_started_at is not null and completed_at is not null)
    )
);

create table public.prediction_events (
    id uuid primary key default gen_random_uuid(),
    stream_run_id uuid not null references public.stream_runs(id) on delete cascade,
    stream_transaction_event_id bigint not null
        references public.stream_transaction_events(id) on delete cascade,
    sequence_number integer not null check (sequence_number >= 0),
    transaction_id bigint not null,
    model_identifier text not null check (model_identifier in (
        'logistic_regression.v1',
        'lightgbm.v1',
        'catboost.v1',
        'neural_network.v1',
        'logistic_regression.v2',
        'lightgbm.v2',
        'catboost.v2',
        'neural_network.v2'
    )),
    risk_score double precision not null check (risk_score between 0 and 1),
    threshold double precision not null check (threshold between 0 and 1),
    decision boolean not null,
    actual_label boolean,
    latency_ms double precision not null check (latency_ms >= 0),
    model_run_id text not null,
    created_at timestamptz not null default now(),
    unique (stream_run_id, sequence_number, model_identifier)
);

create table public.fraud_alerts (
    id uuid primary key default gen_random_uuid(),
    stream_run_id uuid not null references public.stream_runs(id) on delete cascade,
    stream_transaction_event_id bigint not null
        references public.stream_transaction_events(id) on delete cascade,
    transaction_id bigint not null,
    status text not null default 'OPEN'
        check (status in ('OPEN', 'IN_REVIEW', 'CONFIRMED_FRAUD', 'LEGITIMATE', 'ESCALATED', 'CLOSED')),
    highest_risk_score double precision not null
        check (highest_risk_score between 0 and 1),
    model_agreement integer not null check (model_agreement >= 0),
    selected_model_count integer not null check (selected_model_count > 0),
    suspicious_amount numeric(18, 2)
        check (suspicious_amount is null or suspicious_amount >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (stream_run_id, transaction_id),
    check (model_agreement <= selected_model_count)
);

alter table public.analyst_actions
    rename column analyst_subject to analyst_identifier;
alter table public.analyst_actions
    rename column notes to note;
alter table public.analyst_actions
    add column fraud_alert_id uuid
        references public.fraud_alerts(id) on delete set null;
alter table public.analyst_actions
    drop constraint analyst_actions_check;
alter table public.analyst_actions
    add constraint analyst_actions_target_check check (
        alert_id is not null
        or prediction_id is not null
        or fraud_alert_id is not null
    );

create index stream_runs_dataset_created_idx
    on public.stream_runs (dataset_id, created_at desc);
create index stream_runs_active_idx
    on public.stream_runs (status, updated_at desc)
    where status in ('LOADING', 'RUNNING', 'PAUSED');
create index stream_transaction_events_run_sequence_idx
    on public.stream_transaction_events (stream_run_id, sequence_number);
create index prediction_events_run_sequence_idx
    on public.prediction_events (stream_run_id, sequence_number);
create index prediction_events_transaction_idx
    on public.prediction_events (transaction_id, created_at desc);
create index fraud_alerts_status_risk_idx
    on public.fraud_alerts (status, highest_risk_score desc, created_at)
    where status in ('OPEN', 'IN_REVIEW', 'ESCALATED');
create index fraud_alerts_transaction_idx
    on public.fraud_alerts (transaction_id, created_at desc);
create index analyst_actions_fraud_alert_idx
    on public.analyst_actions (fraud_alert_id, created_at desc);

alter table public.stream_runs enable row level security;
alter table public.stream_transaction_events enable row level security;
alter table public.prediction_events enable row level security;
alter table public.fraud_alerts enable row level security;

revoke all on table public.stream_runs from public, anon, authenticated;
revoke all on table public.stream_transaction_events from public, anon, authenticated;
revoke all on table public.prediction_events from public, anon, authenticated;
revoke all on table public.fraud_alerts from public, anon, authenticated;

grant select, insert, update, delete on table public.stream_runs to service_role;
grant select, insert, update, delete on table public.stream_transaction_events to service_role;
grant select, insert, update, delete on table public.prediction_events to service_role;
grant select, insert, update, delete on table public.fraud_alerts to service_role;
grant usage, select on all sequences in schema public to service_role;
