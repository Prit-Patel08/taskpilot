import fetch from "node-fetch";
import type { Company, RawJob } from "../types";
import { log } from "../../logger";

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

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "JobIngestionBot/1.0 (+https://yourdomain.com)",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    log.warn("Ashby request failed", {
      companyId: company.id,
      status: res.status,
    });
    return [];
  }

  const json = await res.json();
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
  }));

  log.info("Fetched Ashby jobs", {
    companyId: company.id,
    count: jobs.length,
  });

  return jobs;
}
