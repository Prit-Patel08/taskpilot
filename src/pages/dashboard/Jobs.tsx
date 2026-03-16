import { useEffect, useState, useMemo } from "react";
import { Search, MapPin, Briefcase, Loader2, ExternalLink, AlertCircle, ChevronLeft, ChevronRight, ChevronsUpDown, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
import { fetchMetrics, searchJobs, type Job } from "@/lib/jobsDb";

function normalizeCountry(location: string | null): string | null {
  if (!location) return null;
  const s = location.trim();
  if (!s) return null;
  const lower = s.toLowerCase();

  // Common patterns seen in Greenhouse location.name strings
  if (lower.includes("india")) return "India";
  if (lower.includes("united states") || /\bus\b/.test(lower) || lower.includes("u.s.")) return "United States";
  if (lower.includes("united kingdom") || /\buk\b/.test(lower)) return "United Kingdom";
  if (lower.includes("ireland")) return "Ireland";
  if (lower.includes("canada")) return "Canada";
  if (lower.includes("australia")) return "Australia";
  if (lower.includes("singapore")) return "Singapore";
  if (lower.includes("germany")) return "Germany";
  if (lower.includes("france")) return "France";
  if (lower.includes("spain")) return "Spain";
  if (lower.includes("italy")) return "Italy";
  if (lower.includes("japan")) return "Japan";
  if (lower.includes("brazil")) return "Brazil";
  if (lower.includes("mexico")) return "Mexico";
  if (lower.includes("netherlands")) return "Netherlands";
  if (lower.includes("sweden")) return "Sweden";
  if (lower.includes("switzerland")) return "Switzerland";
  if (lower.includes("poland")) return "Poland";
  if (lower.includes("romania")) return "Romania";
  if (lower.includes("portugal")) return "Portugal";
  if (lower.includes("south africa")) return "South Africa";
  if (lower.includes("new zealand")) return "New Zealand";

  // Fallback: last comma-separated segment
  const parts = s.split(",").map((p) => p.trim()).filter(Boolean);
  return parts.length >= 2 ? parts[parts.length - 1] : null;
}

const Jobs = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [queueDepth, setQueueDepth] = useState<number | null>(null);
  const [failureRate, setFailureRate] = useState<number | null>(null);
  const [totals, setTotals] = useState<{
    runs: number;
    inserted: number;
    skipped: number;
    duplicates: number;
    failed: number;
  } | null>(null);
  const [companyFilter, setCompanyFilter] = useState<string>("all");
  const [companyOpen, setCompanyOpen] = useState(false);
  const [roleSearch, setRoleSearch] = useState("");
  const [locationSearch, setLocationSearch] = useState("");
  const [countryFilter, setCountryFilter] = useState<string>("all");
  const [page, setPage] = useState(1);

  const JOBS_PER_PAGE = 20;

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const locationParam =
        locationSearch.trim() ||
        (countryFilter !== "all" ? countryFilter : "");

      const result = await searchJobs({
        query: roleSearch.trim() || undefined,
        company: companyFilter !== "all" ? companyFilter : undefined,
        location: locationParam || undefined,
        page,
        pageSize: JOBS_PER_PAGE,
      });
      setJobs(result.jobs);
      setTotal(result.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    setMetricsLoading(true);
    setMetricsError(null);
    try {
      const data = await fetchMetrics();
      setQueueDepth(data.queueDepth);
      setFailureRate(data.failureRate);
      setTotals(data.totals);
    } catch (e) {
      setMetricsError(e instanceof Error ? e.message : "Failed to load metrics");
    } finally {
      setMetricsLoading(false);
    }
  };

  useEffect(() => {
    if (page !== 1) {
      setPage(1);
      return;
    }
    loadJobs();
    loadMetrics();
  }, [page, companyFilter, countryFilter, roleSearch, locationSearch]);

  const companies = useMemo(() => {
    const set = new Set(jobs.map((j) => j.company).filter(Boolean));
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [jobs]);

  const countries = useMemo(() => {
    const set = new Set<string>();
    for (const j of jobs) {
      const c = normalizeCountry(j.location);
      if (c) set.add(c);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [jobs]);

  const totalPages = Math.max(1, Math.ceil(total / JOBS_PER_PAGE));
  const pageJobs = useMemo(() => {
    return jobs;
  }, [jobs]);

  useEffect(() => {
    if (page !== 1) {
      setPage(1);
    }
  }, [companyFilter, countryFilter, roleSearch, locationSearch, page]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Job Matches</h1>
          <p className="text-muted-foreground">
            Filter by company, role, or location. Results are server-side and paginated.
          </p>
        </div>
        <Button
          className="rounded-full"
          onClick={() => {
            loadJobs();
            loadMetrics();
          }}
          disabled={loading}
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 space-y-2">
            <p className="text-xs uppercase text-muted-foreground">Queue Depth</p>
            <p className="text-2xl font-bold">
              {metricsLoading ? "…" : queueDepth ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">Queued ingestion tasks</p>
          </CardContent>
        </Card>
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 space-y-2">
            <p className="text-xs uppercase text-muted-foreground">Failure Rate</p>
            <p className="text-2xl font-bold">
              {metricsLoading
                ? "…"
                : `${(((failureRate ?? 0) * 100) || 0).toFixed(1)}%`}
            </p>
            <p className="text-xs text-muted-foreground">Last 60 minutes</p>
          </CardContent>
        </Card>
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 space-y-2">
            <p className="text-xs uppercase text-muted-foreground">Runs (24h)</p>
            <p className="text-2xl font-bold">{metricsLoading ? "…" : totals?.runs ?? 0}</p>
            <p className="text-xs text-muted-foreground">Total ingestion runs</p>
          </CardContent>
        </Card>
        <Card className="border-none shadow-sm">
          <CardContent className="p-4 space-y-2">
            <p className="text-xs uppercase text-muted-foreground">Inserted (24h)</p>
            <p className="text-2xl font-bold">{metricsLoading ? "…" : totals?.inserted ?? 0}</p>
            <p className="text-xs text-muted-foreground">New jobs stored</p>
          </CardContent>
        </Card>
      </div>

      {metricsError && (
        <div className="rounded-lg bg-destructive/10 text-destructive text-sm p-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {metricsError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Company</label>
          <Popover open={companyOpen} onOpenChange={setCompanyOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={companyOpen}
                className="w-full justify-between rounded-xl"
              >
                <span className="truncate">
                  {companyFilter === "all" ? "All companies" : companyFilter}
                </span>
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="p-0" align="start">
              <Command>
                <CommandInput placeholder="Search company..." />
                <CommandList>
                  <CommandEmpty>No company found.</CommandEmpty>
                  <CommandGroup>
                    <CommandItem
                      value="all"
                      onSelect={() => {
                        setCompanyFilter("all");
                        setCompanyOpen(false);
                      }}
                    >
                      <Check className={cn("mr-2 h-4 w-4", companyFilter === "all" ? "opacity-100" : "opacity-0")} />
                      All companies
                    </CommandItem>
                    {companies.map((c) => (
                      <CommandItem
                        key={c}
                        value={c}
                        onSelect={() => {
                          setCompanyFilter(c);
                          setCompanyOpen(false);
                        }}
                      >
                        <Check className={cn("mr-2 h-4 w-4", companyFilter === c ? "opacity-100" : "opacity-0")} />
                        {c}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Country</label>
          <Select value={countryFilter} onValueChange={setCountryFilter}>
            <SelectTrigger className="rounded-xl">
              <SelectValue placeholder="All countries" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All countries</SelectItem>
              {countries.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Role or keyword</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="e.g. Engineer, Product"
              className="pl-10 rounded-xl"
              value={roleSearch}
              onChange={(e) => setRoleSearch(e.target.value)}
            />
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">Location</label>
          <div className="relative">
            <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="e.g. Remote, San Francisco"
              className="pl-10 rounded-xl"
              value={locationSearch}
              onChange={(e) => setLocationSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-destructive/10 text-destructive text-sm p-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : jobs.length === 0 ? (
        <Card className="border-none shadow-sm">
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>No jobs yet.</p>
            <p className="text-sm mt-2">
              Call <code className="bg-muted px-1 rounded">GET /api/fetch-jobs?companies=stripe,vercel</code> (or <code className="bg-muted px-1 rounded">?companies=all</code> in batches) to populate.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            Showing {jobs.length} of {total} jobs
            {(companyFilter !== "all" || roleSearch.trim() || locationSearch.trim() || countryFilter !== "all") && " (filtered)"}
            {total > JOBS_PER_PAGE && ` · Page ${page} of ${totalPages}`}
          </p>
          <div className="space-y-4">
            {pageJobs.map((job) => (
              <Card key={job.id} className="border-none shadow-sm hover:shadow-md transition-shadow group overflow-hidden">
                <CardContent className="p-0">
                  <div className="flex flex-col md:flex-row">
                    <div className="w-2 bg-primary" />
                    <div className="flex-grow p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center font-bold text-xl text-muted-foreground">
                          {(job.company ?? "?")[0]?.toUpperCase() ?? "?"}
                        </div>
                        <div>
                          <h3 className="text-lg font-bold mb-1 group-hover:text-primary transition-colors">
                            {job.title ?? "Untitled role"}
                          </h3>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1.5">
                              <Briefcase className="w-3.5 h-3.5" /> {job.company ?? "Unknown company"}
                            </span>
                            {job.location && (
                              <span className="flex items-center gap-1.5">
                                <MapPin className="w-3.5 h-3.5" /> {job.location}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 pl-6 border-l">
                        <Button className="rounded-full px-6 gap-2" asChild disabled={!job.apply_url}>
                          <a href={job.apply_url ?? "#"} target="_blank" rel="noopener noreferrer">
                            Apply <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          {jobs.length === 0 && (
            <p className="text-center text-muted-foreground py-8">No jobs match the current filters.</p>
          )}
          {total > JOBS_PER_PAGE && (
            <div className="flex items-center justify-center gap-4 pt-6">
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Jobs;
