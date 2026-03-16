import { pool } from "../db";

type MetricsRow = {
  metric_date: string;
  source: string;
  total_runs: number;
  total_inserted: number;
  total_skipped: number;
  total_duplicates: number;
  failed_runs: number;
};

export async function upsertMetrics(rows: MetricsRow[]): Promise<void> {
  if (!rows.length) return;

  const values: unknown[] = [];
  const placeholders: string[] = [];

  rows.forEach((row, idx) => {
    const base = idx * 7;
    placeholders.push(
      `($${base + 1}, $${base + 2}, $${base + 3}, $${base + 4}, $${base + 5}, $${base + 6}, $${base + 7})`,
    );
    values.push(
      row.metric_date,
      row.source,
      row.total_runs,
      row.total_inserted,
      row.total_skipped,
      row.total_duplicates,
      row.failed_runs,
    );
  });

  await pool.query(
    `
    insert into ingestion_metrics (
      metric_date,
      source,
      total_runs,
      total_inserted,
      total_skipped,
      total_duplicates,
      failed_runs
    )
    values ${placeholders.join(",")}
    on conflict (metric_date, source) do update
    set total_runs = excluded.total_runs,
        total_inserted = excluded.total_inserted,
        total_skipped = excluded.total_skipped,
        total_duplicates = excluded.total_duplicates,
        failed_runs = excluded.failed_runs,
        created_at = now()
    `,
    values,
  );
}

export async function getQueueDepth(): Promise<number> {
  const res = await pool.query<{ count: string }>(
    `
    select count(*)::text as count
    from ingestion_queue
    where status = 'queued'
      and scheduled_for <= now()
    `,
  );
  return parseInt(res.rows[0]?.count ?? "0", 10);
}

export async function getFailureRate(lastMinutes = 60): Promise<number> {
  const res = await pool.query<{
    total: string;
    failed: string;
  }>(
    `
    select
      count(*)::text as total,
      count(*) filter (where status = 'failed')::text as failed
    from ingestion_runs
    where started_at >= now() - ($1 || ' minutes')::interval
    `,
    [lastMinutes],
  );

  const total = parseInt(res.rows[0]?.total ?? "0", 10);
  const failed = parseInt(res.rows[0]?.failed ?? "0", 10);
  if (!total) return 0;
  return failed / total;
}
