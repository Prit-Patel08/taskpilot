/**
 * Vercel serverless API: fetch jobs from Greenhouse and store in Supabase.
 * GET /api/fetch-jobs?companies=stripe,vercel,notion
 *
 * Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 */
import { createClient } from "@supabase/supabase-js";
import { fetchGreenhouseJobs } from "../lib/jobFetcher";

export const config = {
  maxDuration: 60,
};

export default async function handler(
  req: { method?: string; query?: { companies?: string } },
  res: { status: (n: number) => { end: () => void; json: (x: unknown) => void }; setHeader: (a: string, b: string) => void }
) {
  if (req.method !== "GET") {
    res.status(405).end();
    return;
  }

  const url = process.env.SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    res.status(500).json({
      ok: false,
      error: "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
    });
    return;
  }

  const raw = req.query?.companies ?? "stripe,vercel,notion";
  const companies = raw
    .split(",")
    .map((c: string) => c.trim().toLowerCase())
    .filter(Boolean);

  if (companies.length === 0) {
    res.status(400).json({ ok: false, error: "Provide at least one company (e.g. ?companies=stripe)" });
    return;
  }

  const supabase = createClient(url, serviceKey);

  try {
    const result = await fetchGreenhouseJobs(supabase, companies);
    res.status(200).json({
      ok: true,
      companies,
      ...result,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("fetch-jobs error:", message);
    res.status(500).json({ ok: false, error: message });
  }
}
