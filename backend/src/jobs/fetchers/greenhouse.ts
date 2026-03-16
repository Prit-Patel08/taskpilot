import fetch from "node-fetch";
import type { Company, RawJob } from "../types";
import { log } from "../../logger";

export async function fetchGreenhouseJobs(company: Company): Promise<RawJob[]> {
  if (!company.ats_slug) return [];

  const url = `https://boards.greenhouse.io/embed/job_board?for=${encodeURIComponent(
    company.ats_slug,
  )}`;
  const res = await fetch(url, {
    headers: {
      "User-Agent": "JobIngestionBot/1.0 (+https://yourdomain.com)",
    },
  });

  if (!res.ok) {
    log.warn("Greenhouse request failed", {
      companyId: company.id,
      status: res.status,
    });
    return [];
  }

  const html = await res.text();
  const jobs: RawJob[] = [];
  const jobRegex =
    /<div[^>]*class="opening"[^>]*data\-gh\-job\-id="(?<id>\d+)"[^>]*>[\s\S]*?<a[^>]*href="(?<url>[^"]+)"[^>]*>(?<title>[^<]+)<\/a>[\s\S]*?<span[^>]*class="location"[^>]*>(?<location>[^<]*)<\/span>/gi;

  let match: RegExpExecArray | null;
  while ((match = jobRegex.exec(html)) !== null) {
    const groups = match.groups ?? {};
    const title = (groups.title ?? "").trim();
    const location = (groups.location ?? "").trim();
    const applyUrl = `https://boards.greenhouse.io${groups.url ?? ""}`;
    const externalId = groups.id;

    if (!title || !applyUrl) continue;

    jobs.push({
      companyName: company.name,
      title,
      location,
      descriptionHtml: "",
      applyUrl,
      postedAt: null,
      source: "greenhouse",
      externalId,
    });
  }

  log.info("Fetched Greenhouse jobs", {
    companyId: company.id,
    count: jobs.length,
  });

  return jobs;
}
