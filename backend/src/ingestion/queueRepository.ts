import { pool } from "../db";
import type { QueueTask } from "./types";

export async function enqueueDueCompanies(limit: number): Promise<number> {
  const res = await pool.query<{ company_id: string }>(
    `
    insert into ingestion_queue (company_id, scheduled_for)
    select id, now()
    from companies
    where is_active = true
      and (
        last_crawled is null
        or last_crawled <= now() - (coalesce(crawl_interval_seconds, 900) || ' seconds')::interval
      )
    order by coalesce(last_crawled, to_timestamp(0)) asc
    limit $1
    on conflict (company_id) where status in ('queued', 'processing') do nothing
    returning company_id
    `,
    [limit],
  );

  return res.rowCount ?? 0;
}

export async function claimQueueBatch(
  limit: number,
  workerId: string,
  claimTimeoutMs: number,
  shardTotal = 1,
  shardIndex = 0,
): Promise<QueueTask[]> {
  const params: Array<number | string> = [limit, workerId, claimTimeoutMs];
  const shardClause =
    shardTotal > 1
      ? "and mod(abs(hashtext(company_id::text)), $4) = $5"
      : "";

  if (shardTotal > 1) {
    params.push(shardTotal, shardIndex);
  }

  const res = await pool.query<QueueTask>(
    `
    with next as (
      select id
      from ingestion_queue
      where (
        status = 'queued' and scheduled_for <= now()
      ) or (
        status = 'processing'
        and coalesce(locked_at, to_timestamp(0)) <= now() - ($3 || ' milliseconds')::interval
      )
      ${shardClause}
      order by scheduled_for asc
      limit $1
      for update skip locked
    )
    update ingestion_queue
    set status = 'processing',
        locked_at = now(),
        locked_by = $2,
        attempts = attempts + 1,
        updated_at = now()
    where id in (select id from next)
    returning id, company_id, attempts, scheduled_for
    `,
    params,
  );

  return res.rows;
}

export async function markQueueSuccess(id: string): Promise<void> {
  await pool.query(
    `
    update ingestion_queue
    set status = 'done',
        updated_at = now(),
        locked_at = null,
        locked_by = null
    where id = $1
    `,
    [id],
  );
}

export async function markQueueFailure(
  id: string,
  error: string,
  retryDelayMs: number,
  attempts: number,
  maxAttempts: number,
): Promise<"failed" | "requeued"> {
  const res = await pool.query<{ status: string }>(
    `
    update ingestion_queue
    set status = case when $4 >= $5 then 'failed' else 'queued' end,
        last_error = $1,
        scheduled_for = case
          when $4 >= $5 then scheduled_for
          else now() + ($2 || ' milliseconds')::interval
        end,
        updated_at = now(),
        locked_at = null,
        locked_by = null
    where id = $3
    returning status
    `,
    [error, retryDelayMs, id, attempts, maxAttempts],
  );

  return res.rows[0]?.status === "failed" ? "failed" : "requeued";
}
