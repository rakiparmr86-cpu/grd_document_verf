from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf"
TECHNICAL_PDF = OUTPUT / "GRD_Document_Verification_Technical_Guide.pdf"
FLOW_PDF = OUTPUT / "GRD_Document_Verification_Flowchart.pdf"

NAVY = colors.HexColor("#13233A")
BLUE = colors.HexColor("#3478F6")
BLUE_DARK = colors.HexColor("#235BC2")
BLUE_LIGHT = colors.HexColor("#EAF1FF")
CYAN = colors.HexColor("#1CA6C8")
CYAN_LIGHT = colors.HexColor("#E8F8FC")
GREEN = colors.HexColor("#2A9D62")
GREEN_LIGHT = colors.HexColor("#E9F8EF")
ORANGE = colors.HexColor("#E7902B")
ORANGE_LIGHT = colors.HexColor("#FFF3E5")
RED = colors.HexColor("#C94D45")
RED_LIGHT = colors.HexColor("#FDECEA")
PURPLE = colors.HexColor("#7B61C9")
PURPLE_LIGHT = colors.HexColor("#F1EDFC")
INK = colors.HexColor("#25364D")
MUTED = colors.HexColor("#66758A")
LINE = colors.HexColor("#D9E1EC")
PANEL = colors.HexColor("#F6F8FB")
WHITE = colors.white


def make_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=33,
            textColor=NAVY,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=18,
            textColor=MUTED,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=NAVY,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=NAVY,
            spaceBefore=5,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.3,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.5,
            textColor=MUTED,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=NAVY,
            backColor=PANEL,
            borderColor=LINE,
            borderWidth=0.5,
            borderPadding=6,
            spaceAfter=6,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=WHITE,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=9.6,
            textColor=INK,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=BLUE_DARK,
            backColor=BLUE_LIGHT,
            borderColor=BLUE,
            borderWidth=0.8,
            borderPadding=8,
            spaceAfter=8,
        ),
        "simple_title": ParagraphStyle(
            "SimpleTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            alignment=TA_CENTER,
            textColor=NAVY,
            spaceAfter=7,
        ),
        "simple_body": ParagraphStyle(
            "SimpleBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            textColor=INK,
        ),
    }


STYLES = make_styles()


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def draw_arrow(c, x1, y1, x2, y2, color=BLUE, width=1.5):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 5
    points = [
        (x2, y2),
        (
            x2 - size * math.cos(angle - math.pi / 6),
            y2 - size * math.sin(angle - math.pi / 6),
        ),
        (
            x2 - size * math.cos(angle + math.pi / 6),
            y2 - size * math.sin(angle + math.pi / 6),
        ),
    ]
    path = c.beginPath()
    path.moveTo(*points[0])
    path.lineTo(*points[1])
    path.lineTo(*points[2])
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def draw_box(c, x, y, width, height, title, detail, fill, accent):
    c.setFillColor(fill)
    c.setStrokeColor(accent)
    c.setLineWidth(1)
    c.roundRect(x, y, width, height, 7, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x, y, 5, height, 2, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 13, y + height - 17, title)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.2)
    available = width - 26
    words = detail.split()
    lines = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if stringWidth(candidate, "Helvetica", 7.2) <= available:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    for index, line in enumerate(lines[:3]):
        c.drawString(x + 13, y + height - 30 - index * 9, line)


