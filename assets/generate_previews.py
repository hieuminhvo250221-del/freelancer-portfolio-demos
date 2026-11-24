"""Generate crisp 1600x1200 PNG portfolio showcase cards for Freelancer.com."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1600, 1200


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        f"C:/Windows/Fonts/{name}",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_rounded_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: str,
    outline: str,
    width: int = 3,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: str = "#64748B",
    width: int = 4,
) -> None:
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    # Simple arrowhead pointing right or down
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 > x1 else -1
        draw.polygon(
            [(x2, y2), (x2 - 14 * sign, y2 - 8), (x2 - 14 * sign, y2 + 8)],
            fill=color,
        )
    else:
        sign = 1 if y2 > y1 else -1
        draw.polygon(
            [(x2, y2), (x2 - 8, y2 - 14 * sign), (x2 + 8, y2 - 14 * sign)],
            fill=color,
        )


def draw_badge(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    outline: str,
    text_color: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 22, 10
    draw_rounded_box(
        draw,
        (x, y, x + tw + pad_x * 2, y + th + pad_y * 2 + 4),
        18,
        fill,
        outline,
        1,
    )
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=text_color)


def make_n8n_card(out_path: Path) -> None:
    img = Image.new("RGB", (W, H), "#0F172A")
    draw = ImageDraw.Draw(img)

    f_badge = load_font("segoeuib.ttf", 22)
    f_title = load_font("segoeuib.ttf", 48)
    f_sub = load_font("segoeui.ttf", 26)
    f_node_t = load_font("segoeuib.ttf", 22)
    f_node_s = load_font("segoeui.ttf", 19)
    f_mono = load_font("consola.ttf", 20)

    # Header card
    draw_rounded_box(draw, (60, 50, 1540, 250), 24, "#1E293B", "#334155", 2)
    draw_badge(draw, 96, 80, "N8N WORKFLOW DEMO", f_badge, "#0EA5E9", "#38BDF8", "#0F172A")
    draw.text((96, 138), "Telegram Q&A Chatbot (Curated Q&A + AI Fallback)", font=f_title, fill="#F8FAFC")
    draw.text(
        (96, 200),
        "Single-file importable workflow.json  |  Telegram Bot API  |  OpenAI Grounded Matcher  |  Verified Schema",
        font=f_sub,
        fill="#94A3B8",
    )

    # Canvas grid background
    draw_rounded_box(draw, (60, 285, 1540, 915), 24, "#111827", "#1F2937", 2)
    for gx in range(100, 1520, 40):
        for gy in range(320, 900, 40):
            draw.ellipse((gx - 1, gy - 1, gx + 1, gy + 1), fill="#1F2937")

    # Nodes
    # 1. Telegram Trigger
    draw_rounded_box(draw, (95, 510, 365, 650), 18, "#1E293B", "#38BDF8", 3)
    draw.text((118, 535), "1. Telegram Trigger", font=f_node_t, fill="#38BDF8")
    draw.text((118, 578), "On incoming message", font=f_node_s, fill="#CBD5E1")
    draw.text((118, 608), "Extract chatId & text", font=f_node_s, fill="#94A3B8")

    draw_arrow(draw, 365, 580, 415, 580, "#94A3B8", 4)

    # 2. Match Curated Q&A
    draw_rounded_box(draw, (420, 510, 710, 650), 18, "#1E293B", "#A78BFA", 3)
    draw.text((442, 535), "2. Match Curated Q&A", font=f_node_t, fill="#C4B5FD")
    draw.text((442, 578), "Code node scoring", font=f_node_s, fill="#CBD5E1")
    draw.text((442, 608), "sample_qa.json lookup", font=f_node_s, fill="#94A3B8")

    draw_arrow(draw, 710, 580, 760, 580, "#94A3B8", 4)

    # 3. IF Node
    draw_rounded_box(draw, (765, 510, 1015, 650), 18, "#1E293B", "#F59E0B", 3)
    draw.text((788, 535), "3. Match >= 0.25?", font=f_node_t, fill="#FBBF24")
    draw.text((788, 578), "Deterministic IF gate", font=f_node_s, fill="#CBD5E1")
    draw.text((788, 608), "Zero-cost fast path", font=f_node_s, fill="#94A3B8")

    # True branch (top)
    draw.line((1015, 545, 1065, 545, 1065, 405, 1115, 405), fill="#22C55E", width=4)
    draw.polygon([(1120, 405), (1106, 397), (1106, 413)], fill="#22C55E")
    draw.text((985, 430), "TRUE", font=f_badge, fill="#4ADE80")

    draw_rounded_box(draw, (1125, 335, 1495, 475), 18, "#052E16", "#22C55E", 3)
    draw.text((1150, 360), "4A. Send Matched Reply", font=f_node_t, fill="#4ADE80")
    draw.text((1150, 403), "Telegram Markdown reply", font=f_node_s, fill="#DCFCE7")
    draw.text((1150, 433), "Direct curated answer", font=f_node_s, fill="#86EFAC")

    # False branch (bottom)
    draw.line((1015, 615, 1065, 615, 1065, 715, 1115, 715), fill="#38BDF8", width=4)
    draw.polygon([(1120, 715), (1106, 707), (1106, 723)], fill="#38BDF8")
    draw.text((978, 675), "FALSE", font=f_badge, fill="#38BDF8")

    draw_rounded_box(draw, (1125, 635, 1495, 760), 18, "#1E293B", "#38BDF8", 3)
    draw.text((1150, 655), "4B. AI Grounded Matcher", font=f_node_t, fill="#38BDF8")
    draw.text((1150, 695), "OpenAI JSON-mode (temp 0.1)", font=f_node_s, fill="#CBD5E1")
    draw.text((1150, 722), "Strictly Q&A-grounded", font=f_node_s, fill="#94A3B8")

    draw_arrow(draw, 1310, 760, 1310, 795, "#94A3B8", 4)
    draw_rounded_box(draw, (1125, 800, 1495, 890), 18, "#172554", "#60A5FA", 3)
    draw.text((1150, 818), "5. AI or Polite Fallback", font=f_node_t, fill="#93C5FD")
    draw.text((1150, 853), "Send answer or safe fallback", font=f_node_s, fill="#DBEAFE")

    # Bottom deliverables bar
    draw_rounded_box(draw, (60, 950, 1540, 1145), 24, "#1E293B", "#334155", 2)
    draw.text((96, 980), "Deliverables & Automated Verification", font=f_node_t, fill="#F8FAFC")
    draw.text(
        (96, 1025),
        "• workflow.json (importable directly into n8n)   • sample_qa.json (editable Q&A pairs)   • README.md",
        font=f_sub,
        fill="#CBD5E1",
    )
    draw.text(
        (96, 1075),
        "python -m unittest discover -s tests  ->  Ran 2 tests in 0.004s (OK)  |  github.com/hieuminhvo250221-del",
        font=f_mono,
        fill="#4ADE80",
    )

    img.save(out_path, format="PNG")


def make_python_card(out_path: Path) -> None:
    img = Image.new("RGB", (W, H), "#0F172A")
    draw = ImageDraw.Draw(img)

    f_badge = load_font("segoeuib.ttf", 22)
    f_title = load_font("segoeuib.ttf", 48)
    f_sub = load_font("segoeui.ttf", 26)
    f_node_t = load_font("segoeuib.ttf", 24)
    f_node_s = load_font("segoeui.ttf", 19)
    f_mono = load_font("consola.ttf", 20)

    # Header card
    draw_rounded_box(draw, (60, 50, 1540, 250), 24, "#1E293B", "#334155", 2)
    draw_badge(draw, 96, 80, "PYTHON API AUTOMATION", f_badge, "#22C55E", "#4ADE80", "#052E16")
    draw.text((96, 138), "Resilient API Collector (403 Recovery & Fault Isolation)", font=f_title, fill="#F8FAFC")
    draw.text(
        (96, 200),
        "Zero-dependency Python 3  |  Exponential Backoff + Jitter  |  Source Failover  |  Atomic JSON",
        font=f_sub,
        fill="#94A3B8",
    )

    # Left Pipeline Diagram
    draw_rounded_box(draw, (60, 285, 860, 915), 24, "#111827", "#1F2937", 2)
    draw.text((96, 315), "Fault-Tolerant Collection Pipeline", font=f_node_t, fill="#F8FAFC")

    draw_rounded_box(draw, (110, 375, 810, 470), 16, "#1E293B", "#38BDF8", 3)
    draw.text((140, 392), "1. Primary API Fetch + Exponential Backoff", font=f_node_t, fill="#38BDF8")
    draw.text((140, 428), "Retries HTTP 403 / 429 / 5xx with jitter + browser headers", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 470, 460, 515, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 520, 810, 615), 16, "#1E293B", "#F59E0B", 3)
    draw.text((140, 537), "2. Freshness SLA & Fallback Failover", font=f_node_t, fill="#FBBF24")
    draw.text((140, 573), "Rejects stale data (>30s); switches to secondary API cleanly", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 615, 460, 660, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 665, 810, 760), 16, "#1E293B", "#A78BFA", 3)
    draw.text((140, 682), "3. Per-Item Fault Isolation", font=f_node_t, fill="#C4B5FD")
    draw.text((140, 718), "One failing item logs cleanly without crashing the batch", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 760, 460, 800, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 805, 810, 885), 16, "#052E16", "#22C55E", 3)
    draw.text((140, 822), "4. Atomic JSON Snapshot + Windows .bat Launcher", font=f_node_t, fill="#4ADE80")

    # Right Terminal Verification Box
    draw_rounded_box(draw, (900, 285, 1540, 915), 24, "#020617", "#334155", 2)
    draw.text((936, 318), "Verified CLI & Unit Test Output", font=f_node_t, fill="#38BDF8")

    lines = [
        ("$ python -m unittest discover -s tests -v", "#F8FAFC"),
        ("test_falls_back_when_primary_exhausted ... ok", "#4ADE80"),
        ("test_recovers_from_transient_http_403 ... ok", "#4ADE80"),
        ("test_rejects_stale_payload_and_writes ... ok", "#4ADE80"),
        ("Ran 3 tests in 0.026s  ->  OK", "#4ADE80"),
        ("", "#94A3B8"),
        ("$ python -m collector.cli", "#F8FAFC"),
        ("[WARNING] [ITEM-101] HTTP 403 -> retrying", "#FBBF24"),
        ("[WARNING] [ITEM-102] HTTP 403 -> fallback", "#FBBF24"),
        ("[ERROR]   [ITEM-999] HTTP 404 isolated", "#F87171"),
        ("", "#94A3B8"),
        (" - ITEM-101: OK via primary_api  [att=2]", "#4ADE80"),
        (" - ITEM-102: OK via fallback_api [att=3]", "#4ADE80"),
        (" - ITEM-999: FAILED (isolated)   [att=4]", "#FCA5A5"),
        ("Snapshot written atomically: snapshot.json", "#38BDF8"),
    ]
    y = 378
    for text, color in lines:
        draw.text((936, y), text, font=f_mono, fill=color)
        y += 33

    # Bottom bar
    draw_rounded_box(draw, (60, 950, 1540, 1145), 24, "#1E293B", "#334155", 2)
    draw.text((96, 980), "Repository Structure & Key Modules", font=f_node_t, fill="#F8FAFC")
    draw.text(
        (96, 1025),
        "• collector/client.py   • collector/cli.py   • run_collector.bat   • tests/test_collector.py",
        font=f_sub,
        fill="#CBD5E1",
    )
    draw.text(
        (96, 1075),
        "Standard-library Python 3 (zero external deps)  |  github.com/hieuminhvo250221-del",
        font=f_mono,
        fill="#4ADE80",
    )

    img.save(out_path, format="PNG")


def make_order_api_card(out_path: Path) -> None:
    img = Image.new("RGB", (W, H), "#0F172A")
    draw = ImageDraw.Draw(img)

    f_badge = load_font("segoeuib.ttf", 22)
    f_title = load_font("segoeuib.ttf", 48)
    f_sub = load_font("segoeui.ttf", 26)
    f_node_t = load_font("segoeuib.ttf", 24)
    f_node_s = load_font("segoeui.ttf", 19)
    f_mono = load_font("consola.ttf", 20)

    # Header card
    draw_rounded_box(draw, (60, 50, 1540, 250), 24, "#1E293B", "#334155", 2)
    draw_badge(draw, 96, 80, "PYTHON REST API + SQLITE", f_badge, "#A855F7", "#C084FC", "#FFFFFF")
    draw.text((96, 138), "Order & Customer Validation Microservice", font=f_title, fill="#F8FAFC")
    draw.text(
        (96, 200),
        "REST Checkpoint API  |  Stock & CRM Match  |  Live Rule Toggles  |  SQLite Audit Trail",
        font=f_sub,
        fill="#94A3B8",
    )

    # Left Pipeline
    draw_rounded_box(draw, (60, 285, 860, 915), 24, "#111827", "#1F2937", 2)
    draw.text((96, 315), "Validation Checkpoint & Live Rule Engine", font=f_node_t, fill="#F8FAFC")

    draw_rounded_box(draw, (110, 375, 810, 470), 16, "#1E293B", "#38BDF8", 3)
    draw.text((140, 392), "1. POST /orders/validate", font=f_node_t, fill="#38BDF8")
    draw.text((140, 428), "Validates order_id, SKU quantities & duplicate submissions", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 470, 460, 515, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 520, 810, 615), 16, "#1E293B", "#F59E0B", 3)
    draw.text((140, 537), "2. Customer Profile & Stock Cross-Check", font=f_node_t, fill="#FBBF24")
    draw.text((140, 573), "Detects ADDRESS_MISMATCH, PHONE_MISMATCH & OUT_OF_STOCK", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 615, 460, 660, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 665, 810, 760), 16, "#1E293B", "#C084FC", 3)
    draw.text((140, 682), "3. PATCH /rules/{rule_name}", font=f_node_t, fill="#D8B4FE")
    draw.text((140, 718), "Toggle checks on/off dynamically in SQLite without restart", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 760, 460, 800, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 805, 810, 885), 16, "#052E16", "#22C55E", 3)
    draw.text((140, 822), "4. Risk Scoring (LOW/MEDIUM/HIGH) + Audit Logs", font=f_node_t, fill="#4ADE80")

    # Right Terminal
    draw_rounded_box(draw, (900, 285, 1540, 915), 24, "#020617", "#334155", 2)
    draw.text((936, 318), "Verified Integration Tests & Output", font=f_node_t, fill="#C084FC")

    lines = [
        ("$ python -m unittest discover -s tests -v", "#F8FAFC"),
        ("test_flags_mismatch_and_out_of_stock ... ok", "#4ADE80"),
        ("test_valid_order_approved_and_dup    ... ok", "#4ADE80"),
        ("Ran 2 tests in 1.62s  ->  OK (0 warnings)", "#4ADE80"),
        ("", "#94A3B8"),
        ("POST /orders/validate  (ORD-1002)", "#38BDF8"),
        ("{", "#CBD5E1"),
        ('  "approved": false,', "#F87171"),
        ('  "risk_level": "HIGH",', "#FBBF24"),
        ('  "issues": [', "#CBD5E1"),
        ('    "ADDRESS_MISMATCH",', "#FCA5A5"),
        ('    "PHONE_MISMATCH",', "#FCA5A5"),
        ('    "OUT_OF_STOCK"', "#FCA5A5"),
        ("  ]", "#CBD5E1"),
        ("}", "#CBD5E1"),
    ]
    y = 378
    for text, color in lines:
        draw.text((936, y), text, font=f_mono, fill=color)
        y += 33

    # Bottom bar
    draw_rounded_box(draw, (60, 950, 1540, 1145), 24, "#1E293B", "#334155", 2)
    draw.text((96, 980), "Repository Structure & Key Modules", font=f_node_t, fill="#F8FAFC")
    draw.text(
        (96, 1025),
        "• app/db.py   • app/validator.py   • app/server.py   • app/cli.py   • tests/test_api.py",
        font=f_sub,
        fill="#CBD5E1",
    )
    draw.text(
        (96, 1075),
        "Python 3 + SQLite + ThreadingHTTPServer  |  github.com/hieuminhvo250221-del",
        font=f_mono,
        fill="#4ADE80",
    )

    img.save(out_path, format="PNG")


def make_qa_card(out_path: Path) -> None:
    img = Image.new("RGB", (W, H), "#0F172A")
    draw = ImageDraw.Draw(img)

    f_badge = load_font("segoeuib.ttf", 22)
    f_title = load_font("segoeuib.ttf", 48)
    f_sub = load_font("segoeui.ttf", 26)
    f_node_t = load_font("segoeuib.ttf", 24)
    f_node_s = load_font("segoeui.ttf", 19)
    f_mono = load_font("consola.ttf", 20)

    # Header card
    draw_rounded_box(draw, (60, 50, 1540, 250), 24, "#1E293B", "#334155", 2)
    draw_badge(draw, 96, 80, "TYPESCRIPT QA AUTOMATION", f_badge, "#F59E0B", "#FBBF24", "#0F172A")
    draw.text((96, 138), "Web QA & DOM Layout Auditor (JSON + HTML Reports)", font=f_title, fill="#F8FAFC")
    draw.text(
        (96, 200),
        "Native Node.js TypeScript  |  Accessibility & Link Hygiene  |  Hidden-Scroll CSS  |  Smoke Tests",
        font=f_sub,
        fill="#94A3B8",
    )

    # Left Pipeline
    draw_rounded_box(draw, (60, 285, 860, 915), 24, "#111827", "#1F2937", 2)
    draw.text((96, 315), "Automated QA Verification Pipeline", font=f_node_t, fill="#F8FAFC")

    draw_rounded_box(draw, (110, 375, 810, 470), 16, "#1E293B", "#38BDF8", 3)
    draw.text((140, 392), "1. HTML & Accessibility Rule Audit", font=f_node_t, fill="#38BDF8")
    draw.text((140, 428), "Flags missing <title>, viewport, img alt & duplicate IDs", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 470, 460, 515, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 520, 810, 615), 16, "#1E293B", "#F59E0B", 3)
    draw.text((140, 537), "2. CSS Hidden-Scroll & Dead-Link Detector", font=f_node_t, fill="#FBBF24")
    draw.text((140, 573), "Detects overflow:hidden traps, hidden scrollbars & '#' links", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 615, 460, 660, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 665, 810, 760), 16, "#1E293B", "#A78BFA", 3)
    draw.text((140, 682), "3. HTTP Endpoint Latency Smoke Checks", font=f_node_t, fill="#C4B5FD")
    draw.text((140, 718), "Verifies HTTP status codes, timeouts & response latency", font=f_node_s, fill="#CBD5E1")

    draw_arrow(draw, 460, 760, 460, 800, "#94A3B8", 4)

    draw_rounded_box(draw, (110, 805, 810, 885), 16, "#052E16", "#22C55E", 3)
    draw.text((140, 822), "4. Standalone HTML Dashboard + report.json", font=f_node_t, fill="#4ADE80")

    # Right Terminal
    draw_rounded_box(draw, (900, 285, 1540, 915), 24, "#020617", "#334155", 2)
    draw.text((936, 318), "Verified node:test & CLI Output", font=f_node_t, fill="#FBBF24")

    lines = [
        ("$ node --test tests/auditor.test.ts", "#F8FAFC"),
        ("ok good_page.html passes zero issues", "#4ADE80"),
        ("ok buggy_page.html catches 6 defects", "#4ADE80"),
        ("ok smokeCheckEndpoint verifies status", "#4ADE80"),
        ("tests 3 | pass 3 | fail 0", "#4ADE80"),
        ("", "#94A3B8"),
        ("$ node src/cli.ts fixtures/*.html", "#F8FAFC"),
        ("good_page.html:  PASSED (err=0, warn=0)", "#4ADE80"),
        ("buggy_page.html: FAILED (err=3, warn=4)", "#F87171"),
        (" - MISSING_TITLE / DUPLICATE_ID", "#FCA5A5"),
        (" - IMG_MISSING_ALT / EMPTY_LINK_HREF", "#FCA5A5"),
        (" - HIDDEN_SCROLL_RISK", "#FBBF24"),
        ("", "#94A3B8"),
        ("Generated: report.json & report.html", "#38BDF8"),
    ]
    y = 378
    for text, color in lines:
        draw.text((936, y), text, font=f_mono, fill=color)
        y += 33

    # Bottom bar
    draw_rounded_box(draw, (60, 950, 1540, 1145), 24, "#1E293B", "#334155", 2)
    draw.text((96, 980), "Repository Structure & Key Modules", font=f_node_t, fill="#F8FAFC")
    draw.text(
        (96, 1025),
        "• src/auditor.ts   • src/reporter.ts   • src/cli.ts   • fixtures/   • tests/auditor.test.ts",
        font=f_sub,
        fill="#CBD5E1",
    )
    draw.text(
        (96, 1075),
        "Zero-dependency TypeScript (Node 24)  |  github.com/hieuminhvo250221-del",
        font=f_mono,
        fill="#4ADE80",
    )

    img.save(out_path, format="PNG")


if __name__ == "__main__":
    make_n8n_card(ASSETS_DIR / "n8n-telegram-qa-preview.png")
    make_python_card(ASSETS_DIR / "resilient-api-collector-preview.png")
    make_order_api_card(ASSETS_DIR / "order-validation-api-preview.png")
    make_qa_card(ASSETS_DIR / "web-qa-auditor-preview.png")
    print("Generated all 4 1600x1200 preview cards successfully.")
