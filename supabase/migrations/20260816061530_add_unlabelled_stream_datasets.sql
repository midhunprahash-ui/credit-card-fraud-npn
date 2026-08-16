-- Support production-style inference datasets that do not contain ground truth.
-- Existing browser roles remain revoked; all access continues through FastAPI.

alter table public.stream_datasets
    add column labels_available boolean not null default true;

alter table public.stream_datasets
    drop constraint stream_datasets_split_check;

alter table public.stream_datasets
    add constraint stream_datasets_split_check
    check (split in (
        'chronological_test',
        'demo_chronological',
        'kaggle_inference'
    ));

comment on column public.stream_datasets.labels_available is
    'True only when every transaction has separately stored ground truth.';
