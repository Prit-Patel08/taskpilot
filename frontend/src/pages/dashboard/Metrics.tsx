import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Loader2, TrendingUp, Activity, BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { fetchMetrics, type IngestionMetricsRow } from "@/lib/jobsDb";

type MetricsState = {
  queueDepth: number;
  failureRate: number;
  totals: {
    runs: number;
    inserted: number;
    skipped: number;
    duplicates: number;
    failed: number;
  };
  bySource: IngestionMetricsRow[];
};

const Metrics = () => {
  const [metrics, setMetrics] = useState<MetricsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMetrics();
      setMetrics(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  const bySource = useMemo(() => {
    if (!metrics?.bySource) return [];
    return metrics.bySource.slice(0, 20);
  }, [metrics]);

  const dailyTotals = useMemo(() => {
    const map = new Map<string, { inserted: number; failed: number }>();
    (metrics?.bySource ?? []).forEach((row) => {
      const prev = map.get(row.metric_date) ?? { inserted: 0, failed: 0 };
      map.set(row.metric_date, {
        inserted: prev.inserted + row.total_inserted,
        failed: prev.failed + row.failed_runs,
      });
    });
    const entries = Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-14)
      .map(([date, totals]) => ({ date, ...totals }));
    return entries;
  }, [metrics]);

  const buildSparkline = (values: number[], width = 240, height = 80) => {
    if (!values.length) return "";
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const span = Math.max(1, max - min);
    return values
      .map((value, index) => {
        const x = (index / Math.max(1, values.length - 1)) * width;
        const y = height - ((value - min) / span) * height;
        return `${x},${y}`;
      })
      .join(" ");
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ingestion Metrics</h1>
          <p className="text-muted-foreground">
            Queue health, failure rate, and daily ingestion totals by source.
          </p>
        </div>
        <button
          className="text-sm text-muted-foreground hover:text-foreground transition"
          onClick={loadMetrics}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-destructive/10 text-destructive text-sm p-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-none shadow-sm">
              <CardContent className="p-4 space-y-2">
                <p className="text-xs uppercase text-muted-foreground">Queue Depth</p>
                <p className="text-3xl font-bold flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  {metrics?.queueDepth ?? 0}
                </p>
                <p className="text-xs text-muted-foreground">Queued ingestion tasks</p>
              </CardContent>
            </Card>
            <Card className="border-none shadow-sm">
              <CardContent className="p-4 space-y-2">
                <p className="text-xs uppercase text-muted-foreground">Failure Rate</p>
                <p className="text-3xl font-bold flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  {(((metrics?.failureRate ?? 0) * 100) || 0).toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground">Last 60 minutes</p>
              </CardContent>
            </Card>
            <Card className="border-none shadow-sm">
              <CardContent className="p-4 space-y-2">
                <p className="text-xs uppercase text-muted-foreground">Jobs Inserted (24h)</p>
                <p className="text-3xl font-bold flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  {metrics?.totals.inserted ?? 0}
                </p>
                <p className="text-xs text-muted-foreground">Across all sources</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="border-none shadow-sm">
              <CardContent className="p-6 space-y-4">
                <h2 className="text-lg font-semibold">Totals (24h)</h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="space-y-1">
                    <p className="text-muted-foreground">Runs</p>
                    <p className="text-xl font-semibold">{metrics?.totals.runs ?? 0}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground">Failed</p>
                    <p className="text-xl font-semibold">{metrics?.totals.failed ?? 0}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground">Skipped</p>
                    <p className="text-xl font-semibold">{metrics?.totals.skipped ?? 0}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-muted-foreground">Duplicates</p>
                    <p className="text-xl font-semibold">{metrics?.totals.duplicates ?? 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-none shadow-sm">
              <CardContent className="p-6 space-y-4">
                <h2 className="text-lg font-semibold">Daily By Source</h2>
                <div className="space-y-3 max-h-80 overflow-auto pr-2">
                  {bySource.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No metrics yet.</p>
                  ) : (
                    bySource.map((row) => (
                      <div
                        key={`${row.metric_date}-${row.source}`}
                        className="flex items-center justify-between text-sm"
                      >
                        <div>
                          <p className="font-medium capitalize">{row.source}</p>
                          <p className="text-xs text-muted-foreground">{row.metric_date}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{row.total_inserted}</p>
                          <p className="text-xs text-muted-foreground">inserted</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="border-none shadow-sm">
              <CardContent className="p-6 space-y-4">
                <h2 className="text-lg font-semibold">Inserted Trend (14d)</h2>
                {dailyTotals.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No trend data yet.</p>
                ) : (
                  <>
                    <svg
                      viewBox="0 0 240 80"
                      className="w-full h-20"
                      role="img"
                      aria-label="Inserted jobs trend"
                    >
                      <polyline
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="text-primary"
                        points={buildSparkline(dailyTotals.map((d) => d.inserted))}
                      />
                    </svg>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{dailyTotals[0].date}</span>
                      <span>{dailyTotals[dailyTotals.length - 1].date}</span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
            <Card className="border-none shadow-sm">
              <CardContent className="p-6 space-y-4">
                <h2 className="text-lg font-semibold">Failed Runs Trend (14d)</h2>
                {dailyTotals.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No trend data yet.</p>
                ) : (
                  <>
                    <svg
                      viewBox="0 0 240 80"
                      className="w-full h-20"
                      role="img"
                      aria-label="Failed runs trend"
                    >
                      <polyline
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="text-destructive"
                        points={buildSparkline(dailyTotals.map((d) => d.failed))}
                      />
                    </svg>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{dailyTotals[0].date}</span>
                      <span>{dailyTotals[dailyTotals.length - 1].date}</span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
};

export default Metrics;