class ArchitectureDiagram(Flowable):
    def __init__(self, width=500, height=300):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        w = self.width
        box_w = 142
        box_h = 54
        center_x = (w - box_w) / 2
        draw_box(
            c,
            center_x,
            236,
            box_w,
            box_h,
            "React browser UI",
            "Login, case creation, upload, status polling",
            BLUE_LIGHT,
            BLUE,
        )
        draw_box(
            c,
            center_x,
            158,
            box_w,
            box_h,
            "FastAPI service",
            "Routes, JWT auth, permissions, rate limits, validation",
            CYAN_LIGHT,
            CYAN,
        )
        draw_arrow(c, w / 2, 236, w / 2, 212)

        stores = [
            (8, "MySQL 8.4", "Cases, documents, status and audit metadata", GREEN_LIGHT, GREEN),
            (179, "Redis 8", "Rate counters and Celery broker/result backend", ORANGE_LIGHT, ORANGE),
            (350, "MinIO", "Private quarantine object storage", PURPLE_LIGHT, PURPLE),
        ]
        for x, title, detail, fill, accent in stores:
            draw_box(c, x, 78, 142, box_h, title, detail, fill, accent)
            draw_arrow(c, w / 2, 158, x + 71, 132, accent, 1.1)

        draw_box(
            c,
            80,
            2,
            155,
            50,
            "Celery worker",
            "Downloads object, scans, processes, updates MySQL",
            BLUE_LIGHT,
            BLUE_DARK,
        )
        draw_box(
            c,
            270,
            2,
            155,
            50,
            "ClamAV + Celery Beat",
            "Malware gate and scheduled retention cleanup",
            RED_LIGHT,
            RED,
        )
        draw_arrow(c, 250, 78, 157, 52, ORANGE, 1.1)
        draw_arrow(c, 421, 78, 205, 52, PURPLE, 1.1)
        draw_arrow(c, 157, 52, 270, 27, BLUE_DARK, 1.1)


class VerticalPipeline(Flowable):
    def __init__(self, nodes, width=500, node_height=42, gap=17):
        super().__init__()
        self.nodes = nodes
        self.width = width
        self.node_height = node_height
        self.gap = gap
        self.height = len(nodes) * node_height + (len(nodes) - 1) * gap

    def draw(self):
        c = self.canv
        box_w = self.width * 0.78
        x = (self.width - box_w) / 2
        y = self.height - self.node_height
        for index, (title, detail, fill, accent) in enumerate(self.nodes):
            draw_box(c, x, y, box_w, self.node_height, title, detail, fill, accent)
            if index < len(self.nodes) - 1:
                next_top = y - self.gap
                draw_arrow(c, self.width / 2, y, self.width / 2, next_top)
            y -= self.node_height + self.gap


class StatusRail(Flowable):
    def __init__(self, width=500, height=90):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        names = ["UPLOADED", "QUARANTINED", "SCANNING", "PROCESSING"]
        node_w = 102
        gap = (self.width - node_w * 4) / 3
        y = 40
        for index, name in enumerate(names):
            x = index * (node_w + gap)
            c.setFillColor(BLUE_LIGHT if index < 2 else CYAN_LIGHT)
            c.setStrokeColor(BLUE if index < 2 else CYAN)
            c.roundRect(x, y, node_w, 30, 6, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + node_w / 2, y + 11, name)
            if index < 3:
                draw_arrow(c, x + node_w, y + 15, x + node_w + gap - 3, y + 15)

        outcomes = [
            (50, "COMPLETED", GREEN_LIGHT, GREEN),
            (200, "MANUAL_REVIEW", ORANGE_LIGHT, ORANGE),
            (365, "FAILED", RED_LIGHT, RED),
        ]
        for x, name, fill, accent in outcomes:
            c.setFillColor(fill)
            c.setStrokeColor(accent)
            c.roundRect(x, 0, 90 if name != "MANUAL_REVIEW" else 110, 25, 6, fill=1, stroke=1)
            c.setFillColor(accent)
            c.setFont("Helvetica-Bold", 7.2)
            c.drawCentredString(
                x + (45 if name != "MANUAL_REVIEW" else 55), 9, name
            )
            draw_arrow(c, self.width - node_w / 2, y, x + (45 if name != "MANUAL_REVIEW" else 55), 25, accent, 0.9)


