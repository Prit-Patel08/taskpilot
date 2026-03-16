import type { EmploymentType, RemoteType, Seniority } from "./types";

const REMOTE_PATTERNS = [
  /\bremote\b/i,
  /\bwork\s*from\s*home\b/i,
  /\bwfh\b/i,
  /\bdistributed\b/i,
];

const ONSITE_PATTERNS = [/\bon[-\s]?site\b/i, /\bonsite\b/i];

const HYBRID_PATTERNS = [/\bhybrid\b/i];

const SENIORITY_RULES: Array<{ value: Seniority; pattern: RegExp }> = [
  { value: "intern", pattern: /\bintern(ship)?\b/i },
  { value: "junior", pattern: /\bjunior\b|\bjr\.?\b/i },
  { value: "mid", pattern: /\bmid\b|\bmid-level\b|\bintermediate\b/i },
  { value: "senior", pattern: /\bsenior\b|\bsr\.?\b/i },
  { value: "staff", pattern: /\bstaff\b/i },
  { value: "principal", pattern: /\bprincipal\b/i },
  { value: "lead", pattern: /\blead\b/i },
  { value: "manager", pattern: /\bmanager\b/i },
  { value: "director", pattern: /\bdirector\b/i },
  { value: "vp", pattern: /\bvp\b|\bvice president\b/i },
  { value: "cxo", pattern: /\bchief\b|\bc[eo]o\b|\bcfo\b|\bcto\b/i },
];

const EMPLOYMENT_RULES: Array<{ value: EmploymentType; pattern: RegExp }> = [
  { value: "internship", pattern: /\bintern(ship)?\b/i },
  { value: "part_time", pattern: /\bpart[-\s]?time\b/i },
  { value: "contract", pattern: /\bcontract\b|\bcontractor\b/i },
  { value: "temporary", pattern: /\btemporary\b|\btemp\b/i },
  { value: "full_time", pattern: /\bfull[-\s]?time\b/i },
];

export function detectRemoteType(text: string): RemoteType {
  if (HYBRID_PATTERNS.some((pattern) => pattern.test(text))) {
    return "hybrid";
  }
  if (REMOTE_PATTERNS.some((pattern) => pattern.test(text))) {
    return "remote";
  }
  if (ONSITE_PATTERNS.some((pattern) => pattern.test(text))) {
    return "onsite";
  }
  return "unknown";
}

export function normalizeLocationText(raw: string): string {
  const cleaned = raw.replace(/\s+/g, " ").trim();
  if (!cleaned) return "";

  const stripped = cleaned
    .replace(/\((remote|hybrid|onsite|on-site)\)/gi, "")
    .replace(/\b(remote|hybrid|onsite|on-site|work from home|wfh)\b/gi, "")
    .replace(/\s*[-/|]\s*/g, ", ")
    .replace(/\s*,\s*/g, ", ")
    .replace(/\s{2,}/g, " ")
    .trim();

  const [first] = stripped.split(/\s*,\s*or\s+|\s+or\s+|\s*\/\s*/i);
  return (first ?? stripped).trim();
}

export function detectSeniority(text: string): Seniority {
  for (const rule of SENIORITY_RULES) {
    if (rule.pattern.test(text)) {
      return rule.value;
    }
  }
  return "unknown";
}

export function detectEmploymentType(text: string): EmploymentType {
  for (const rule of EMPLOYMENT_RULES) {
    if (rule.pattern.test(text)) {
      return rule.value;
    }
  }
  return "unknown";
}

export function normalizeJobFields(
  title: string,
  location: string,
  descriptionHtml: string,
): {
  locationRaw: string;
  locationNormalized: string;
  remoteType: RemoteType;
  seniority: Seniority;
  employmentType: EmploymentType;
} {
  const locationRaw = location.trim();
  const combinedText = `${title} ${locationRaw} ${descriptionHtml}`.toLowerCase();
  const remoteType = detectRemoteType(combinedText);
  const locationNormalized =
    normalizeLocationText(locationRaw) || (remoteType === "remote" ? "Remote" : "");
  const seniority = detectSeniority(combinedText);
  const employmentType = detectEmploymentType(combinedText);

  return {
    locationRaw,
    locationNormalized,
    remoteType,
    seniority,
    employmentType,
  };
}
