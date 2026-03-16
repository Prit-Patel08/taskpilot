import crypto from "node:crypto";
import type { Company, RawJob, NormalizedJob } from "./types";
import { normalizeJobFields } from "./normalization";

export function buildJobHash(
  companyName: string,
  title: string,
  location: string,
): string {
  const normalizedCompany = companyName.trim().toLowerCase();
  const normalizedTitle = title.trim().toLowerCase();
  const normalizedLocation = location.trim().toLowerCase();
  return crypto
    .createHash("sha256")
    .update(
      `${normalizedCompany}::${normalizedTitle}::${normalizedLocation}`,
    )
    .digest("hex");
}

export function normalizeJob(company: Company, raw: RawJob): NormalizedJob {
  const title = raw.title.trim();
  const location = raw.location.trim();
  const companyName = company.name;
  const {
    locationRaw,
    locationNormalized,
    remoteType,
    seniority,
    employmentType,
  } = normalizeJobFields(title, location, raw.descriptionHtml);
  const hash = buildJobHash(
    companyName,
    title,
    locationNormalized || locationRaw,
  );

  return {
    companyId: company.id,
    companyName,
    title,
    location: locationRaw,
    locationRaw,
    locationNormalized,
    remoteType,
    seniority,
    employmentType,
    descriptionHtml: raw.descriptionHtml,
    applyUrl: raw.applyUrl,
    postedAt: raw.postedAt ?? null,
    source: raw.source,
    externalId: raw.externalId,
    hash,
  };
}