class ContainerDiagram(Flowable):
    def __init__(self, width=500, height=245):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        c.setFillColor(PANEL)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(14, self.height - 22, "Docker Compose network: grd-document-verf")

        top = [
            (15, "backend", "FastAPI :8003", BLUE_LIGHT, BLUE),
            (177, "celery", "Worker + ClamAV", RED_LIGHT, RED),
            (339, "celery-beat", "Retention scheduler", ORANGE_LIGHT, ORANGE),
        ]
        for x, title, detail, fill, accent in top:
            draw_box(c, x, 142, 145, 55, title, detail, fill, accent)
        lower = [
            (15, "mysql", "Persistent volume", GREEN_LIGHT, GREEN),
            (177, "redis", "AOF persistent queue", ORANGE_LIGHT, ORANGE),
            (339, "minio", "Object data volume", PURPLE_LIGHT, PURPLE),
        ]
        for x, title, detail, fill, accent in lower:
            draw_box(c, x, 42, 145, 55, title, detail, fill, accent)

        draw_arrow(c, 87, 142, 87, 97, GREEN, 1)
        draw_arrow(c, 249, 142, 249, 97, ORANGE, 1)
        draw_arrow(c, 411, 142, 411, 97, PURPLE, 1)
        draw_arrow(c, 177, 170, 160, 170, BLUE, 1)
        draw_arrow(c, 339, 170, 322, 170, ORANGE, 1)
        c.setFont("Helvetica", 7)
        c.setFillColor(MUTED)
        c.drawString(15, 16, "Host ports: API 8003, MySQL 3306, Redis 6379, MinIO 9000, MinIO Console 9001")


class SimpleFlow(Flowable):
    def __init__(self, width=500, height=515):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        nodes = [
            ("1. Select document", "Choose PDF, JPG, JPEG, PNG or enabled TIFF", BLUE_LIGHT, BLUE),
            ("2. Send securely", "Browser calls the authenticated upload API", BLUE_LIGHT, BLUE),
            ("3. Safety checks", "Permission, rate limit, size, extension, signature, pages and duplicate check", CYAN_LIGHT, CYAN),
            ("4. Quarantine", "Random name, SHA-256 hash, MinIO or protected local storage", PURPLE_LIGHT, PURPLE),
            ("5. Background scan", "Redis queues the work; Celery and ClamAV scan the file", ORANGE_LIGHT, ORANGE),
            ("6. Document processing", "Extract and verify document information", CYAN_LIGHT, CYAN),
        ]
        node_h = 52
        gap = 18
        box_w = 410
        x = (self.width - box_w) / 2
        y = self.height - node_h
        last_bottom = 0
        for index, (title, detail, fill, accent) in enumerate(nodes):
            draw_box(c, x, y, box_w, node_h, title, detail, fill, accent)
            last_bottom = y
            if index < len(nodes) - 1:
                next_top = y - gap
                draw_arrow(c, self.width / 2, y, self.width / 2, next_top)
            y -= node_h + gap

        outcome_y = 0
        outcomes = [
            (5, 145, "COMPLETED", "Ready", GREEN_LIGHT, GREEN),
            (177, 145, "MANUAL REVIEW", "A person checks it", ORANGE_LIGHT, ORANGE),
            (349, 145, "FAILED", "Fix or upload again", RED_LIGHT, RED),
        ]
        for x, width, title, detail, fill, accent in outcomes:
            draw_box(c, x, outcome_y, width, 52, title, detail, fill, accent)
            draw_arrow(c, self.width / 2, last_bottom, x + width / 2, 52, accent, 1)


def footer(canvas_obj: canvas.Canvas, doc):
    canvas_obj.saveState()
    page_width, _ = A4
    canvas_obj.setStrokeColor(LINE)
    canvas_obj.line(18 * mm, 13 * mm, page_width - 18 * mm, 13 * mm)
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawString(18 * mm, 8.5 * mm, doc.title)
    canvas_obj.drawRightString(
        page_width - 18 * mm, 8.5 * mm, f"Page {doc.page}"
    )
    canvas_obj.restoreState()


def table(data, widths, header=True):
    formatted = []
    for row_index, row in enumerate(data):
        style = "table_head" if header and row_index == 0 else "table"
        formatted.append([P(str(cell), style) for cell in row])
    result = Table(formatted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
            ]
        )
    result.setStyle(TableStyle(commands))
    return result


def cover_banner(label: str):
    return Table(
        [[P(label, "table_head")]],
        colWidths=[500],
        rowHeights=[24],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )


