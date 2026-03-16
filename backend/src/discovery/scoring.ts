const CAREER_KEYWORDS = [
  "careers",
  "career",
  "jobs",
  "work-with-us",
  "join-us",
  "open-roles",
  "openings",
];

export function scoreCareerLink(url: string, text: string): number {
  const lowerUrl = url.toLowerCase();
  const lowerText = text.toLowerCase();

  let score = 0.2;

  for (const keyword of CAREER_KEYWORDS) {
    if (lowerUrl.includes(keyword)) score += 0.35;
    if (lowerText.includes(keyword)) score += 0.2;
  }

  if (lowerUrl.includes("greenhouse.io") || lowerUrl.includes("lever.co")) {
    score += 0.3;
  }

  return Math.max(0, Math.min(1, score));
}
