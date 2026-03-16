export type AtsType = "greenhouse" | "lever" | "ashby" | "workday" | "custom";

export interface Company {
  id: string;
  name: string;
  ats_type: AtsType;
  ats_slug: string | null;
  career_url: string | null;
  last_crawled: Date | null;
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
}

export interface NormalizedJob {
  companyId: string;
  companyName: string;
  title: string;
  location: string;
  descriptionHtml: string;
  applyUrl: string;
  postedAt: Date | null;
  source: string;
  externalId?: string;
  hash: string;
}
