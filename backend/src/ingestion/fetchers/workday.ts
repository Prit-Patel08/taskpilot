import type { Company, RawJob } from "../types";
import { log } from "../../logger";
import { fetchJson } from "../httpClient";

type WorkdayJob = {
  title?: string;
  locationsText?: string;
  externalPath?: string;
  postedOn?: string;
  jobRequisitionId?: string;
  bulletFields?: Array<{ id?: string; label?: string; content?: string }>;
};

type WorkdayResponse = {
  jobPostings?: WorkdayJob[];
  total?: number;
};

const DEFAULT_PAGE_SIZE = 50;
const MAX_JOBS = 2000;

function buildWorkdayBaseUrl(company: Company): string | null {
  if (company.career_url) return company.career_url;
  if (company.ats_slug?.startsWith("http")) return company.ats_slug;
  return null;
}

export async function fetchWorkdayJobs(company: Company): Promise<RawJob[]> {
  const baseUrl = buildWorkdayBaseUrl(company);
  if (!baseUrl) {
    log.warn("Workday base URL missing", { companyId: company.id });
    return [];
  }

  const base = baseUrl.replace(/\/$/, "");
  const origin = (() => {
    try {
      return new URL(base).origin;
    } catch {
      return "";
    }
  })();

  const jobs: RawJob[] = [];
  let offset = 0;

  while (jobs.length < MAX_JOBS) {
    const url = `${base}?offset=${offset}&limit=${DEFAULT_PAGE_SIZE}`;
    let data: WorkdayResponse;
    try {
      data = await fetchJson<WorkdayResponse>(url, {
        headers: {
          "User-Agent": "TaskPilotBot/1.0 (+https://yourdomain.com)",
        },
      });
    } catch (err) {
      log.warn("Workday request failed", {
        companyId: company.id,
        error: err instanceof Error ? err.message : String(err),
      });
      break;
    }

    const postings = data.jobPostings ?? [];
    if (!postings.length) break;

    for (const posting of postings) {
      const title = (posting.title ?? "").trim();
      const location = (posting.locationsText ?? "").trim();
      const externalId = posting.jobRequisitionId ?? posting.externalPath;

      let applyUrl = posting.externalPath ?? "";
      if (applyUrl && !applyUrl.startsWith("http") && origin) {
        applyUrl = `${origin}${applyUrl}`;
      }

      if (!title || !applyUrl) continue;

      jobs.push({
        companyName: company.name,
        title,
        location,
        descriptionHtml: posting.bulletFields
          ?.map((field) => field.content ?? "")
          .filter(Boolean)
          .join("\n\n") ?? "",
        applyUrl,
        postedAt: posting.postedOn ? new Date(posting.postedOn) : null,
        source: "workday",
        externalId: externalId ?? undefined,
        rawPayload: posting,
      });
    }

    offset += postings.length;
    if (postings.length < DEFAULT_PAGE_SIZE) break;
  }

  log.info("Fetched Workday jobs", {
    companyId: company.id,
    count: jobs.length,
  });

  return jobs;
}
