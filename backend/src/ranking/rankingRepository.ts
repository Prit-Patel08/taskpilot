import { pool } from "../db";

export async function getCompanyScore(companyId: string): Promise<number> {
  const res = await pool.query<{ reputation_score: number }>(
    `
    select reputation_score
    from companies
    where id = $1
    `,
    [companyId],
  );
  return res.rows[0]?.reputation_score ?? 0.5;
}

export async function updateJobRank(jobId: string, score: number): Promise<void> {
  await pool.query(
    `
    update jobs
    set rank_score = $2
    where id = $1
    `,
    [jobId, score],
  );
}

export async function updateJobRanksBatch(
  updates: Array<{ jobId: string; score: number }>,
): Promise<void> {
  if (!updates.length) return;
  const values: unknown[] = [];
  const rows: string[] = [];

  updates.forEach((update, idx) => {
    const base = idx * 2;
    rows.push(`($${base + 1}, $${base + 2})`);
    values.push(update.jobId, update.score);
  });

  await pool.query(
    `
    update jobs as j
    set rank_score = v.score
    from (values ${rows.join(",")}) as v(id, score)
    where j.id = v.id
    `,
    values,
  );
}
