# Web QA & DOM Layout Auditor (TypeScript / Node.js)

A zero-dependency TypeScript QA automation tool that audits HTML pages and API endpoints for accessibility defects, broken link placeholders, duplicate IDs, CSS hidden-scroll content risks, and HTTP smoke regressions—generating both JSON and standalone HTML QA reports.

## Architecture

```mermaid
flowchart LR
    A["HTML Fixtures / Pages"] --> B["TypeScript QA Auditor"]
    C["HTTP Endpoints"] --> B
    B --> D["DOM & Link Hygiene Checks"]
    B --> E["CSS Hidden-Scroll Risk Detector"]
    B --> F["Endpoint Latency & Status Smoke Check"]
    D & E & F --> G["report.json + report.html"]
```

## Quick Start
Run the demo audit on the sample fixtures:
```bash
node src/cli.ts fixtures/good_page.html fixtures/buggy_page.html --out output
```

Run the automated TypeScript test suite (`node:test`):
```bash
node --test tests/auditor.test.ts
```
