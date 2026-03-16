import { pool } from "../db";
import type { NormalizedJob } from "./types";
import { config } from "../config";

export async function upsertJobs(
  jobs: NormalizedJob[],
): Promise<{ inserted: number; skipped: number }> {
  if (!jobs.length) return { inserted: 0, skipped: 0 };

  const { maxJobsPerCompany } = config.ingestion;
  const limitedJobs = jobs.slice(0, maxJobsPerCompany);

  const values: unknown[] = [];
  const rows: string[] = [];

  limitedJobs.forEach((job, idx) => {
    const base = idx * 9;
    rows.push(
      `($${base + 1}, $${base + 2}, $${base + 3}, $${base + 4}, $${base + 5}, $${base + 6}, $${base + 7}, $${base + 8}, $${base + 9})`,
    );
    values.push(
      job.companyId,
      job.companyName,
      job.title,
      job.location,
      job.descriptionHtml,
      job.applyUrl,
      job.postedAt ? job.postedAt.toISOString() : null,
      job.source,
      job.hash,
    );
  });

  const query = `
    insert into jobs (
      company_id,
      company,
      title,
      location,
      description,
      apply_url,
      posted_at,
      source,
      hash
    ) values
      ${rows.join(",")}
    on conflict (hash) do nothing
    returning id
  `;

  const res = await pool.query<{ id: string }>(query, values);
  const inserted = res.rowCount ?? 0;
  const skipped = limitedJobs.length - inserted;

  return { inserted, skipped };
}
