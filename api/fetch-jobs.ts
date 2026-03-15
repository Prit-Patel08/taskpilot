/**
 * Vercel serverless API: fetch jobs from Greenhouse and store in Supabase.
 * GET /api/fetch-jobs?companies=stripe,vercel,notion
 * GET /api/fetch-jobs?companies=all  (batched; use offset to get more)
 * GET /api/fetch-jobs?companies=all&offset=20
 *
 * Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 */
import { createClient } from "@supabase/supabase-js";

const GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards";

/** Max boards per request when using companies=all (avoids 60s timeout) */
const BATCH_SIZE = 15;

const BOARD_SLUGS = [
  "stripe", "vercel", "notion", "cloudflare", "figma", "linear", "supabase", "retool",
  "plausible", "sourcegraph", "mixpanel", "segment", "twilio", "discord", "robinhood",
  "brex", "plaid", "doordash", "instacart", "airbnb", "dropbox", "box", "asana",
  "monday", "atlassian", "gitlab", "hashicorp", "datadog", "newrelic", "elastic",
  "mongodb", "snowflake", "databricks", "confluent", "grafana", "launchdarkly",
  "pagerduty", "rippling", "deel", "canva", "webflow", "netlify", "railway",
  "render", "fly", "digitalocean", "fastly", "postman", "circleci", "sentry",
  "amplitude", "intercom", "zendesk", "hubspot", "salesforce", "shopify", "square",
  "okta", "auth0", "crowdstrike", "cloudflare", "vimeo", "spotify", "github",
  "bitbucket", "microsoft", "google", "meta", "apple", "amazon", "netflix",
  "uber", "lyft", "reddit", "pinterest", "snap", "twitter", "linkedin",
  "greenhouse", "lever",
];

export const config = { maxDuration: 60 };

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function fetchGreenhouseJobs(supabase: any, companies: string[]) {
  const errors: string[] = [];
  let inserted = 0;

  for (const slug of companies) {
    const url = `${GREENHOUSE_BASE}/${encodeURIComponent(slug)}/jobs`;
    let jobs: { id: number; title?: string; company_name?: string; location?: { name?: string }; absolute_url?: string }[];

    try {
      const res = await fetch(url);
      if (!res.ok) {
        errors.push(`${slug}: ${res.status}`);
        continue;
      }
      const data = await res.json();
      jobs = data.jobs ?? [];
    } catch (e) {
      errors.push(`${slug}: ${e instanceof Error ? e.message : String(e)}`);
      continue;
    }

    for (const job of jobs) {
      const row = {
        external_id: String(job.id),
        source: "greenhouse",
        company: job.company_name ?? slug,
        title: job.title ?? "",
        location: job.location?.name ?? null,
        description: null,
        apply_url: job.absolute_url ?? "",
      };
      if (!row.apply_url || !row.title) continue;

      const { error } = await supabase.from("jobs").upsert(row, {
        onConflict: "external_id,source",
        ignoreDuplicates: false,
      });
      if (error) {
        errors.push(`${slug} ${row.external_id}: ${error.message}`);
        continue;
      }
      inserted += 1;
    }
  }

  return { inserted, errors };
}

export default async function handler(
  req: { method?: string; query?: { companies?: string; offset?: string } },
  res: { status: (n: number) => { end: () => void; json: (x: unknown) => void } }
) {
  try {
    if (req.method !== "GET") {
      res.status(405).end();
      return;
    }

    const url = process.env.SUPABASE_URL;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
    if (!url || !serviceKey) {
      res.status(500).json({ ok: false, error: "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY" });
      return;
    }

    const raw = (req.query?.companies ?? "stripe,vercel,notion").trim().toLowerCase();
    const offset = Math.max(0, parseInt(req.query?.offset ?? "0", 10) || 0);

    let companies: string[];
    if (raw === "all") {
      companies = BOARD_SLUGS.slice(offset, offset + BATCH_SIZE);
    } else {
      companies = raw.split(",").map((c: string) => c.trim().toLowerCase()).filter(Boolean);
    }

    if (companies.length === 0) {
      res.status(400).json({
        ok: false,
        error: "Provide companies (e.g. ?companies=stripe,vercel or ?companies=all) or use &offset= for next batch",
      });
      return;
    }

    const supabase = createClient(url, serviceKey);
    const result = await fetchGreenhouseJobs(supabase, companies);

    const nextOffset = raw === "all" ? offset + companies.length : undefined;
    const hasMore = raw === "all" && nextOffset !== undefined && nextOffset < BOARD_SLUGS.length;

    res.status(200).json({
      ok: true,
      companies: companies.length,
      ...result,
      ...(raw === "all" && {
        totalBoards: BOARD_SLUGS.length,
        offset,
        nextOffset: hasMore ? nextOffset : undefined,
        nextUrl: hasMore && nextOffset !== undefined ? `/api/fetch-jobs?companies=all&offset=${nextOffset}` : undefined,
      }),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("fetch-jobs:", message);
    res.status(500).json({ ok: false, error: message });
  }
}
