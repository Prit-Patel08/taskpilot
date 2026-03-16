import { setTimeout as sleep } from "node:timers/promises";
import { log } from "../logger";

export type FetchRetryOptions = {
  retries?: number;
  backoffMs?: number;
  timeoutMs?: number;
};

function shouldRetry(status: number) {
  return status >= 500 || status === 429;
}

export async function fetchWithRetry(
  url: string,
  init: RequestInit = {},
  options: FetchRetryOptions = {},
): Promise<Response> {
  const retries = options.retries ?? 3;
  const backoffMs = options.backoffMs ?? 500;
  const timeoutMs = options.timeoutMs ?? 20000;

  let attempt = 0;
  while (true) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(url, {
        ...init,
        signal: controller.signal,
      });

      if (res.ok || attempt >= retries || !shouldRetry(res.status)) {
        return res;
      }

      log.warn("HTTP retryable response", {
        url,
        status: res.status,
        attempt,
      });
    } catch (err) {
      if (attempt >= retries) {
        throw err;
      }
      log.warn("HTTP request failed", {
        url,
        attempt,
        error: err instanceof Error ? err.message : String(err),
      });
    } finally {
      clearTimeout(timeout);
    }

    const delay = backoffMs * Math.pow(2, attempt);
    await sleep(delay);
    attempt += 1;
  }
}

export async function fetchJson<T>(
  url: string,
  init: RequestInit = {},
  options: FetchRetryOptions = {},
): Promise<T> {
  const res = await fetchWithRetry(url, init, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  return (await res.json()) as T;
}

export async function fetchText(
  url: string,
  init: RequestInit = {},
  options: FetchRetryOptions = {},
): Promise<string> {
  const res = await fetchWithRetry(url, init, options);
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${url}`);
  }
  return await res.text();
}
