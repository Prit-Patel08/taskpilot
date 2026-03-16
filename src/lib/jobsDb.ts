export interface Job {
  id: string;
  source: string | null;
  company: string | null;
  title: string | null;
  location: string | null;
  location_norm: string | null;
  remote_type: string | null;
  posted_at: string | null;
  apply_url: string | null;
  seniority: string | null;
  employment_type: string | null;
  rank_score?: number | null;
}

export interface JobSearchParams {
  query?: string;
  company?: string;
  location?: string;
  remote?: string;
  page?: number;
  pageSize?: number;
}

export interface JobSearchResponse {
  jobs: Job[];
  total: number;
  page: number;
  pageSize: number;
}

export interface IngestionMetricsRow {
  metric_date: string;
  source: string;
  total_runs: number;
  total_inserted: number;
  total_skipped: number;
  total_duplicates: number;
  failed_runs: number;
}

export interface MetricsSummary {
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
}

export async function fetchCompanies(search?: string): Promise<string[]> {
  const qs = new URLSearchParams();
  if (search) qs.set("q", search);
  const res = await fetch(`/api/companies?${qs.toString()}`);
  const body = await res.json();
  if (!res.ok || !body.ok) {
    throw new Error(body?.error ?? "Failed to load companies");
  }
  return (body.companies ?? []) as string[];
}

export async function searchJobs(
  params: JobSearchParams,
): Promise<JobSearchResponse> {
  const qs = new URLSearchParams();
  if (params.query) qs.set("q", params.query);
  if (params.company) qs.set("company", params.company);
  if (params.location) qs.set("location", params.location);
  if (params.remote) qs.set("remote", params.remote);
  if (params.page) qs.set("page", String(params.page));
  if (params.pageSize) qs.set("pageSize", String(params.pageSize));

  const res = await fetch(`/api/search-jobs?${qs.toString()}`);
  const body = await res.json();
  if (!res.ok || !body.ok) {
    throw new Error(body?.error ?? "Search failed");
  }

  return {
    jobs: (body.jobs ?? []) as Job[],
    total: body.total ?? 0,
    page: body.page ?? params.page ?? 1,
    pageSize: body.pageSize ?? params.pageSize ?? 20,
  };
}

export async function fetchMetrics(): Promise<MetricsSummary> {
  const res = await fetch("/api/metrics");
  const body = await res.json();
  if (!res.ok || !body.ok) {
    throw new Error(body?.error ?? "Failed to load metrics");
  }
  return body.metrics as MetricsSummary;
}
