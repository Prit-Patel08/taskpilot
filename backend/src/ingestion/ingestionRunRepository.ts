import { pool } from "../db";

export async function startIngestionRun(
  companyId: string,
  source: string,
  queueId?: string,
): Promise<string> {
  const res = await pool.query<{ id: string }>(
    `
    insert into ingestion_runs (queue_id, company_id, source, status)
    values ($1, $2, $3, 'running')
    returning id
    `,
    [queueId ?? null, companyId, source],
  );

  return res.rows[0].id;
}

export async function finishIngestionRun(
  runId: string,
  status: "success" | "failed",
  inserted: number,
  skipped: number,
  duplicates: number,
  error?: string,
): Promise<void> {
  await pool.query(
    `
    update ingestion_runs
    set status = $2,
        finished_at = now(),
        inserted = $3,
        skipped = $4,
        duplicates = $5,
        error = $6
    where id = $1
    `,
    [runId, status, inserted, skipped, duplicates, error ?? null],
  );
}
