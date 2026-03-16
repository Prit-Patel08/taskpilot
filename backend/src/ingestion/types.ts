import type { AtsType } from "../domain/ats";

export type { AtsType };

export type RemoteType = "remote" | "hybrid" | "onsite" | "unknown";
export type Seniority =
  | "intern"
  | "junior"
  | "mid"
  | "senior"
  | "staff"
  | "lead"
  | "principal"
  | "manager"
  | "director"
  | "vp"
  | "cxo"
  | "unknown";
export type EmploymentType =
  | "full_time"
  | "part_time"
  | "contract"
  | "internship"
  | "temporary"
  | "unknown";

export interface Company {
  id: string;
  name: string;
  ats_type: AtsType;
  ats_slug: string | null;
  career_url: string | null;
  last_crawled: Date | null;
  crawl_interval_seconds?: number | null;
  is_active?: boolean | null;
}

export interface RawJob {
  companyName: string;
  title: string;
  location: string;
  descriptionHtml: string;
  applyUrl: string;
  postedAt: Date | null;
  source: string;
  externalId?: string;
  rawPayload?: unknown;
}

export interface NormalizedJob {
  companyId: string;
  companyName: string;
  title: string;
  location: string;
  locationRaw: string;
  locationNormalized: string;
  remoteType: RemoteType;
  seniority: Seniority;
  employmentType: EmploymentType;
  descriptionHtml: string;
  applyUrl: string;
  postedAt: Date | null;
  source: string;
  externalId?: string;
  hash: string;
}

export interface QueueTask {
  id: string;
  company_id: string;
  attempts: number;
  scheduled_for: Date;
}

export interface IngestionResult {
  companyId: string;
  totalRaw: number;
  inserted: number;
  skipped: number;
  duplicates: number;
}
