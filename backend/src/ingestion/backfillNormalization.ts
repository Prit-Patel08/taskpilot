import { pathToFileURL } from "url";
import { pool } from "../db";
import { log } from "../logger";
import { normalizeJobFields } from "./normalization";
import { buildJobHash } from "./jobNormalizer";

type JobRow = {
  id: string;
  company: string | null;
  title: string | null;
  location: string | null;
  description: string | null;
};

async function backfillBatch(limit: number): Promise<number> {
  const res = await pool.query<JobRow>(
    `
    select id, company, title, location, description
    from jobs
    where location_norm is null
       or remote_type is null
       or seniority is null
       or employment_type is null
       or hash is null
    order by created_at asc
    limit $1
    `,
    [limit],
  );

  if (!res.rows.length) return 0;

  const updates: Array<Promise<void>> = res.rows.map(async (row) => {
    const title = row.title ?? "";
    const location = row.location ?? "";
    const description = row.description ?? "";
    const companyName = row.company ?? "";
    const fields = normalizeJobFields(title, location, description);
    const hash = buildJobHash(
      companyName,
      title,
      fields.locationNormalized || fields.locationRaw,
    );

    await pool.query(
      `
      update jobs
      set location_raw = $2,
          location_norm = $3,
          remote_type = $4,
          seniority = $5,
          employment_type = $6,
          hash = $7
      where id = $1
      `,
      [
        row.id,
        fields.locationRaw,
        fields.locationNormalized,
        fields.remoteType,
        fields.seniority,
        fields.employmentType,
        hash,
      ],
    );
  });

  await Promise.all(updates);
  return res.rows.length;
}

export async function backfillJobNormalization(batchSize = 500): Promise<void> {
  let total = 0;
  while (true) {
    const updated = await backfillBatch(batchSize);
    if (!updated) break;
    total += updated;
    log.info("Backfilled job normalization batch", { updated, total });
  }
  log.info("Backfill complete", { total });
}

const isMain = import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  backfillJobNormalization().catch((err) => {
    log.error("Backfill failed", { error: (err as Error).message });
    process.exit(1);
  });
}
