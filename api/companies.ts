/**
 * Server-side companies list for filters.
 * GET /api/companies?q=ver&limit=200
 *
 * Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 */
import { createClient } from "@supabase/supabase-js";

export default async function handler(
  req: { method?: string; query?: { q?: string; limit?: string } },
  res: { status: (n: number) => { end: () => void; json: (x: unknown) => void } },
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

    const q = (req.query?.q ?? "").trim();
    const limit = Math.min(1000, Math.max(1, parseInt(req.query?.limit ?? "500", 10)));

    const supabase = createClient(url, serviceKey);
    const { data, error } = await supabase.rpc("distinct_companies", {
      search: q || null,
      limit_count: limit,
    });

    if (error) {
      res.status(500).json({ ok: false, error: error.message });
      return;
    }

    res.status(200).json({ ok: true, companies: data?.map((row: { company: string }) => row.company) ?? [] });
  } catch (err) {
    res.status(500).json({ ok: false, error: err instanceof Error ? err.message : String(err) });
  }
}
