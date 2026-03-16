alter table companies
  add column if not exists reputation_score numeric not null default 0.5;

alter table jobs
  add column if not exists rank_score numeric not null default 0.0;

create index if not exists jobs_rank_score_idx on jobs (rank_score desc);
