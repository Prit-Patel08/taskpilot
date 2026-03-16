import type { AtsType } from "../domain/ats";

export type DiscoverySource = "seed" | "crawl" | "sitemap" | "user";

export interface CompanyCandidate {
  domain: string;
  guessed_careers_url: string | null;
  ats_type: AtsType | null;
  ats_slug: string | null;
  confidence: number;
  discovery_source: DiscoverySource;
}
