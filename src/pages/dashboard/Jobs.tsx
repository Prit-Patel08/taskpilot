import { useEffect, useState } from "react";
import { Search, Filter, MapPin, Briefcase, Loader2, ExternalLink, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getJobs, type Job } from "@/lib/jobsDb";

const Jobs = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJobs();
      setJobs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Job Matches</h1>
          <p className="text-muted-foreground">
            Roles from Greenhouse. Fetch more via <code className="text-xs bg-muted px-1 rounded">/api/fetch-jobs</code>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2 rounded-full">
            <Filter className="w-4 h-4" /> Filters
          </Button>
          <Button className="rounded-full" onClick={loadJobs} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Role or keyword" className="pl-10 rounded-xl" />
        </div>
        <div className="relative">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Location" className="pl-10 rounded-xl" />
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
              Deploy the app and call <code className="bg-muted px-1 rounded">GET /api/fetch-jobs?companies=stripe,vercel</code> to populate.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => (
            <Card key={job.id} className="border-none shadow-sm hover:shadow-md transition-shadow group overflow-hidden">
              <CardContent className="p-0">
                <div className="flex flex-col md:flex-row">
                  <div className="w-2 bg-primary" />
                  <div className="flex-grow p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center font-bold text-xl text-muted-foreground">
                        {job.company[0]?.toUpperCase() ?? "?"}
                      </div>
                      <div>
                        <h3 className="text-lg font-bold mb-1 group-hover:text-primary transition-colors">
                          {job.title}
                        </h3>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1.5">
                            <Briefcase className="w-3.5 h-3.5" /> {job.company}
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
                      <Button
                        className="rounded-full px-6 gap-2"
                        asChild
                      >
                        <a href={job.apply_url} target="_blank" rel="noopener noreferrer">
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
      )}
    </div>
  );
};

export default Jobs;
