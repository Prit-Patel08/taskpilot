import type { Company, RawJob } from "../types";
import { log } from "../../logger";
import { fetchJson } from "../httpClient";

interface LeverJob {
  id: string;
  text: string;
  hostedUrl: string;
  createdAt: number;
  categories?: {
    location?: string;
  };
  descriptionPlain?: string;
}

export async function fetchLeverJobs(company: Company): Promise<RawJob[]> {
  if (!company.ats_slug) return [];

  const url = `https://api.lever.co/v0/postings/${encodeURIComponent(
    company.ats_slug,
  )}?mode=json`;
  let data: LeverJob[] = [];
  try {
    data = await fetchJson<LeverJob[]>(url, {
      headers: {
        "User-Agent": "TaskPilotBot/1.0 (+https://yourdomain.com)",
      },
    });
  } catch (err) {
    log.warn("Lever request failed", {
      companyId: company.id,
      error: err instanceof Error ? err.message : String(err),
    });
    return [];
  }
  const jobs: RawJob[] = data.map((job) => ({
    companyName: company.name,
    title: job.text.trim(),
    location: job.categories?.location?.trim() ?? "",
    descriptionHtml: job.descriptionPlain ?? "",
    applyUrl: job.hostedUrl,
    postedAt: job.createdAt ? new Date(job.createdAt) : null,
    source: "lever",
    externalId: job.id,
    rawPayload: job,
  }));

  log.info("Fetched Lever jobs", {
    companyId: company.id,
    count: jobs.length,
  });

  return jobs;
}
