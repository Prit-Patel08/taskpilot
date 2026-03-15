/**
 * Fetches jobs from Greenhouse boards API and upserts them into Supabase.
 * Used by the Vercel serverless API (api/fetch-jobs.ts).
 * Run in Node (Vercel), not in the browser.
 */
import type { SupabaseClient } from "@supabase/supabase-js";

const GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards";

/** Curated list of Greenhouse job board slugs. Use with ?companies=all to fetch from all. */
export const GREENHOUSE_BOARD_SLUGS: string[] = [
  "stripe",
  "vercel",
  "notion",
  "cloudflare",
  "figma",
  "linear",
  "supabase",
  "retool",
  "plausible",
  "sourcegraph",
  "mixpanel",
  "segment",
  "twilio",
  "discord",
  "robinhood",
  "brex",
  "plaid",
  "affirm",
  "chime",
  "doordash",
  "instacart",
  "grubhub",
  "airbnb",
  "dropbox",
  "box",
  "asana",
  "monday",
  "smartsheet",
  "atlassian",
  "gitlab",
  "hashicorp",
  "datadog",
  "newrelic",
  "splunk",
  "elastic",
  "mongodb",
  "cockroachlabs",
  "snowflake",
  "databricks",
  "confluent",
  "grafana",
  "launchdarkly",
  "pagerduty",
  "lattice",
  "rippling",
  "deel",
  "remote",
  "luma",
  "cal",
  "loom",
  "canva",
  "webflow",
  "netlify",
  "railway",
  "render",
  "fly",
  "digitalocean",
  "fastly",
  "kong",
  "postman",
  "circleci",
  "buildkite",
  "codecov",
  "sentry",
  "bugsnag",
  "split",
  "optimizely",
  "amplitude",
  "heap",
  "fullstory",
  "hotjar",
  "intercom",
  "zendesk",
  "freshdesk",
  "hubspot",
  "salesforce",
  "shopify",
  "square",
  "adobe",
  "okta",
  "auth0",
  "onelogin",
  "duo",
  "crowdstrike",
  "paloaltonetworks",
  "zscaler",
  "akamai",
  "vimeo",
  "spotify",
  "soundcloud",
  "bandcamp",
  "patreon",
  "substack",
  "medium",
  "github",
  "bitbucket",
  "microsoft",
  "google",
  "meta",
  "apple",
  "amazon",
  "netflix",
  "uber",
  "lyft",
  "tesla",
  "rivian",
  "waymo",
  "cruise",
  "nuro",
  "getaround",
  "turo",
  "reddit",
  "pinterest",
  "snap",
  "twitter",
  "linkedin",
  "greenhouse",
  "lever",
];

interface GreenhouseJob {
  id: number;
  title: string;
  company_name?: string;
  location?: { name?: string };
  absolute_url: string;
}

interface GreenhouseResponse {
  jobs?: GreenhouseJob[];
}

export interface JobRow {
  external_id: string;
  source: string;
  company: string;
  title: string;
  location: string | null;
  description: string | null;
  apply_url: string;
}

function parseGreenhouseJob(job: GreenhouseJob, companySlug: string): JobRow {
  const company = job.company_name ?? companySlug;
  const location = job.location?.name ?? null;
  return {
    external_id: String(job.id),
    source: "greenhouse",
    company,
    title: job.title ?? "",
    location,
    description: null,
    apply_url: job.absolute_url ?? "",
  };
}

/**
 * Fetch jobs from Greenhouse for the given board slugs and upsert into Supabase.
 * Prevents duplicates by (external_id, source). On conflict, updates the row.
 */
export async function fetchGreenhouseJobs(
  supabase: SupabaseClient,
  companies: string[]
): Promise<{ inserted: number; updated: number; errors: string[] }> {
  const errors: string[] = [];
  let inserted = 0;
  let updated = 0;

  for (const companySlug of companies) {
    const url = `${GREENHOUSE_BASE}/${encodeURIComponent(companySlug)}/jobs`;
    let jobs: GreenhouseJob[];

    try {
      const res = await fetch(url);
      if (!res.ok) {
        errors.push(`${companySlug}: HTTP ${res.status}`);
        continue;
      }
      const data = (await res.json()) as GreenhouseResponse;
      jobs = data.jobs ?? [];
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      errors.push(`${companySlug}: ${msg}`);
      continue;
    }

    for (const job of jobs) {
      const row = parseGreenhouseJob(job, companySlug);
      if (!row.apply_url || !row.title) continue;

      const { error } = await supabase.from("jobs").upsert(row, {
        onConflict: "external_id,source",
        ignoreDuplicates: false,
      });

      if (error) {
        errors.push(`${companySlug} job ${row.external_id}: ${error.message}`);
        continue;
      }
      // upsert doesn't tell us insert vs update; count as inserted for simplicity
      inserted += 1;
    }
  }

  return { inserted, updated, errors };
}
