create extension if not exists "pgcrypto";

alter table companies
  add column if not exists crawl_interval_seconds integer not null default 900;

alter table companies
  add column if not exists is_active boolean not null default true;

create table if not exists ingestion_queue (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  scheduled_for timestamptz not null default now(),
  status text not null default 'queued',
  attempts integer not null default 0,
  locked_at timestamptz,
  locked_by text,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ingestion_queue_status_idx
  on ingestion_queue (status, scheduled_for);

create index if not exists ingestion_queue_company_idx
  on ingestion_queue (company_id);

create index if not exists ingestion_queue_locked_at_idx
  on ingestion_queue (locked_at);

create unique index if not exists ingestion_queue_company_active_idx
  on ingestion_queue (company_id)
  where status in ('queued', 'processing');

create table if not exists ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  queue_id uuid references ingestion_queue(id) on delete set null,
  company_id uuid not null references companies(id) on delete cascade,
  source text,
  status text not null default 'running',
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  inserted integer not null default 0,
  skipped integer not null default 0,
  duplicates integer not null default 0,
  error text
);

create index if not exists ingestion_runs_company_idx
  on ingestion_runs (company_id, started_at desc);

create index if not exists ingestion_runs_status_idx
  on ingestion_runs (status);

drop trigger if exists ingestion_queue_set_timestamp on ingestion_queue;
create trigger ingestion_queue_set_timestamp
before update on ingestion_queue
for each row execute function set_timestamp();
