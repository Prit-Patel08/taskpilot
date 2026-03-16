create extension if not exists "pgcrypto";

create table if not exists ingestion_metrics (
  id uuid primary key default gen_random_uuid(),
  metric_date date not null,
  source text not null default 'unknown',
  total_runs integer not null default 0,
  total_inserted integer not null default 0,
  total_skipped integer not null default 0,
  total_duplicates integer not null default 0,
  failed_runs integer not null default 0,
  created_at timestamptz not null default now(),
  unique (metric_date, source)
);

create index if not exists ingestion_metrics_date_idx on ingestion_metrics (metric_date desc);
