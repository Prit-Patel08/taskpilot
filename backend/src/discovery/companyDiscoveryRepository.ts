import { pool } from "../db";
import type { CompanyCandidate } from "./types";

export async function upsertCompanyCandidate(
  candidate: CompanyCandidate,
): Promise<void> {
  await pool.query(
    `
    insert into company_candidates (
      domain,
      guessed_careers_url,
      ats_type,
      ats_slug,
      confidence,
      discovery_source
    ) values ($1, $2, $3, $4, $5, $6)
    on conflict (domain, guessed_careers_url)
    do update set
      ats_type = excluded.ats_type,
      ats_slug = excluded.ats_slug,
      confidence = greatest(company_candidates.confidence, excluded.confidence),
      discovery_source = excluded.discovery_source,
      updated_at = now()
    `,
    [
      candidate.domain,
      candidate.guessed_careers_url,
      candidate.ats_type,
      candidate.ats_slug,
      candidate.confidence,
      candidate.discovery_source,
    ],
  );
}

export async function promoteCandidateToSource(
  candidateId: string,
  status: "active" | "pending" = "active",
): Promise<void> {
  await pool.query(
    `
    insert into company_sources (
      company_id,
      ats_type,
      ats_slug,
      career_url,
      confidence,
      status
    )
    select
      c.id,
      cc.ats_type,
      cc.ats_slug,
      cc.guessed_careers_url,
      cc.confidence,
      $2
    from company_candidates cc
    join companies c on c.name = cc.domain or c.career_url = cc.guessed_careers_url
    where cc.id = $1
    on conflict do nothing
    `,
    [candidateId, status],
  );
}

export async function autoPromoteTopCandidates(
  minConfidence = 0.75,
  limit = 200,
): Promise<number> {
  const res = await pool.query<{ id: string }>(
    `
    select id
    from company_candidates
    where confidence >= $1
    order by confidence desc
    limit $2
    `,
    [minConfidence, limit],
  );

  let promoted = 0;
  for (const row of res.rows) {
    await promoteCandidateToSource(row.id, "pending");
    promoted += 1;
  }

  return promoted;
}
