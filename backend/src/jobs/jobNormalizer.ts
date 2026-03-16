import crypto from "node:crypto";
import type { Company, RawJob, NormalizedJob } from "./types";

export function buildJobHash(
  companyName: string,
  title: string,
  location: string,
): string {
  return crypto
    .createHash("sha256")
    .update(`${companyName}::${title}::${location}`.toLowerCase())
    .digest("hex");
}

export function normalizeJob(company: Company, raw: RawJob): NormalizedJob {
  const title = raw.title.trim();
  const location = raw.location.trim();
  const companyName = company.name;
  const hash = buildJobHash(companyName, title, location);

  return {
    companyId: company.id,
    companyName,
    title,
    location,
    descriptionHtml: raw.descriptionHtml,
    applyUrl: raw.applyUrl,
    postedAt: raw.postedAt ?? null,
    source: raw.source,
    externalId: raw.externalId,
    hash,
  };
}
