/**
 * Server-side job search with pagination and filters.
 * GET /api/search-jobs?q=backend&company=stripe&location=remote&remote=remote&page=1&pageSize=20
 *
 * Requires env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 */
import { createClient } from "@supabase/supabase-js";

const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 100;

function toNumber(value: string | undefined, fallback: number) {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function buildLocationTerms(input: string): string[] {
  const normalized = input.trim().toLowerCase();
  if (!normalized) return [];

  const aliasMap: Record<string, string[]> = {
    bengaluru: ["bengaluru", "bangalore"],
    bangalore: ["bangalore", "bengaluru"],
    gurugram: ["gurugram", "gurgaon"],
    gurgaon: ["gurgaon", "gurugram"],
    mumbai: ["mumbai", "bombay"],
    bombay: ["bombay", "mumbai"],
    delhi: ["delhi", "new delhi"],
    "new delhi": ["new delhi", "delhi"],
    hyderabad: ["hyderabad", "hyd"],
    hyd: ["hyd", "hyderabad"],
    sf: ["sf", "san francisco", "bay area"],
    "san francisco": ["san francisco", "sf", "bay area"],
    nyc: ["nyc", "new york", "new york city"],
    "new york": ["new york", "nyc", "new york city"],
    "new york city": ["new york city", "new york", "nyc"],
  };

  const terms = aliasMap[normalized] ?? [normalized];
  return Array.from(new Set(terms));
}

export default async function handler(
  req: {
    method?: string;
    query?: {
      q?: string;
      company?: string;
      location?: string;
      remote?: string;
      page?: string;
      pageSize?: string;
    };
  },
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
    const company = (req.query?.company ?? "").trim();
    const location = (req.query?.location ?? "").trim();
    const remote = (req.query?.remote ?? "").trim().toLowerCase();
    const page = Math.max(1, toNumber(req.query?.page, 1));
    const pageSize = Math.min(MAX_PAGE_SIZE, toNumber(req.query?.pageSize, DEFAULT_PAGE_SIZE));
    const offset = (page - 1) * pageSize;

    const supabase = createClient(url, serviceKey);
    let query = supabase
      .from("jobs")
      .select(
        "id, company, title, location, location_norm, remote_type, posted_at, apply_url, source, seniority, employment_type, rank_score",
        { count: "exact" },
      );

    if (q) {
      query = query.textSearch("search_tsv", q, { type: "websearch" });
    }

    if (company) {
      query = query.ilike("company", `%${company}%`);
    }

    if (location) {
      const terms = buildLocationTerms(location);
      const orParts = terms.flatMap((term) => [
        `location_norm.ilike.%${term}%`,
        `location.ilike.%${term}%`,
        `location_raw.ilike.%${term}%`,
      ]);
      query = query.or(orParts.join(","));
    }

    if (remote === "remote" || remote === "hybrid" || remote === "onsite") {
      query = query.eq("remote_type", remote);
    }

    const { data, error, count } = await query
      .order("rank_score", { ascending: false })
      .order("posted_at", { ascending: false })
      .order("created_at", { ascending: false })
      .range(offset, offset + pageSize - 1);

    if (error) {
      res.status(500).json({ ok: false, error: error.message });
      return;
    }

    res.status(200).json({
      ok: true,
      page,
      pageSize,
      total: count ?? data?.length ?? 0,
      jobs: data ?? [],
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    res.status(500).json({ ok: false, error: message });
  }
}
