export type AtsType = "greenhouse" | "lever" | "ashby" | "workday" | "custom";

type AtsMatch = {
  atsType: AtsType;
  atsSlug?: string | null;
};

const ATS_PATTERNS: Array<{ type: AtsType; pattern: RegExp }> = [
  { type: "greenhouse", pattern: /boards\.greenhouse\.io/i },
  { type: "greenhouse", pattern: /greenhouse\.io/i },
  { type: "lever", pattern: /jobs\.lever\.co/i },
  { type: "lever", pattern: /lever\.co/i },
  { type: "ashby", pattern: /jobs\.ashbyhq\.com/i },
  { type: "ashby", pattern: /ashbyhq\.com/i },
  { type: "workday", pattern: /myworkdayjobs\.com/i },
  { type: "workday", pattern: /\/wday\/cxs\//i },
];

export function detectAtsFromUrl(url: string): AtsMatch | null {
  for (const entry of ATS_PATTERNS) {
    if (entry.pattern.test(url)) {
      const atsSlug = extractAtsSlug(entry.type, url);
      return { atsType: entry.type, atsSlug };
    }
  }
  return null;
}

export function detectAtsFromHtml(html: string): AtsMatch | null {
  return detectAtsFromUrl(html);
}

export function extractAtsSlug(
  atsType: AtsType,
  url: string,
): string | null {
  let parsed: URL | null = null;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }

  const pathParts = parsed.pathname.split("/").filter(Boolean);

  switch (atsType) {
    case "greenhouse": {
      const forParam = parsed.searchParams.get("for");
      if (forParam) return forParam;
      return pathParts[0] ?? null;
    }
    case "lever":
    case "ashby":
      return pathParts[0] ?? null;
    case "workday":
      return null;
    default:
      return null;
  }
}
