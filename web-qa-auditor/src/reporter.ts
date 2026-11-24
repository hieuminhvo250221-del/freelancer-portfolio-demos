import type { EndpointSmokeResult, PageAuditResult } from "./auditor.ts";

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export interface FullQaReport {
  generatedAt: string;
  pages: PageAuditResult[];
  endpoints: EndpointSmokeResult[];
}

export function renderHtmlReport(report: FullQaReport): string {
  const pageCards = report.pages
    .map((page) => {
      const badgeColor = page.passed ? "#16a34a" : "#dc2626";
      const badgeLabel = page.passed ? "PASSED" : "FAILED";
      const issueRows =
        page.issues.length === 0
          ? "<tr><td colspan='3'>No issues detected.</td></tr>"
          : page.issues
              .map(
                (i) =>
                  `<tr><td><strong>${escapeHtml(i.code)}</strong></td><td>${escapeHtml(
                    i.severity.toUpperCase()
                  )}</td><td>${escapeHtml(i.message)}</td></tr>`
              )
              .join("\n");

      return `
      <section class="card">
        <div class="card-head">
          <h2>${escapeHtml(page.target)}</h2>
          <span class="badge" style="background:${badgeColor}">${badgeLabel}</span>
        </div>
        <p>Errors: ${page.summary.errors} | Warnings: ${page.summary.warnings} | Links: ${page.summary.linksChecked} | Images: ${page.summary.imagesChecked}</p>
        <table>
          <thead><tr><th>Code</th><th>Severity</th><th>Message</th></tr></thead>
          <tbody>${issueRows}</tbody>
        </table>
      </section>`;
    })
    .join("\n");

  const endpointRows =
    report.endpoints.length === 0
      ? "<tr><td colspan='4'>No endpoints checked.</td></tr>"
      : report.endpoints
          .map(
            (e) =>
              `<tr><td>${escapeHtml(e.url)}</td><td>${e.ok ? "OK" : "FAIL"}</td><td>${
                e.status ?? "-"
              }</td><td>${e.latencyMs} ms</td></tr>`
          )
          .join("\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Web QA Audit Report</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 32px; }
    h1, h2 { margin-top: 0; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    .card-head { display: flex; justify-content: space-between; align-items: center; }
    .badge { color: #fff; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #334155; font-size: 14px; }
  </style>
</head>
<body>
  <h1>Web QA &amp; Layout Audit Report</h1>
  <p>Generated at: ${escapeHtml(report.generatedAt)}</p>
  ${pageCards}
  <section class="card">
    <h2>API Endpoint Smoke Checks</h2>
    <table>
      <thead><tr><th>URL</th><th>Result</th><th>Status</th><th>Latency</th></tr></thead>
      <tbody>${endpointRows}</tbody>
    </table>
  </section>
</body>
</html>`;
}
