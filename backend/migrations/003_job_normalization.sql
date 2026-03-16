alter table jobs
  add column if not exists location_raw text,
  add column if not exists location_norm text,
  add column if not exists remote_type text,
  add column if not exists seniority text,
  add column if not exists employment_type text;

create index if not exists jobs_location_norm_idx on jobs (location_norm);
create index if not exists jobs_remote_type_idx on jobs (remote_type);
create index if not exists jobs_seniority_idx on jobs (seniority);
create index if not exists jobs_employment_type_idx on jobs (employment_type);
