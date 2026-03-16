import { Pool, type PoolClient } from "pg";
import { config } from "./config";

if (!config.db.connectionString) {
  throw new Error("DATABASE_URL is required");
}

export const pool = new Pool({
  connectionString: config.db.connectionString,
  max: 20,
});

export async function withClient<T>(
  fn: (client: PoolClient) => Promise<T>,
): Promise<T> {
  const client = await pool.connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}
