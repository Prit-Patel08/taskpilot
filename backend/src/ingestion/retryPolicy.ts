export type RetryPolicy = {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
};

export const defaultRetryPolicy: RetryPolicy = {
  maxAttempts: 5,
  baseDelayMs: 1000,
  maxDelayMs: 300000,
};

export function nextRetryDelay(
  attempt: number,
  policy: RetryPolicy = defaultRetryPolicy,
): number {
  const delay = policy.baseDelayMs * Math.pow(2, Math.max(0, attempt - 1));
  return Math.min(delay, policy.maxDelayMs);
}
