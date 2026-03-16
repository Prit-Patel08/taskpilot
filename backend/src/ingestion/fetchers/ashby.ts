import type { Company, RawJob } from "../types";
import { log } from "../../logger";
import { fetchJson } from "../httpClient";

interface AshbyJob {
  id: string;
  title: string;
  location: string;
  jobUrl: string;
  createdAt: string;
  descriptionHtml: string;
}

export async function fetchAshbyJobs(company: Company): Promise<RawJob[]> {
  if (!company.ats_slug && !company.career_url) return [];

  const url = "https://jobs.ashbyhq.com/api/non-user-graphql";
  const body = {
    operationName: "JobBoard",
    variables: {
      organizationHostedJobsPageName: company.ats_slug ?? company.career_url,
    },
    query: `
      query JobBoard($organizationHostedJobsPageName: String!) {
        jobBoard: jobBoardWithHostedJobsPage(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
          jobs {
            id
            title
            location
            jobUrl
            createdAt
            descriptionHtml
          }
        }
      }
    `,
  };

  let json: { data?: { jobBoard?: { jobs?: AshbyJob[] } } } = {};
  try {
    json = await fetchJson(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "TaskPilotBot/1.0 (+https://yourdomain.com)",
      },
      body: JSON.stringify(body),
    });
  } catch (err) {
    log.warn("Ashby request failed", {
      companyId: company.id,
      error: err instanceof Error ? err.message : String(err),
    });
    return [];
  }
  const jobsData: AshbyJob[] = json?.data?.jobBoard?.jobs ?? [];
  const jobs: RawJob[] = jobsData.map((job) => ({
    companyName: company.name,
    title: job.title.trim(),
    location: job.location.trim(),
    descriptionHtml: job.descriptionHtml,
    applyUrl: job.jobUrl,
    postedAt: job.createdAt ? new Date(job.createdAt) : null,
    source: "ashby",
    externalId: job.id,
    rawPayload: job,
  }));

  log.info("Fetched Ashby jobs", {
    companyId: company.id,
    count: jobs.length,
  });

  return jobs;
}
