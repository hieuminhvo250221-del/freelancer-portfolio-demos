export type Severity = "error" | "warning" | "info";

export interface AuditIssue {
  code: string;
  severity: Severity;
  message: string;
  detail?: string;
}

export interface PageAuditResult {
  target: string;
  passed: boolean;
  summary: {
    errors: number;
    warnings: number;
    linksChecked: number;
    imagesChecked: number;
  };
  issues: AuditIssue[];
}

export interface EndpointSmokeResult {
  url: string;
  ok: boolean;
  status: number | null;
  latencyMs: number;
  error?: string;
}

/**
 * Audit raw HTML markup for QA, accessibility, link hygiene, and CSS hidden-scroll risks.
 */
export function auditHtmlDocument(html: string, target: string): PageAuditResult {
  const issues: AuditIssue[] = [];

  if (!/<title>\s*[^<\s][^<]*<\/title>/i.test(html)) {
    issues.push({
      code: "MISSING_TITLE",
      severity: "error",
      message: "Document is missing a non-empty <title> element.",
    });
  }

  if (!/<meta\s+[^>]*name=["']viewport["'][^>]*>/i.test(html)) {
    issues.push({
      code: "MISSING_VIEWPORT",
      severity: "warning",
      message: "Missing <meta name=\"viewport\"> tag for mobile responsiveness.",
    });
  }

  // Check duplicate element IDs
  const idCounts = new Map<string, number>();
  const idRegex = /\bid\s*=\s*["']([^"']+)["']/gi;
  let idMatch: RegExpExecArray | null;
  while ((idMatch = idRegex.exec(html)) !== null) {
    const idVal = idMatch[1].trim();
    idCounts.set(idVal, (idCounts.get(idVal) ?? 0) + 1);
  }
  for (const [idVal, count] of idCounts.entries()) {
    if (count > 1) {
      issues.push({
        code: "DUPLICATE_ID",
        severity: "error",
        message: `Duplicate element id "${idVal}" appears ${count} times.`,
      });
    }
  }

  // Check <img> alt attributes
  const imgRegex = /<img\b([^>]*)>/gi;
  let imgMatch: RegExpExecArray | null;
  let imagesChecked = 0;
  while ((imgMatch = imgRegex.exec(html)) !== null) {
    imagesChecked += 1;
    const attrs = imgMatch[1];
    if (!/\balt\s*=\s*["'][^"']*["']/i.test(attrs)) {
      issues.push({
        code: "IMG_MISSING_ALT",
        severity: "error",
        message: "Image tag is missing an alt attribute.",
        detail: imgMatch[0].slice(0, 80),
      });
    }
  }

  // Check <a> href placeholders & dead links
  const linkRegex = /<a\b([^>]*)>/gi;
  let linkMatch: RegExpExecArray | null;
  let linksChecked = 0;
  while ((linkMatch = linkRegex.exec(html)) !== null) {
    linksChecked += 1;
    const attrs = linkMatch[1];
    const hrefMatch = /\bhref\s*=\s*["']([^"']*)["']/i.exec(attrs);
    if (!hrefMatch || hrefMatch[1].trim() === "" || hrefMatch[1].trim() === "#") {
      issues.push({
        code: "EMPTY_LINK_HREF",
        severity: "warning",
        message: "Anchor tag uses an empty or '#' placeholder href.",
        detail: linkMatch[0].slice(0, 80),
      });
    }
  }

  // Detect CSS hidden-scrollbar / overflow-clipping risks
  const hiddenScrollbarPatterns: Array<[RegExp, string]> = [
    [
      /scrollbar-width\s*:\s*none/i,
      "CSS 'scrollbar-width: none' hides scroll indicators from users.",
    ],
    [
      /::-webkit-scrollbar\s*\{[^}]*display\s*:\s*none/i,
      "CSS '::-webkit-scrollbar { display: none }' hides WebKit scrollbars.",
    ],
    [
      /overflow(?:-[xy])?\s*:\s*hidden\b[^;{}]*(?:height|max-height)\s*:\s*\d+/i,
      "Fixed height paired with overflow:hidden may clip scroll content silently.",
    ],
  ];

  for (const [pattern, message] of hiddenScrollbarPatterns) {
    if (pattern.test(html)) {
      issues.push({
        code: "HIDDEN_SCROLL_RISK",
        severity: "warning",
        message,
      });
    }
  }

  const errors = issues.filter((i) => i.severity === "error").length;
  const warnings = issues.filter((i) => i.severity === "warning").length;

  return {
    target,
    passed: errors === 0,
    summary: {
      errors,
      warnings,
      linksChecked,
      imagesChecked,
    },
    issues,
  };
}

/**
 * Run an HTTP smoke check against an endpoint and measure response latency.
 */
export async function smokeCheckEndpoint(
  url: string,
  expectedStatus = 200,
  timeoutMs = 5000
): Promise<EndpointSmokeResult> {
  const started = performance.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const resp = await fetch(url, { signal: controller.signal });
    const latencyMs = Math.round(performance.now() - started);
    return {
      url,
      ok: resp.status === expectedStatus,
      status: resp.status,
      latencyMs,
      error:
        resp.status === expectedStatus
          ? undefined
          : `Expected HTTP ${expectedStatus}, got ${resp.status}`,
    };
  } catch (err) {
    const latencyMs = Math.round(performance.now() - started);
    return {
      url,
      ok: false,
      status: null,
      latencyMs,
      error: err instanceof Error ? err.message : String(err),
    };
  } finally {
    clearTimeout(timer);
  }
}
