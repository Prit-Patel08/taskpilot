import { pool } from "../db";
import { log } from "../logger";

export async function importSeedDomains(domains: string[]): Promise<number> {
  if (!domains.length) return 0;
  let inserted = 0;
  for (const domain of domains) {
    try {
      await pool.query(
        `
        insert into company_candidates (domain, guessed_careers_url, confidence, discovery_source)
        values ($1, null, 0.1, 'seed')
        on conflict do nothing
        `,
        [domain],
      );
      inserted += 1;
    } catch (err) {
      log.warn("Seed import failed", {
        domain,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return inserted;
}
