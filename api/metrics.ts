/**
 * Server-side metrics API for monitoring dashboard.
 * GET /api/metrics
 *
 * Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 */
import { createClient } from "@supabase/supabase-js";

export default async function handler(
  req: { method?: string },
  res: { status: (n: number) => { end: () => void; json: (x: unknown) => void } },
) {
  try {
    if (req.method !== "GET") {
      res.status(405).end();
      return;
    }

    const url = process.env.SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    if (!url || !serviceKey) {
      res.status(500).json({ ok: false, error: "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY" });
      return;
    }

    const supabase = createClient(url, serviceKey);

    const [metricsRes, queueRes, runsRes] = await Promise.all([
      supabase
        .from("ingestion_metrics")
        .select("metric_date, source, total_runs, total_inserted, total_skipped, total_duplicates, failed_runs")
        .order("metric_date", { ascending: false })
        .limit(30),
      supabase
        .from("ingestion_queue")
        .select("id", { count: "exact", head: true })
        .eq("status", "queued"),
      supabase
        .from("ingestion_runs")
        .select("status", { count: "exact" })
        .gte("started_at", new Date(Date.now() - 60 * 60 * 1000).toISOString()),
    ]);

    if (metricsRes.error || queueRes.error || runsRes.error) {
      res.status(500).json({
        ok: false,
        error: metricsRes.error?.message ?? queueRes.error?.message ?? runsRes.error?.message ?? "Unknown error",
      });
      return;
    }

    const queueDepth = queueRes.count ?? 0;
    const runs = runsRes.data ?? [];
    const totalRuns = runsRes.count ?? runs.length ?? 0;
    const failedRuns = runs.filter((r) => r.status === "failed").length;
    const failureRate = totalRuns > 0 ? failedRuns / totalRuns : 0;

    const totals = (metricsRes.data ?? []).reduce(
      (acc, row) => {
        acc.runs += row.total_runs;
        acc.inserted += row.total_inserted;
        acc.skipped += row.total_skipped;
        acc.duplicates += row.total_duplicates;
        acc.failed += row.failed_runs;
        return acc;
      },
      { runs: 0, inserted: 0, skipped: 0, duplicates: 0, failed: 0 },
    );

    res.status(200).json({
      ok: true,
      metrics: {
        queueDepth,
        failureRate,
        totals,
        bySource: metricsRes.data ?? [],
      },
    });
  } catch (err) {
    res.status(500).json({
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    });
  }
}
