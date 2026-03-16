create extension if not exists "pgcrypto";

do $$
begin
  if not exists (
    select 1
    from information_schema.tables
    where table_schema = 'public'
      and table_name = 'companies'
  ) then
    create table public.companies (
      id uuid primary key default gen_random_uuid(),
      name text not null,
      ats_type text,
      ats_slug text,
      career_url text,
      crawl_interval_seconds integer not null default 900,
      is_active boolean not null default true,
      last_crawled timestamptz,
      created_at timestamptz not null default now(),
      updated_at timestamptz not null default now()
    );
  end if;
end $$;

alter table companies
  add column if not exists ats_type text,
  add column if not exists ats_slug text,
  add column if not exists career_url text,
  add column if not exists crawl_interval_seconds integer not null default 900,
  add column if not exists is_active boolean not null default true,
  add column if not exists last_crawled timestamptz,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

create index if not exists companies_ats_type_idx on companies (ats_type);
create index if not exists companies_last_crawled_idx on companies (last_crawled);

create or replace function set_timestamp()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists companies_set_timestamp on companies;
create trigger companies_set_timestamp
before update on companies
for each row execute function set_timestamp();

do $$
begin
  if not exists (
    select 1
    from information_schema.tables
    where table_schema = 'public'
      and table_name = 'jobs'
  ) then
    create table public.jobs (
      id uuid primary key default gen_random_uuid(),
      company_id uuid references companies(id) on delete set null,
      source text,
      external_id text,
      hash text,
      company text,
      title text,
      location text,
      location_raw text,
      location_norm text,
      remote_type text,
      seniority text,
      employment_type text,
      description text,
      apply_url text,
      posted_at timestamptz,
      first_seen timestamptz not null default now(),
      last_seen timestamptz not null default now(),
      created_at timestamptz not null default now()
    );
  end if;
end $$;

alter table jobs
  add column if not exists company_id uuid references companies(id) on delete set null,
  add column if not exists source text,
  add column if not exists external_id text,
  add column if not exists hash text,
  add column if not exists company text,
  add column if not exists title text,
  add column if not exists location text,
  add column if not exists location_raw text,
  add column if not exists location_norm text,
  add column if not exists remote_type text,
  add column if not exists seniority text,
  add column if not exists employment_type text,
  add column if not exists description text,
  add column if not exists apply_url text,
  add column if not exists posted_at timestamptz,
  add column if not exists first_seen timestamptz not null default now(),
  add column if not exists last_seen timestamptz not null default now(),
  add column if not exists created_at timestamptz not null default now();

do $$
begin
  if exists (
    select 1
    from pg_constraint
    where conname = 'jobs_external_id_source_key'
  ) then
    alter table jobs drop constraint jobs_external_id_source_key;
  end if;
end $$;

create unique index if not exists jobs_hash_unique_idx on jobs (hash);
create unique index if not exists jobs_company_source_external_idx
  on jobs (company_id, source, external_id)
  where external_id is not null;
create index if not exists jobs_company_id_idx on jobs (company_id);
create index if not exists jobs_posted_at_idx on jobs (posted_at desc);
create index if not exists jobs_location_norm_idx on jobs (location_norm);
create index if not exists jobs_remote_type_idx on jobs (remote_type);
create index if not exists jobs_seniority_idx on jobs (seniority);
create index if not exists jobs_employment_type_idx on jobs (employment_type);
create index if not exists jobs_apply_url_idx on jobs (apply_url);
