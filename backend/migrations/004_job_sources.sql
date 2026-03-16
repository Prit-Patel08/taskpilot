create extension if not exists "pgcrypto";

create table if not exists job_sources (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references jobs(id) on delete cascade,
  source text not null,
  external_id text,
  raw_payload jsonb,
  fetched_at timestamptz not null default now(),
  unique (job_id, source, external_id)
);

create index if not exists job_sources_job_idx
  on job_sources (job_id);

create index if not exists job_sources_source_idx
  on job_sources (source);
