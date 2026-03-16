import { log } from "../logger";
import { fetchText } from "../ingestion/httpClient";
import { detectAtsFromHtml, detectAtsFromUrl } from "../domain/ats";
import { extractLinks } from "./linkExtractor";
import { scoreCareerLink } from "./scoring";
import { canFetchUrl } from "./robots";
import type { CompanyCandidate, DiscoverySource } from "./types";

const SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"];
const MAX_SITEMAP_LINKS = 200;

function normalizeDomain(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) return trimmed;
  const withScheme = trimmed.startsWith("http")
    ? trimmed
    : `https://${trimmed}`;
  try {
    const parsed = new URL(withScheme);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return trimmed.replace(/^www\./, "");
  }
}

async function fetchHomepage(domain: string): Promise<string | null> {
  const candidates = [
    `https://${domain}`,
    `https://www.${domain}`,
    `http://${domain}`,
    `http://www.${domain}`,
  ];

  for (const url of candidates) {
    const allowed = await canFetchUrl(url);
    if (!allowed) {
      log.warn("Robots disallowed homepage fetch", { domain, url });
      continue;
    }
    try {
      return await fetchText(url, {
        headers: { "User-Agent": "TaskPilotDiscoveryBot/1.0" },
      });
    } catch (err) {
      log.warn("Homepage fetch failed", {
        domain,
        url,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
  return null;
}

async function fetchSitemapLinks(domain: string): Promise<string[]> {
  const links: string[] = [];
  for (const path of SITEMAP_PATHS) {
    const sitemapUrl = `https://${domain}${path}`;
    const allowed = await canFetchUrl(sitemapUrl);
    if (!allowed) {
      log.warn("Robots disallowed sitemap fetch", { domain, sitemapUrl });
      continue;
    }
    try {
      const xml = await fetchText(sitemapUrl);
      const locMatches = xml.match(/<loc>(.*?)<\/loc>/gi) ?? [];
      for (const match of locMatches) {
        const loc = match.replace(/<\/?loc>/gi, "").trim();
        if (!loc) continue;
        links.push(loc);
        if (links.length >= MAX_SITEMAP_LINKS) break;
      }
    } catch {
      continue;
    }
  }
  return links;
}

function buildCandidate(
  domain: string,
  url: string,
  discovery_source: DiscoverySource,
  text = "",
): CompanyCandidate {
  const atsMatch = detectAtsFromUrl(url);
  return {
    domain,
    guessed_careers_url: url,
    ats_type: atsMatch?.atsType ?? null,
    ats_slug: atsMatch?.atsSlug ?? null,
    confidence: scoreCareerLink(url, text),
    discovery_source,
  };
}

export async function discoverCompanyCandidates(
  rawDomain: string,
): Promise<CompanyCandidate[]> {
  const domain = normalizeDomain(rawDomain);
  if (!domain) return [];

  const html = await fetchHomepage(domain);
  const candidates: CompanyCandidate[] = [];

  if (html) {
    const atsInHtml = detectAtsFromHtml(html);
    if (atsInHtml) {
      candidates.push({
        domain,
        guessed_careers_url: null,
        ats_type: atsInHtml.atsType,
        ats_slug: atsInHtml.atsSlug ?? null,
        confidence: 0.6,
        discovery_source: "crawl",
      });
    }

    const baseUrl = `https://${domain}`;
    const links = extractLinks(html, baseUrl);
    for (const link of links) {
      if (!link.href.includes(domain) && !detectAtsFromUrl(link.href)) continue;
      const score = scoreCareerLink(link.href, link.text);
      if (score < 0.35) continue;
      candidates.push(buildCandidate(domain, link.href, "crawl", link.text));
    }
  }

  const sitemapLinks = await fetchSitemapLinks(domain);
  for (const link of sitemapLinks) {
    if (!link.includes(domain) && !detectAtsFromUrl(link)) continue;
    const score = scoreCareerLink(link, "");
    if (score < 0.35) continue;
    candidates.push(buildCandidate(domain, link, "sitemap"));
  }

  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    const key = `${candidate.domain}::${candidate.guessed_careers_url ?? ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
