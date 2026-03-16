import { pathToFileURL } from "url";
import { pool } from "../db";
import { log } from "../logger";
import { rankJob } from "./jobRanker";
import { getCompanyScore, updateJobRanksBatch } from "./rankingRepository";

type JobRow = {
  id: string;
  company_id: string | null;
  posted_at: Date | null;
  location_norm: string | null;
  remote_type: string | null;
  title: string | null;
  description: string | null;
};

type RankContext = {
  preferredLocation?: string;
  remotePreference?: "remote" | "hybrid" | "onsite";
  skillKeywords?: string[];
};

function locationMatchScore(
  preferredLocation: string | undefined,
  locationNorm: string | null,
): number {
  if (!preferredLocation) return 0.5;
  if (!locationNorm) return 0.1;
  const pref = preferredLocation.toLowerCase();
  const loc = locationNorm.toLowerCase();
  if (loc.includes(pref)) return 1;
  return 0.2;
}

function remoteMatchScore(
  preference: RankContext["remotePreference"],
  remoteType: string | null,
): number {
  if (!preference) return 0.5;
  if (!remoteType) return 0.2;
  return remoteType === preference ? 1 : 0.1;
}

function skillMatchScore(skills: string[] | undefined, text: string): number {
  if (!skills || skills.length === 0) return 0.5;
  const lower = text.toLowerCase();
  let matches = 0;
  for (const skill of skills) {
    if (lower.includes(skill.toLowerCase())) {
      matches += 1;
    }
  }
  return Math.min(1, matches / skills.length);
}

export async function rankRecentJobs(
  context: RankContext = {},
  limit = 5000,
): Promise<number> {
  const res = await pool.query<JobRow>(
    `
    select id, company_id, posted_at, location_norm, remote_type, title, description
    from jobs
    order by posted_at desc nulls last
    limit $1
    `,
    [limit],
  );

  if (!res.rows.length) return 0;

  const companyScoreCache = new Map<string, number>();
  const updates: Array<{ jobId: string; score: number }> = [];

  for (const row of res.rows) {
    let companyScore = 0.5;
    if (row.company_id) {
      if (!companyScoreCache.has(row.company_id)) {
        const score = await getCompanyScore(row.company_id);
        companyScoreCache.set(row.company_id, score);
      }
      companyScore = companyScoreCache.get(row.company_id) ?? 0.5;
    }

    const text = `${row.title ?? ""} ${row.description ?? ""}`;
    const score = rankJob({
      postedAt: row.posted_at,
      companyScore,
      locationMatch: locationMatchScore(context.preferredLocation, row.location_norm),
      remoteMatch: remoteMatchScore(context.remotePreference, row.remote_type),
      skillMatch: skillMatchScore(context.skillKeywords, text),
    });

    updates.push({ jobId: row.id, score });
  }

  await updateJobRanksBatch(updates);
  return updates.length;
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  rankRecentJobs()
    .then((count) => {
      log.info("Ranked jobs", { count });
    })
    .catch((err) => {
      log.error("Ranking failed", { error: (err as Error).message });
      process.exit(1);
    });
}