def build_technical_pdf():
    doc = SimpleDocTemplate(
        str(TECHNICAL_PDF),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="GRD Document Verification - Technical Guide",
        author="GRD Engineering",
    )
    story = []

    story.extend(
        [
            Spacer(1, 24 * mm),
            cover_banner("GRD ENGINEERING / SYSTEM DOCUMENTATION"),
            Spacer(1, 15 * mm),
            P("GRD Document Verification", "cover_title"),
            P("Technical Architecture and Processing Guide", "cover_title"),
            Spacer(1, 7 * mm),
            P(
                "How an API request reaches the route, how authentication and rate limiting work, how Redis and Celery coordinate background jobs, how containers start, and how quarantine storage protects uploaded files.",
                "cover_subtitle",
            ),
            Spacer(1, 14 * mm),
            ArchitectureDiagram(),
            Spacer(1, 8 * mm),
            P(
                "Scope: local development and the Docker Compose deployment in grd-document-verf. Version: 1.0 | 08 August 2026",
                "small",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("1. Technology stack", "h1"),
            P(
                "The application separates browser interaction, synchronous API controls, durable data, object storage, and asynchronous processing. This keeps uploads responsive while expensive security and document checks run outside the request thread.",
            ),
            table(
                [
                    ["Layer", "Technology", "Responsibility"],
                    ["Frontend", "React + TypeScript + Vite", "Dashboard, login, document submission, case display and 3-second status polling."],
                    ["API", "FastAPI + Uvicorn", "HTTP routing, validation, dependencies, authentication, tenant authorization and response models."],
                    ["Data access", "SQLAlchemy + PyMySQL", "ORM models and transactions for MySQL-backed cases and document metadata."],
                    ["Database", "MySQL 8.4", "Durable tenant-scoped cases, document hashes, statuses, storage keys and timestamps."],
                    ["Queue and limits", "Redis 8", "Celery broker/result backend plus fixed-window request counters."],
                    ["Background work", "Celery", "Runs malware scanning and the document-processing pipeline outside the API request."],
                    ["Scheduler", "Celery Beat", "Dispatches the retention cleanup task on a configured interval."],
                    ["Object storage", "MinIO + boto3", "S3-compatible private quarantine storage used by the Compose deployment."],
                    ["File inspection", "PyMuPDF + Pillow", "Validates PDF/image structure, page count and password protection after signature detection."],
                    ["Malware gate", "ClamAV", "Scans the quarantined file before any parser, OCR or verification logic executes."],
                    ["Identity", "JWT + role permissions", "Validates issuer/audience/signature and enforces tenant, role and permission boundaries."],
                    ["Packaging", "Docker Compose", "Starts MySQL, Redis, MinIO, API, worker and scheduler on one private network."],
                ],
                [77, 113, 310],
            ),
            Spacer(1, 8),
            P("Primary runtime configuration", "h2"),
            table(
                [
                    ["Area", "Important settings"],
                    ["Upload", "MAX_UPLOAD_SIZE_BYTES, MAX_DOCUMENT_PAGES, MAX_FILES_PER_CASE, ALLOW_TIFF_UPLOADS"],
                    ["Storage", "STORAGE_BACKEND, MINIO_ENDPOINT, MINIO_BUCKET_NAME, QUARANTINE_STORAGE_PATH"],
                    ["Queue", "REDIS_URL, CELERY_DISPATCH_ENABLED"],
                    ["Retention", "DOCUMENT_EXPIRY_ENABLED, DOCUMENT_RETENTION_DAYS, DOCUMENT_EXPIRY_SWEEP_SECONDS"],
                    ["Security", "SECRET_KEY, JWT_ISSUER, JWT_AUDIENCE, PASSWORD_PROTECTED_PDF_POLICY"],
                ],
                [100, 400],
            ),
            PageBreak(),
        ]
    )

    request_nodes = [
        ("Browser request", "POST /api/v1/documents or POST /api/v1/cases/{case_id}/documents", BLUE_LIGHT, BLUE),
        ("FastAPI router", "app.main mounts api_router at /api/v1; router.py selects the documents or cases endpoint", CYAN_LIGHT, CYAN),
        ("General API rate limit", "Router dependency authenticates JWT and consumes per-user and per-tenant Redis counters", ORANGE_LIGHT, ORANGE),
        ("Upload rate limit", "Upload endpoint applies the stricter upload-specific user and tenant limits", ORANGE_LIGHT, ORANGE),
        ("Permission and tenant context", "require_permission(CASE_SUBMIT) returns tenant_id, user_id and role", BLUE_LIGHT, BLUE_DARK),
        ("Endpoint orchestration", "Create/select case, validate file, detect duplicate, save metadata and enqueue work", PURPLE_LIGHT, PURPLE),
        ("HTTP response", "Return 202 Accepted with document/case status while Celery continues in background", GREEN_LIGHT, GREEN),
    ]
    story.extend(
        [
            P("2. From API hit to route", "h1"),
            P(
                "FastAPI uses dependency injection at both router and endpoint level. The request does not reach upload logic until the token and rate controls have passed.",
            ),
            VerticalPipeline(request_nodes, node_height=40, gap=10),
            Spacer(1, 8),
            P(
                "Important: the changing port shown in Uvicorn logs is the browser's temporary source port. The API still listens on the fixed server address and port, such as 127.0.0.1:8003.",
                "callout",
            ),
            P("Route registration", "h2"),
            P(
                "app/main.py creates FastAPI and mounts app/api/v1/router.py at /api/v1. The router then mounts /auth, /cases, /documents, /verification and /reviews. Protected routers share the general API rate-limit dependency; upload routes add the stricter upload dependency.",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("3. Authentication and rate limiting", "h1"),
            P("Authentication sequence", "h2"),
            table(
                [
                    ["Step", "Control", "Failure response"],
                    ["1", "HTTPBearer reads Authorization: Bearer &lt;token&gt;.", "401 when credentials are absent or invalid."],
                    ["2", "JWT validation checks signature, algorithm, issuer, audience and expiry.", "401 Invalid authentication token."],
                    ["3", "Claims become AuthContext: tenant_id, user_id and role.", "401 when required claims are invalid."],
                    ["4", "require_permission checks ROLE_PERMISSIONS.", "403 Permission denied."],
                    ["5", "Queries include tenant_id so one tenant cannot read another tenant's records.", "404 is returned instead of disclosing existence."],
                ],
                [35, 325, 140],
            ),
            Spacer(1, 8),
            P("How rate limiting is added", "h2"),
            P(
                "rate_limit.py builds fixed-window Redis keys. A Lua script atomically increments the counter, assigns expiry on the first request and returns the current value plus TTL. Atomic execution prevents two simultaneous requests from bypassing the count.",
            ),
            P(
                "Redis key pattern:<br/><font name='Courier'>grd:rate-limit:{scope}:{identity}:{window_id}</font><br/><br/>Scopes are <b>api</b>, <b>upload</b> and <b>login</b>. API/upload identities include both tenant+user and tenant-only counters. Login uses the client IP address.",
                "callout",
            ),
            table(
                [
                    ["Limit", "Default", "Window", "Purpose"],
                    ["General API per user", "120", "60 seconds", "Prevents one user from flooding protected endpoints."],
                    ["General API per tenant", "1000", "60 seconds", "Caps aggregate tenant traffic."],
                    ["Uploads per user", "10", "600 seconds", "Controls expensive file intake."],
                    ["Uploads per tenant", "100", "600 seconds", "Protects storage and processing capacity."],
                    ["Login per IP", "10", "300 seconds", "Reduces password guessing."],
                ],
                [130, 60, 80, 230],
            ),
            Spacer(1, 7),
            P(
                "When exceeded, the API returns 429 with Retry-After and X-RateLimit headers. With fail-open disabled, Redis failure returns 503 instead of silently bypassing the control.",
            ),
            PageBreak(),
        ]
    )

    upload_nodes = [
        ("Authenticate and authorize", "JWT, CASE_SUBMIT permission and tenant ownership", BLUE_LIGHT, BLUE),
        ("Apply request limits", "General API limit plus stricter upload limit", ORANGE_LIGHT, ORANGE),
        ("Stream into staging", "Read in chunks, enforce 25 MB maximum and calculate SHA-256", CYAN_LIGHT, CYAN),
        ("Validate actual content", "Extension allow-list, magic signature, PDF/image integrity and 100-page maximum", CYAN_LIGHT, CYAN),
        ("Create random storage key", "Original name remains metadata; internal object name is UUID-based", PURPLE_LIGHT, PURPLE),
        ("Duplicate check", "Unique tenant_id + SHA-256 prevents an exact duplicate", BLUE_LIGHT, BLUE_DARK),
        ("Quarantine and persist", "Store in MinIO/local quarantine, insert MySQL record and enqueue Celery task", GREEN_LIGHT, GREEN),
    ]
    story.extend(
        [
            P("4. Secure document upload pipeline", "h1"),
            P(
                "The browser-provided MIME type is ignored. The application first checks the filename extension and then verifies the file's byte signature and encoded structure.",
            ),
            VerticalPipeline(upload_nodes, node_height=42, gap=12),
            Spacer(1, 7),
            table(
                [
                    ["Accepted type", "Signature", "Deeper validation"],
                    ["PDF", "%PDF-", "PyMuPDF opens the file, checks page count, corruption and password policy."],
                    ["JPEG", "FF D8 FF", "Pillow decodes all frames and confirms JPEG encoding."],
                    ["PNG", "89 50 4E 47 ...", "Pillow decodes image data and confirms PNG encoding."],
                    ["TIFF", "II* or MM*", "Only allowed when enabled; Pillow checks frames and page count."],
                ],
                [90, 90, 320],
            ),
            Spacer(1, 7),
            P(
                "Successful intake returns 202 Accepted. Validation errors return 400/413/415/422; duplicate content returns 409; unavailable storage or queue returns 503.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("5. Redis jobs, Celery workers and processing status", "h1"),
            P(
                "Redis does not receive the file itself. Redis carries a small task message containing document_id, case_id, storage_key and password_protected. The file remains in quarantine storage.",
                "callout",
            ),
            P("Queue sequence", "h2"),
            table(
                [
                    ["Actor", "Action"],
                    ["FastAPI", "Calls verify_document.delay(...) after the database record is committed."],
                    ["Celery client", "Serializes the task arguments and publishes the message to Redis."],
                    ["Redis", "Holds the queued message until a worker consumes it."],
                    ["Celery worker", "Receives the task and writes SCANNING to MySQL."],
                    ["Storage adapter", "Returns the local path or downloads a temporary MinIO copy."],
                    ["ClamAV", "Scans before any parser, OCR or extraction step."],
                    ["Worker", "Writes PROCESSING, performs the pipeline, then writes a final state."],
                    ["Frontend", "Polls GET /api/v1/cases every 3 seconds and shows the latest MySQL state."],
                ],
                [100, 400],
            ),
            Spacer(1, 13),
            StatusRail(),
            Spacer(1, 8),
            P("Retry behavior", "h2"),
            P(
                "POST /api/v1/documents/{document_id}/retry is tenant-scoped and allowed only for FAILED, non-infected documents whose quarantine object still exists. It locks the database row, resets the document to QUARANTINED/QUEUED, enqueues a new task and restores the previous state if Redis dispatch fails.",
            ),
            P("Why asynchronous processing is used", "h2"),
            P(
                "ClamAV, OCR and document analysis can be slow. Moving them to Celery keeps API response time short, supports retries, isolates failures and lets worker capacity scale independently from web traffic.",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("6. How the containers start", "h1"),
            P(
                "docker compose up -d --build creates the private Compose network and persistent volumes, starts infrastructure, waits for health checks, then starts application services in dependency order.",
            ),
            ContainerDiagram(),
            Spacer(1, 8),
            table(
                [
                    ["Startup order", "What happens"],
                    ["1. MySQL", "Loads the grd-mysql-data external volume and becomes healthy after mysqladmin ping succeeds."],
                    ["2. Redis", "Starts with append-only persistence and becomes healthy after redis-cli ping."],
                    ["3. MinIO", "Mounts grd-minio-data, exposes the S3 API/console and passes the live health endpoint."],
                    ["4. Backend", "Runs Uvicorn. Startup creates missing tables and applies the additive document status/storage schema update."],
                    ["5. Celery", "Updates ClamAV definitions, starts worker processes and connects to Redis."],
                    ["6. Celery Beat", "Loads the hourly retention schedule and publishes cleanup tasks to Redis."],
                ],
                [95, 405],
            ),
            Spacer(1, 8),
            P("Useful commands", "h2"),
            P(
                "docker compose up -d --build<br/>docker compose ps<br/>docker compose logs -f backend celery celery-beat minio<br/>docker compose down",
                "code",
            ),
            P(
                "Do not use docker compose down -v unless the managed volumes are intentionally being removed. MySQL and MinIO data require separate production backups.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("7. Storage architecture and document expiry", "h1"),
            P("Storage adapter", "h2"),
            P(
                "storage.py exposes one interface for local and MinIO operation. Upload validation always uses a temporary local staging file because PyMuPDF, Pillow and ClamAV operate on file paths. After validation, local mode moves the file into the protected quarantine directory; MinIO mode uploads the file and deletes staging.",
            ),
            table(
                [
                    ["Operation", "Local backend", "MinIO backend"],
                    ["Save", "Atomic move into storage/quarantine", "boto3 upload_file into grd-quarantine"],
                    ["Existence check", "Path.is_file()", "S3 HeadObject"],
                    ["Worker access", "Use protected local path", "Download to UUID temporary file"],
                    ["Cleanup", "Path.unlink()", "S3 DeleteObject"],
                    ["Object name", "Random UUID + canonical extension", "Same random key; original filename is metadata only"],
                ],
                [95, 190, 215],
            ),
            Spacer(1, 9),
            P("Retention workflow", "h2"),
            VerticalPipeline(
                [
                    ("Celery Beat interval", "Default: publish cleanup every 3600 seconds", ORANGE_LIGHT, ORANGE),
                    ("Select expired records", "created_at older than DOCUMENT_RETENTION_DAYS and storage_deleted_at is null", BLUE_LIGHT, BLUE),
                    ("Delete file content", "Use the configured local or MinIO storage adapter", PURPLE_LIGHT, PURPLE),
                    ("Retain audit metadata", "Set storage_deleted_at; keep filename, hash, statuses and ownership in MySQL", GREEN_LIGHT, GREEN),
                ],
                node_height=44,
                gap=15,
            ),
            Spacer(1, 7),
            P(
                "The dashboard displays Storage: Expired and suppresses retry when the quarantine object has been deleted. A stuck non-final document that reaches retention is safely moved to FAILED.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("8. Code map and operational checklist", "h1"),
            table(
                [
                    ["File", "Responsibility"],
                    ["backend/app/main.py", "FastAPI creation, startup database initialization, CORS and API mounting."],
                    ["backend/app/api/v1/router.py", "Connects URL prefixes to endpoint modules and general API limits."],
                    ["backend/app/api/v1/endpoints/cases.py", "Case CRUD, secure case upload orchestration and status observations."],
                    ["backend/app/api/v1/endpoints/documents.py", "Direct upload, read/status, retry and deletion endpoints."],
                    ["backend/app/services/rate_limit.py", "Redis Lua counters, limit decisions and response headers."],
                    ["backend/app/services/storage.py", "Signature inspection, SHA-256, local/MinIO storage and temporary materialization."],
                    ["backend/app/services/antivirus.py", "ClamAV command execution and fail-closed scan outcome."],
                    ["backend/app/workers/tasks.py", "Task dispatch, processing stages, malware gate and expiry task."],
                    ["backend/app/workers/celery_app.py", "Redis broker/result configuration and Beat schedule."],
                    ["backend/app/db/session.py", "Engine/session creation, create_all and existing MySQL compatibility update."],
                    ["docker-compose.yml", "All containers, health checks, networks, ports, volumes and environment overrides."],
                    ["frontend/src/App.tsx", "Upload form, case polling, observations, retry and storage availability display."],
                ],
                [190, 310],
            ),
            Spacer(1, 9),
            P("Pre-production checklist", "h2"),
            table(
                [
                    ["Check", "Required result"],
                    ["Secrets", "Replace JWT and MinIO development credentials; use a secret manager."],
                    ["Transport", "Use HTTPS for API and MinIO endpoints."],
                    ["Object storage", "Use redundant/managed MinIO and verified backups; migrate any legacy local objects."],
                    ["Database", "Back up MySQL and confirm the status/storage schema update completed."],
                    ["Malware", "Confirm fresh ClamAV signatures and verify EICAR test rejection."],
                    ["Queue", "Monitor Redis memory/persistence, worker failures and task backlog."],
                    ["Retention", "Confirm the legal retention period and monitor cleanup errors."],
                    ["End-to-end", "Upload a test file and observe QUARANTINED, SCANNING, PROCESSING and final status."],
                ],
                [105, 395],
            ),
            Spacer(1, 10),
            P(
                "System rule: MySQL stores the authoritative business state, MinIO stores file bytes, Redis coordinates short-lived counters and tasks, and Celery performs background work. The file itself is never sent through Redis.",
                "callout",
            ),
        ]
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def build_flow_pdf():
    doc = SimpleDocTemplate(
        str(FLOW_PDF),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title="GRD Document Verification - Simple Flowchart",
        author="GRD Engineering",
    )
    story = [
        P("Document Verification Flow", "simple_title"),
        P(
            "A simple view of what happens after a user submits a document.",
            "cover_subtitle",
        ),
        Spacer(1, 8),
        SimpleFlow(),
        Spacer(1, 6),
        P(
            "The upload page returns quickly after the document is safely stored and queued. The dashboard then refreshes the status while background processing continues.",
            "callout",
        ),
        PageBreak(),
        P("Status and exception guide", "simple_title"),
        Spacer(1, 5),
        StatusRail(),
        Spacer(1, 12),
        table(
            [
                ["Status", "Meaning for the user"],
                ["UPLOADED", "The API received the upload request."],
                ["QUARANTINED", "The file passed intake checks and is stored away from normal processing."],
                ["SCANNING", "The malware scanner is checking the quarantined file."],
                ["PROCESSING", "Document information is being extracted and verified."],
                ["COMPLETED", "Automated processing finished successfully."],
                ["MANUAL_REVIEW", "A reviewer needs to inspect the document or provide a decision."],
                ["FAILED", "Processing stopped safely. Retry may be available if the file is not infected and has not expired."],
            ],
            [120, 380],
        ),
        Spacer(1, 12),
        P("Common exception paths", "h2"),
        table(
            [
                ["Situation", "Result"],
                ["Wrong extension or signature", "Upload rejected before storage."],
                ["File larger than 25 MB", "Upload rejected with a size-limit response."],
                ["More than 100 pages", "Upload rejected before background processing."],
                ["Exact duplicate", "Upload rejected and existing document ID returned."],
                ["Malware detected", "Document marked FAILED; retry is blocked."],
                ["Password-protected PDF", "Rejected or sent to MANUAL_REVIEW according to policy."],
                ["Redis or storage unavailable", "API fails safely with service unavailable instead of losing work."],
                ["Retention period reached", "File bytes are deleted; audit metadata remains and storage shows Expired."],
            ],
            [180, 320],
        ),
        Spacer(1, 12),
        KeepTogether(
            [
                P("Where each item lives", "h2"),
                P(
                    "- MySQL: case and document records<br/>- MinIO/local quarantine: uploaded file bytes<br/>- Redis: rate counters and task messages<br/>- Celery: background processing<br/>- ClamAV: malware scan",
                    "callout",
                ),
            ]
        ),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    build_technical_pdf()
    build_flow_pdf()
    print(TECHNICAL_PDF)
    print(FLOW_PDF)
