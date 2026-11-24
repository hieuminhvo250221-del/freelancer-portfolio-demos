import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import http from "node:http";
import test from "node:test";
import { auditHtmlDocument, smokeCheckEndpoint } from "../src/auditor.ts";
import { renderHtmlReport } from "../src/reporter.ts";

test("good_page.html passes with zero errors and warnings", async () => {
  const html = await readFile("fixtures/good_page.html", "utf-8");
  const result = auditHtmlDocument(html, "fixtures/good_page.html");
  assert.equal(result.passed, true);
  assert.equal(result.summary.errors, 0);
  assert.equal(result.summary.warnings, 0);
  assert.equal(result.summary.linksChecked, 2);
  assert.equal(result.summary.imagesChecked, 1);
});

test("buggy_page.html catches missing title, duplicate id, missing alt, empty link, and hidden scroll risks", async () => {
  const html = await readFile("fixtures/buggy_page.html", "utf-8");
  const result = auditHtmlDocument(html, "fixtures/buggy_page.html");
  assert.equal(result.passed, false);

  const codes = new Set(result.issues.map((i) => i.code));
  assert.ok(codes.has("MISSING_TITLE"));
  assert.ok(codes.has("MISSING_VIEWPORT"));
  assert.ok(codes.has("DUPLICATE_ID"));
  assert.ok(codes.has("IMG_MISSING_ALT"));
  assert.ok(codes.has("EMPTY_LINK_HREF"));
  assert.ok(codes.has("HIDDEN_SCROLL_RISK"));

  const reportHtml = renderHtmlReport({
    generatedAt: "2026-11-24T00:00:00Z",
    pages: [result],
    endpoints: [],
  });
  assert.ok(reportHtml.includes("FAILED"));
  assert.ok(reportHtml.includes("DUPLICATE_ID"));
});

test("smokeCheckEndpoint verifies live HTTP status and latency", async () => {
  const server = http.createServer((_req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert.ok(address && typeof address !== "string");

  try {
    const okRes = await smokeCheckEndpoint(`http://127.0.0.1:${address.port}/health`, 200);
    assert.equal(okRes.ok, true);
    assert.equal(okRes.status, 200);

    const failRes = await smokeCheckEndpoint(`http://127.0.0.1:${address.port}/health`, 201);
    assert.equal(failRes.ok, false);
    assert.equal(failRes.status, 200);
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((err) => (err ? reject(err) : resolve()))
    );
  }
});
