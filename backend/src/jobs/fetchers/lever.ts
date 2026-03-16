import fetch from "node-fetch";
import type { Company, RawJob } from "../types";
import { log } from "../../logger";

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
  const res = await fetch(url, {
    headers: {
      "User-Agent": "JobIngestionBot/1.0 (+https://yourdomain.com)",
    },
  });

  if (!res.ok) {
    log.warn("Lever request failed", {
      companyId: company.id,
      status: res.status,
    });
    return [];
  }

  const data = (await res.json()) as LeverJob[];
  const jobs: RawJob[] = data.map((job) => ({
    companyName: company.name,
    title: job.text.trim(),
    location: job.categories?.location?.trim() ?? "",
    descriptionHtml: job.descriptionPlain ?? "",
    applyUrl: job.hostedUrl,
    postedAt: job.createdAt ? new Date(job.createdAt) : null,
    source: "lever",
    externalId: job.id,
  }));

  log.info("Fetched Lever jobs", {
    companyId: company.id,
    count: jobs.length,
  });

  return jobs;
}
