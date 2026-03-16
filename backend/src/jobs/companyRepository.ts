import { pool } from "../db";
import type { Company } from "./types";
import { config } from "../config";

export async function getCompaniesPage(offset: number): Promise<Company[]> {
  const { companyPageSize } = config.ingestion;
  const res = await pool.query<Company>(
    `
    select id, name, ats_type, ats_slug, career_url, last_crawled
    from companies
    order by coalesce(last_crawled, to_timestamp(0)) asc
    limit $1 offset $2
    `,
    [companyPageSize, offset],
  );
  return res.rows;
}

export async function updateCompanyLastCrawled(
  id: string,
  date = new Date(),
): Promise<void> {
  await pool.query("update companies set last_crawled = $1 where id = $2", [
    date.toISOString(),
    id,
  ]);
}
