alter table jobs
  add column if not exists search_tsv tsvector;

create index if not exists jobs_search_tsv_idx
  on jobs using gin (search_tsv);

create or replace function jobs_search_tsv_update()
returns trigger as $$
begin
  new.search_tsv :=
    to_tsvector(
      'english',
      coalesce(new.title, '') || ' ' ||
      coalesce(new.company, '') || ' ' ||
      coalesce(new.location, '') || ' ' ||
      coalesce(new.description, '')
    );
  return new;
end;
$$ language plpgsql;

drop trigger if exists jobs_search_tsv_trigger on jobs;
create trigger jobs_search_tsv_trigger
before insert or update on jobs
for each row execute function jobs_search_tsv_update();

update jobs
set search_tsv =
  to_tsvector(
    'english',
    coalesce(title, '') || ' ' ||
    coalesce(company, '') || ' ' ||
    coalesce(location, '') || ' ' ||
    coalesce(description, '')
  )
where search_tsv is null;
