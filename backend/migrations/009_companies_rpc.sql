create or replace function distinct_companies(
  search text default null,
  limit_count int default 500
)
returns table(company text)
language sql
stable
as $$
  select distinct company
  from jobs
  where company is not null
    and (search is null or company ilike '%' || search || '%')
  order by company asc
  limit limit_count;
$$;
