import { pathToFileURL } from "url";
import { pool } from "../db";
import { log } from "../logger";
import { upsertMetrics } from "./metricsRepository";

type MetricsRow = {
  metric_date: string;
  source: string;
  total_runs: number;
  total_inserted: number;
  total_skipped: number;
  total_duplicates: number;
  failed_runs: number;
};

export async function runMetricsRollup(): Promise<void> {
  const res = await pool.query<MetricsRow>(
    `
    select
      (date_trunc('day', started_at))::date as metric_date,
      coalesce(source, 'unknown') as source,
      count(*)::int as total_runs,
      coalesce(sum(inserted), 0)::int as total_inserted,
      coalesce(sum(skipped), 0)::int as total_skipped,
      coalesce(sum(duplicates), 0)::int as total_duplicates,
      count(*) filter (where status = 'failed')::int as failed_runs
    from ingestion_runs
    where started_at >= date_trunc('day', now() - interval '1 day')
    group by metric_date, source
    `,
  );

  await upsertMetrics(res.rows);
  log.info("Metrics rollup complete", { rows: res.rows.length });
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  runMetricsRollup().catch((err) => {
    log.error("Metrics rollup failed", { error: (err as Error).message });
    process.exit(1);
  });
}
