import { pool } from "../db";

export async function listCandidates(status = "new", limit = 100) {
  const res = await pool.query(
    `
    select id, domain, guessed_careers_url, ats_type, ats_slug, confidence, discovery_source, status, created_at
    from company_candidates
    where status = $1
    order by confidence desc
    limit $2
    `,
    [status, limit],
  );
  return res.rows;
}

export async function updateCandidateStatus(
  id: string,
  status: "new" | "approved" | "rejected",
): Promise<void> {
  await pool.query("update company_candidates set status = $1 where id = $2", [
    status,
    id,
  ]);
}

export async function promoteCandidateById(id: string): Promise<void> {
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
      'active'
    from company_candidates cc
    join companies c on c.name = cc.domain or c.career_url = cc.guessed_careers_url
    where cc.id = $1
    on conflict do nothing
    `,
    [id],
  );
  await updateCandidateStatus(id, "approved");
}
