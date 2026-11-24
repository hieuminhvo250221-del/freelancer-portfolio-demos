import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { auditHtmlDocument, type PageAuditResult } from "./auditor.ts";
import { renderHtmlReport, type FullQaReport } from "./reporter.ts";

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  const outIdx = args.indexOf("--out");
  const outDir = outIdx >= 0 && args[outIdx + 1] ? args[outIdx + 1] : "output";

  const htmlFiles = args.filter(
    (arg, idx) => !arg.startsWith("--") && (outIdx < 0 || idx !== outIdx + 1)
  );
  const targets =
    htmlFiles.length > 0
      ? htmlFiles
      : ["fixtures/good_page.html", "fixtures/buggy_page.html"];

  const pages: PageAuditResult[] = [];
  for (const filePath of targets) {
    const content = await readFile(filePath, "utf-8");
    pages.push(auditHtmlDocument(content, filePath));
  }

  const report: FullQaReport = {
    generatedAt: new Date().toISOString(),
    pages,
    endpoints: [],
  };

  await mkdir(outDir, { recursive: true });
  const jsonPath = path.join(outDir, "report.json");
  const htmlPath = path.join(outDir, "report.html");
  await writeFile(jsonPath, JSON.stringify(report, null, 2), "utf-8");
  await writeFile(htmlPath, renderHtmlReport(report), "utf-8");

  for (const p of pages) {
    console.log(
      `${p.target}: ${p.passed ? "PASSED" : "FAILED"} (errors=${p.summary.errors}, warnings=${p.summary.warnings})`
    );
  }
  console.log(`Reports written to ${jsonPath} and ${htmlPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
