type LinkEntry = {
  href: string;
  text: string;
};

const LINK_REGEX = /<a\s+[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;

function stripHtml(text: string): string {
  return text.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

export function extractLinks(html: string, baseUrl: string): LinkEntry[] {
  const links: LinkEntry[] = [];
  let match: RegExpExecArray | null;

  while ((match = LINK_REGEX.exec(html)) !== null) {
    const rawHref = match[1]?.trim();
    if (!rawHref || rawHref.startsWith("javascript:")) continue;
    if (rawHref.startsWith("#")) continue;

    let href = rawHref;
    try {
      href = new URL(rawHref, baseUrl).toString();
    } catch {
      continue;
    }

    links.push({
      href,
      text: stripHtml(match[2] ?? ""),
    });
  }

  return links;
}
