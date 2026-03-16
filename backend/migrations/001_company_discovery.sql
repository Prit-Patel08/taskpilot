create extension if not exists "pgcrypto";

create table if not exists company_candidates (
  id uuid primary key default gen_random_uuid(),
  domain text not null,
  guessed_careers_url text,
  ats_type text,
  ats_slug text,
  confidence numeric not null default 0,
  discovery_source text not null default 'crawl',
  status text not null default 'new',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (domain, guessed_careers_url)
);

create table if not exists company_sources (
  id uuid primary key default gen_random_uuid(),
  company_id uuid,
  ats_type text not null,
  ats_slug text,
  career_url text,
  confidence numeric not null default 0,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists company_candidates_domain_idx on company_candidates (domain);
create index if not exists company_candidates_ats_type_idx on company_candidates (ats_type);
create index if not exists company_candidates_status_idx on company_candidates (status);
create index if not exists company_sources_company_id_idx on company_sources (company_id);
create index if not exists company_sources_ats_type_idx on company_sources (ats_type);

create or replace function set_timestamp()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists company_candidates_set_timestamp on company_candidates;
create trigger company_candidates_set_timestamp
before update on company_candidates
for each row execute function set_timestamp();

drop trigger if exists company_sources_set_timestamp on company_sources;
create trigger company_sources_set_timestamp
before update on company_sources
for each row execute function set_timestamp();
