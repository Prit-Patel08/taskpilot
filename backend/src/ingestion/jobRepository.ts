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
    const base = idx * 15;
    rows.push(
      `($${base + 1}, $${base + 2}, $${base + 3}, $${base + 4}, $${base + 5}, $${base + 6}, $${base + 7}, $${base + 8}, $${base + 9}, $${base + 10}, $${base + 11}, $${base + 12}, $${base + 13}, $${base + 14}, $${base + 15})`,
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
      job.externalId ?? null,
      job.hash,
      job.locationRaw,
      job.locationNormalized,
      job.remoteType,
      job.seniority,
      job.employmentType,
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
      external_id,
      hash,
      location_raw,
      location_norm,
      remote_type,
      seniority,
      employment_type
    ) values
      ${rows.join(",")}
    on conflict (hash) do update
    set last_seen = now(),
        posted_at = coalesce(jobs.posted_at, excluded.posted_at),
        apply_url = coalesce(jobs.apply_url, excluded.apply_url),
        external_id = coalesce(jobs.external_id, excluded.external_id),
        source = coalesce(jobs.source, excluded.source),
        location_norm = coalesce(jobs.location_norm, excluded.location_norm),
        remote_type = coalesce(jobs.remote_type, excluded.remote_type),
        seniority = coalesce(jobs.seniority, excluded.seniority),
        employment_type = coalesce(jobs.employment_type, excluded.employment_type)
    returning (xmax = 0) as inserted
  `;

  const res = await pool.query<{ inserted: boolean }>(query, values);
  const inserted = res.rows.filter((row) => row.inserted).length;
  const skipped = limitedJobs.length - inserted;

  return { inserted, skipped };
}
