import type { NormalizedJob } from "./types";

export function dedupeJobs(jobs: NormalizedJob[]): {
  deduped: NormalizedJob[];
  duplicates: number;
} {
  const seen = new Set<string>();
  const deduped: NormalizedJob[] = [];
  let duplicates = 0;

  for (const job of jobs) {
    if (!job.hash) {
      deduped.push(job);
      continue;
    }
    if (seen.has(job.hash)) {
      duplicates += 1;
      continue;
    }
    seen.add(job.hash);
    deduped.push(job);
  }

  return { deduped, duplicates };
}
