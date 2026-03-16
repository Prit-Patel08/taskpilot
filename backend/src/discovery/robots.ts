import { fetchText } from "../ingestion/httpClient";

type RobotsRules = {
  disallow: string[];
  allow: string[];
};

const robotsCache = new Map<string, RobotsRules>();

function parseRobots(text: string): RobotsRules {
  const disallow: string[] = [];
  const allow: string[] = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const [rawKey, rawValue] = trimmed.split(":");
    const key = rawKey?.toLowerCase();
    const value = rawValue?.trim() ?? "";
    if (key === "disallow") disallow.push(value);
    if (key === "allow") allow.push(value);
  }
  return { disallow, allow };
}

export async function canFetchUrl(url: string): Promise<boolean> {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }

  const host = parsed.hostname;
  if (robotsCache.has(host)) {
    return isAllowed(parsed.pathname, robotsCache.get(host)!);
  }

  try {
    const robotsText = await fetchText(`${parsed.origin}/robots.txt`);
    const rules = parseRobots(robotsText);
    robotsCache.set(host, rules);
    return isAllowed(parsed.pathname, rules);
  } catch {
    return true;
  }
}

function isAllowed(pathname: string, rules: RobotsRules): boolean {
  if (rules.allow.some((rule) => pathname.startsWith(rule))) return true;
  if (rules.disallow.some((rule) => rule && pathname.startsWith(rule)))
    return false;
  return true;
}
