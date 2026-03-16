import { pool } from "../db";

type DedupeCandidate = {
  id: string;
  company_id: string;
  title: string | null;
  location_norm: string | null;
  apply_url: string | null;
  external_id: string | null;
  source: string | null;
  hash: string | null;
  posted_at: Date | null;
};

export async function findDedupeCandidates(
  companyId: string,
  hash: string,
  applyUrl: string | null,
  externalId: string | null,
  source: string | null,
): Promise<DedupeCandidate[]> {
  const res = await pool.query<DedupeCandidate>(
    `
    select id, company_id, title, location_norm, apply_url, external_id, source, hash, posted_at
    from jobs
    where company_id = $1
      and (
        hash = $2
        or (apply_url is not null and apply_url = $3)
        or (external_id is not null and source is not null and external_id = $4 and source = $5)
      )
    `,
    [companyId, hash, applyUrl, externalId, source],
  );
  return res.rows;
}

export async function linkJobSource(
  jobId: string,
  source: string,
  externalId: string | null,
  rawPayload: unknown,
): Promise<void> {
  await pool.query(
    `
    insert into job_sources (job_id, source, external_id, raw_payload, fetched_at)
    values ($1, $2, $3, $4, now())
    on conflict (job_id, source, external_id) do nothing
    `,
    [jobId, source, externalId, rawPayload],
  );
}
