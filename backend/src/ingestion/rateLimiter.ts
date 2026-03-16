import { setTimeout as sleep } from "node:timers/promises";

type Bucket = {
  nextAllowedAt: number;
  intervalMs: number;
};

const buckets = new Map<string, Bucket>();

export function configureRateLimit(key: string, intervalMs: number) {
  buckets.set(key, { nextAllowedAt: 0, intervalMs });
}

export async function waitForRateLimit(key: string): Promise<void> {
  const bucket = buckets.get(key);
  if (!bucket) return;

  const now = Date.now();
  const waitMs = Math.max(0, bucket.nextAllowedAt - now);
  if (waitMs > 0) {
    await sleep(waitMs);
  }
  bucket.nextAllowedAt = Date.now() + bucket.intervalMs;
}
