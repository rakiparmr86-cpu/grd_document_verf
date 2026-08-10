from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from build_documentation import (
    ArchitectureDiagram,
    BLUE,
    BLUE_LIGHT,
    CYAN,
    CYAN_LIGHT,
    GREEN,
    GREEN_LIGHT,
    INK,
    LINE,
    MUTED,
    NAVY,
    ORANGE,
    ORANGE_LIGHT,
    P,
    PANEL,
    PURPLE,
    PURPLE_LIGHT,
    RED,
    RED_LIGHT,
    STYLES,
    StatusRail,
    VerticalPipeline,
    WHITE,
    cover_banner,
    footer,
    table,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf"
PDF_PATH = OUTPUT / "GRD_Technical_Issue_Analysis_and_Resolution_Handbook.pdf"


def command_block(*lines: str) -> Paragraph:
    return P("<br/>".join(escape(line) for line in lines), "code")


def issue_summary(symptom: str, root_cause: str, resolution: str, validation: str):
    data = [
        [P("Observed symptom", "table_head"), P(symptom, "table")],
        [P("Root cause", "table_head"), P(root_cause, "table")],
        [P("Resolution", "table_head"), P(resolution, "table")],
        [P("Validation", "table_head"), P(validation, "table")],
    ]
    result = Table(data, colWidths=[105, 395])
    result.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), NAVY),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("ROWBACKGROUNDS", (1, 0), (1, -1), [WHITE, PANEL]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return result


def scenario(title: str, text: str, color=BLUE, fill=BLUE_LIGHT):
    label = Table(
        [[P(title, "table_head")]],
        colWidths=[500],
        rowHeights=[22],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        ),
    )
    body = Table(
        [[P(text, "body")]],
        colWidths=[500],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.8, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        ),
    )
    return [label, body]


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title="GRD Technical Issue Analysis and Resolution Handbook",
        author="GRD Engineering",
    )
    story = []

    story.extend(
        [
            Spacer(1, 21 * mm),
            cover_banner("GRD ENGINEERING / TROUBLESHOOTING HANDBOOK"),
            Spacer(1, 14 * mm),
            P("GRD Document Verification", "cover_title"),
            P("Technical Issue Analysis and Resolution Handbook", "cover_title"),
            Spacer(1, 7 * mm),
            P(
                "A consolidated analysis of the setup, runtime, upload, database, queue, storage, frontend and developer-tool issues encountered during implementation. Each section records the symptom, root cause, applied resolution, example scenario and useful command sequence.",
                "cover_subtitle",
            ),
            Spacer(1, 14 * mm),
            ArchitectureDiagram(),
            Spacer(1, 7 * mm),
            P(
                "Security note: commands use placeholders. Real JWT secrets, database passwords and account data are intentionally not reproduced. Version 1.0 | 08 August 2026",
                "small",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("1. Issue register", "h1"),
            P(
                "The register below provides a quick index. Detailed explanations and commands follow on later pages.",
            ),
            table(
                [
                    ["ID", "Issue", "Primary cause", "Resolution status"],
                    ["I-01", "No module named pydantic", "Wrong Python interpreter / individual file execution", "Resolved with project virtual environment and module launch"],
                    ["I-02", "Virtual environment would not activate", "Used cd on a PowerShell script", "Resolved with the call operator"],
                    ["I-03", "VS Code F5 launched auth.py", "Incorrect debug target and Python 3.14", "Resolved with launch.json for Uvicorn and the backend venv"],
                    ["I-04", "Uvicorn IndentationError", "Unexpected indentation in documents.py", "Source corrected and compile/test checks added"],
                    ["I-05", "Redis/Celery purpose unclear", "File storage and task messaging were confused", "Architecture separated file bytes from queue messages"],
                    ["I-06", "MySQL port not published", "Existing container had no host mapping", "Container recreated with 127.0.0.1:3306:3306 and named volume"],
                    ["I-07", "Where to put database password", "System password confused with DB credential", "DATABASE_URL documented and credentials aligned"],
                    ["I-08", "Submission failed", "Backend/database/queue dependencies not consistently available", "Health-first diagnosis and error detail handling"],
                    ["I-09", "Password-protected PDF rejected", "Policy loaded as reject or process not restarted", "Policy changed to review and services restarted"],
                    ["I-10", "Document observations not visible", "UI showed cases without processing detail", "Database-backed observations displayed inside case documents"],
                    ["I-11", "Repeated GET requests and changing ports", "Frontend polling and normal client ephemeral ports", "Explained and retained as expected behavior"],
                    ["I-12", "Dashboard changes in wrong directory", "Edits targeted a different frontend", "Work restricted to grd-document-verf/frontend/src"],
                ],
                [38, 140, 190, 132],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("1. Issue register - continued", "h1"),
            table(
                [
                    ["ID", "Issue", "Primary cause", "Resolution status"],
                    ["I-13", "Base dashboard must remain", "Feature page risked replacing existing UI", "Verification functions kept under More / command centre"],
                    ["I-14", "ClamAV container communication", "Code expected local clamscan executable", "ClamAV installed inside Celery worker image"],
                    ["I-15", "No rate limits", "Expensive endpoints were unprotected", "Redis-based user/tenant/login/upload limits added"],
                    ["I-16", "No processing retry", "Failed work required re-upload", "Tenant-scoped retry endpoint and UI action added"],
                    ["I-17", "Local quarantine not production-ready", "API and worker required shared local disk", "Local/MinIO storage adapter introduced"],
                    ["I-18", "No automatic expiry", "Quarantine content could remain indefinitely", "Celery Beat retention cleanup added"],
                    ["I-19", "Statuses were too technical", "Legacy OCR/extraction status names", "Clear public lifecycle stages added"],
                    ["I-20", "Git bad revision refs/heads/main", "Repository had no first commit/main history", "Initial commit and branch setup documented"],
                    ["I-21", "Open authentication link in Firefox", "VS Code external browser not configured", "Workspace browser preference set to Firefox"],
                    ["I-22", "Access MySQL data/procedures in container", "Container filesystem confused with database persistence", "docker exec, SQL views/procedures, volumes and backups documented"],
                    ["I-23", "Unclear file-analysis libraries", "Python logic and external tools were conflated", "PyMuPDF, Pillow and ClamAV responsibilities documented"],
                    ["I-24", "Multi-service startup was manual", "MySQL, Redis, worker and API started separately", "Docker Compose orchestration added"],
                ],
                [38, 140, 190, 132],
            ),
            Spacer(1, 10),
            P(
                "Outcome: automated backend tests, Python checks, frontend build, Compose validation and rendered documentation checks now provide repeatable evidence instead of relying only on manual observation.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("2. Python environment and VS Code execution", "h1"),
            P("I-01: ModuleNotFoundError for pydantic", "h2"),
            issue_summary(
                "Running a schema file directly produced: No module named 'pydantic'.",
                "VS Code used a system Python installation instead of backend/.venv. Running app files directly also bypassed the application package startup path.",
                "Select backend/.venv/Scripts/python.exe and launch Uvicorn as a module. Install requirements only inside that environment.",
                "python -c imports pydantic; Uvicorn imports app.main successfully.",
            ),
            Spacer(1, 8),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\backend",
                r"& .\.venv\Scripts\Activate.ps1",
                "python -m pip install -r requirements.txt",
                "python -c \"import pydantic; print(pydantic.__version__)\"",
                "python -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload",
            ),
            P("I-02: activation command used with cd", "h2"),
            P(
                "PowerShell <b>cd</b> changes directories; it does not execute scripts. From the backend directory, run the activation script with <b>&amp;</b> or dot-source it. If already inside .venv, do not add another .venv path segment.",
            ),
            command_block(
                r"# Correct from backend",
                r"& .\.venv\Scripts\Activate.ps1",
                r"# Correct while already inside backend\.venv",
                r"& .\Scripts\Activate.ps1",
            ),
            P("I-03: F5 launched auth.py instead of the application", "h2"),
            P(
                "The working launch configuration uses module=uvicorn, cwd=backend, envFile=backend/.env and the project virtual-environment interpreter. Individual endpoint modules are imported by FastAPI; they are not standalone programs.",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("3. API startup and Python source errors", "h1"),
            P("I-04: IndentationError in documents.py", "h2"),
            issue_summary(
                "Uvicorn reloader started, but the child process stopped at documents.py line 129 with unexpected indent.",
                "Python parses every imported endpoint before the server can accept traffic. One extra indentation level made the module invalid.",
                "Correct the function indentation, compile the complete app tree, then restart the Uvicorn module instead of the individual file.",
                "compileall passes and /health returns status ok.",
            ),
            Spacer(1, 8),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\backend",
                r"& .\.venv\Scripts\Activate.ps1",
                "python -m compileall -q app",
                "python -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload",
                "curl.exe http://127.0.0.1:8003/health",
            ),
            Spacer(1, 8),
            *scenario(
                "Example scenario",
                "A developer presses F5 and sees 'Uvicorn running' followed by a traceback. The first line is only the reloader process. The final traceback line is decisive: IndentationError at documents.py. Fix that source error, save the file and let the reloader import app.main again.",
                RED,
                RED_LIGHT,
            ),
            Spacer(1, 9),
            P("Recommended diagnostic order", "h2"),
            VerticalPipeline(
                [
                    ("Read the final traceback line", "Identify syntax, import, configuration or connection failure", RED_LIGHT, RED),
                    ("Compile before running", "python -m compileall -q app", ORANGE_LIGHT, ORANGE),
                    ("Import the application module", "python -c \"from app.main import app\"", BLUE_LIGHT, BLUE),
                    ("Start Uvicorn", "Run app.main:app from the backend working directory", CYAN_LIGHT, CYAN),
                    ("Check /health", "Only then test authenticated API endpoints", GREEN_LIGHT, GREEN),
                ],
                node_height=43,
                gap=14,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("4. Correct local startup order", "h1"),
            P(
                "The local workflow uses separate terminals so that the API and worker remain visible. Infrastructure must be healthy before work is submitted.",
            ),
            table(
                [
                    ["Order", "Component", "Command / result"],
                    ["1", "Docker Desktop", "Docker engine must be running."],
                    ["2", "MySQL", "docker start grd-mysql; port 3306 must be published."],
                    ["3", "Redis", "docker start grd-redis; redis-cli ping returns PONG."],
                    ["4", "Database schema", "Backend startup creates tables and applies additive compatibility updates."],
                    ["5", "FastAPI", "Uvicorn listens on fixed port 8003."],
                    ["6", "Celery worker", "Worker connects to redis://localhost:6379/0 and reports ready."],
                    ["7", "Frontend", "Vite listens on 5176 and proxies /api to 8003."],
                ],
                [45, 120, 335],
            ),
            Spacer(1, 9),
            P("Infrastructure commands", "h2"),
            command_block(
                "docker start grd-mysql",
                "docker start grd-redis",
                "docker exec grd-redis redis-cli ping",
                "docker port grd-mysql",
                "docker ps --format \"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\"",
            ),
            P("API terminal", "h2"),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\backend",
                r"& .\.venv\Scripts\Activate.ps1",
                "python -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload",
            ),
            P("Worker terminal", "h2"),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\backend",
                r"& .\.venv\Scripts\Activate.ps1",
                "python -m celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo",
            ),
            P("Frontend terminal", "h2"),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\frontend",
                "npm run dev",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("5. MySQL container, credentials and persistence", "h1"),
            P("I-06: no public port 3306", "h2"),
            issue_summary(
                "docker port grd-mysql 3306 reported that no public port was published.",
                "Docker port mappings are fixed when a container is created. docker start cannot add a missing mapping.",
                "Recreate the container with 127.0.0.1:3306:3306 and mount the named grd-mysql-data volume.",
                "docker port shows 127.0.0.1:3306 and the API connects using localhost:3306.",
            ),
            Spacer(1, 7),
            command_block(
                "docker run -d --name grd-mysql -p 127.0.0.1:3306:3306 `",
                "  -e MYSQL_DATABASE=grd_document_verf `",
                "  -e MYSQL_USER=grd `",
                "  -e MYSQL_PASSWORD=<DB_PASSWORD> `",
                "  -e MYSQL_ROOT_PASSWORD=<ROOT_PASSWORD> `",
                "  -v grd-mysql-data:/var/lib/mysql mysql:8.4",
            ),
            P("I-07: which password belongs in .env", "h2"),
            P(
                "DATABASE_URL uses the MySQL account password, not the Windows password. Its format is <b>mysql+pymysql://user:password@host:port/database</b>. URL-encode special characters. Never commit the active .env file.",
            ),
            command_block(
                "DATABASE_URL=mysql+pymysql://grd:<DB_PASSWORD>@localhost:3306/grd_document_verf",
                "REDIS_URL=redis://localhost:6379/0",
                "CELERY_DISPATCH_ENABLED=true",
            ),
            P("Initialization warning", "h2"),
            P(
                "MySQL environment variables are applied only when /var/lib/mysql is initialized. Reusing an existing volume preserves old users/passwords. Changing Compose variables later does not rewrite them; use ALTER USER or intentionally initialize a new volume after a verified backup.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("6. MySQL data, views, procedures and backups", "h1"),
            P("I-22: database exists inside a container", "h2"),
            P(
                "The MySQL server process runs in the container, but durable table data lives in the named Docker volume. SQL objects such as views and stored procedures live inside the database schema and are created with normal SQL commands.",
            ),
            P("Open MySQL and inspect application data", "h2"),
            command_block(
                "docker exec -it grd-mysql mysql -ugrd -p grd_document_verf",
                "SHOW TABLES;",
                "SELECT id, filename, status, malware_scan_status FROM documents ORDER BY created_at DESC;",
                "SHOW CREATE TABLE documents\\G",
            ),
            P("Example view", "h2"),
            command_block(
                "CREATE OR REPLACE VIEW vw_document_processing_status AS",
                "SELECT tenant_id, case_id, id AS document_id, filename, status,",
                "       malware_scan_status, storage_deleted_at, created_at",
                "FROM documents;",
                "SELECT * FROM vw_document_processing_status;",
            ),
            P("Example stored procedure", "h2"),
            command_block(
                "DELIMITER //",
                "CREATE PROCEDURE GetCaseDocuments(IN p_case_id CHAR(36))",
                "BEGIN",
                "  SELECT id, filename, status, malware_scan_status",
                "  FROM documents WHERE case_id = p_case_id ORDER BY created_at;",
                "END //",
                "DELIMITER ;",
                "CALL GetCaseDocuments('<CASE_UUID>');",
            ),
            P("Backup and restore", "h2"),
            command_block(
                "New-Item -ItemType Directory -Force .\\backups",
                "docker exec grd-mysql sh -c `",
                "  'exec mysqldump -ugrd -p\"$MYSQL_PASSWORD\" grd_document_verf' `",
                "  > .\\backups\\grd.sql",
                "Get-Content .\\backups\\grd.sql | docker exec -i grd-mysql sh -c `",
                "  'exec mysql -ugrd -p\"$MYSQL_PASSWORD\" grd_document_verf'",
            ),
            Spacer(1, 8),
            P(
                "Production practice: use managed backups or scheduled dumps, monitor restore tests, retain database and MinIO backups separately, and never treat the container writable layer as durable storage.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("7. Upload failure diagnosis", "h1"),
            P("I-08: browser displayed Submission failed", "h2"),
            issue_summary(
                "The upload form accepted a file but displayed a generic submission failure.",
                "A frontend message can represent API unavailability, authentication failure, database connection error, validation rejection, duplicate content, Redis queue failure or quarantine storage failure.",
                "Return API detail to the UI, then diagnose dependencies in order: health, logs, authentication, database, Redis, MinIO/local storage and file validation.",
                "A valid file returns 202 Accepted; cases/status endpoints return 200; the worker advances the stored status.",
            ),
            Spacer(1, 8),
            P("Diagnostic commands", "h2"),
            command_block(
                "curl.exe http://127.0.0.1:8003/health",
                "docker compose ps",
                "docker compose logs --tail=200 backend mysql redis minio celery",
                "docker exec grd-redis redis-cli ping",
                "docker exec -it grd-mysql mysql -ugrd -p -e \"SELECT 1\" grd_document_verf",
            ),
            Spacer(1, 8),
            *scenario(
                "Example scenario: queue unavailable",
                "The API successfully validates and stores statement.pdf, commits the document row, then cannot publish the Celery message because Redis is stopped. The secure upload transaction removes the newly created record and quarantine object and returns 503. After Redis returns PONG, resubmit the document.",
                ORANGE,
                ORANGE_LIGHT,
            ),
            Spacer(1, 8),
            *scenario(
                "Example scenario: duplicate file",
                "The same tenant uploads identical bytes under a different filename. The SHA-256 value matches the existing row, so the new quarantine object is deleted and the API returns 409 with the existing document ID. Renaming a file does not bypass duplicate detection.",
                PURPLE,
                PURPLE_LIGHT,
            ),
            Spacer(1, 8),
            P(
                "Status codes are useful evidence: 401 token problem, 403 permission problem, 409 duplicate/state conflict, 413 size/page limit, 415 file type mismatch, 422 corrupt/invalid document, 429 rate limit and 503 dependency unavailable.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("8. Password protection, observations and analysis libraries", "h1"),
            P("I-09: password-protected PDFs were still rejected", "h2"),
            issue_summary(
                "Bank statements continued to show Password-protected PDFs are not accepted after the setting was changed.",
                "The active process had already loaded settings, the wrong .env was edited, or the policy value remained reject.",
                "Set PASSWORD_PROTECTED_PDF_POLICY=review in backend/.env and restart both API and worker. Review does not decrypt the file; it stores and scans the encrypted PDF and routes it to MANUAL_REVIEW.",
                "A protected PDF returns 202 and eventually shows MANUAL_REVIEW rather than an intake rejection.",
            ),
            Spacer(1, 7),
            command_block(
                "PASSWORD_PROTECTED_PDF_POLICY=review",
                "docker compose up -d --force-recreate backend celery",
                "docker compose logs -f backend celery",
            ),
            P("I-10: observations were not shown", "h2"),
            P(
                "Document responses now build observations from the database record: detected type, size, page count, password state, malware outcome, processing status and storage expiry. The case dashboard expands each document and displays those observations.",
            ),
            P("I-23: what actually checks the document", "h2"),
            table(
                [
                    ["Component", "Checks performed"],
                    ["Pure Python logic", "Extension allow-list, chunked size limit, random filename, SHA-256 and duplicate lookup."],
                    ["Magic signature logic", "PDF, JPEG, PNG and TIFF header bytes; browser MIME is ignored."],
                    ["PyMuPDF (fitz)", "PDF open/integrity, pages and password requirement."],
                    ["Pillow", "JPEG/PNG/TIFF decoding, encoded format and frame/page count."],
                    ["ClamAV", "Malware scan before parser/OCR/verification processing."],
                    ["SQLAlchemy/MySQL", "Unique tenant hash, statuses and durable audit metadata."],
                ],
                [130, 370],
            ),
            Spacer(1, 8),
            P(
                "Therefore the scan is not 'Python without libraries'. Python orchestrates the controls, while specialized libraries and the ClamAV executable perform file-format and malware analysis.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("9. Redis, Celery and the background job", "h1"),
            P("I-05: where Redis is called to upload the CV", "h2"),
            issue_summary(
                "No code appeared to upload the CV/PDF into Redis.",
                "Redis is intentionally not file storage. It stores small Celery task messages and rate-limit counters. File bytes belong in MinIO or local quarantine.",
                "After storage and database commit, enqueue_document_processing calls verify_document.delay with IDs, storage_key and password flag. Celery publishes that message to Redis.",
                "Worker logs show the received verify_document task and MySQL status changes from SCANNING to PROCESSING to a final state.",
            ),
            Spacer(1, 8),
            table(
                [
                    ["System", "What it stores", "Retention"],
                    ["MySQL", "Cases, documents, hashes, ownership and statuses", "Durable business data"],
                    ["MinIO/local", "Actual PDF/image bytes", "Configured document retention"],
                    ["Redis", "Task messages, results and rate counters", "Short-lived/queue data"],
                    ["Celery", "No durable data itself; executes work", "Worker process lifetime"],
                ],
                [90, 260, 150],
            ),
            Spacer(1, 9),
            P("Worker flow", "h2"),
            VerticalPipeline(
                [
                    ("API publishes task", "document_id, case_id, storage_key, password_protected", BLUE_LIGHT, BLUE),
                    ("Redis holds message", "Worker can consume when ready", ORANGE_LIGHT, ORANGE),
                    ("Celery sets SCANNING", "Materialize MinIO/local object and call ClamAV", CYAN_LIGHT, CYAN),
                    ("Celery sets PROCESSING", "Run the document verification pipeline", PURPLE_LIGHT, PURPLE),
                    ("Write final status", "COMPLETED, MANUAL_REVIEW or FAILED in MySQL", GREEN_LIGHT, GREEN),
                ],
                node_height=44,
                gap=15,
            ),
            Spacer(1, 8),
            command_block(
                "docker exec grd-redis redis-cli ping",
                "docker exec grd-redis redis-cli --scan --pattern \"grd:rate-limit:*\"",
                "docker compose logs -f celery redis",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("10. Repeated requests and changing client ports", "h1"),
            P("I-11: repeated GET /api/v1/cases", "h2"),
            issue_summary(
                "Uvicorn logged GET /api/v1/cases repeatedly, each line showing a different client port.",
                "The Cases page polls every 3 seconds for updated Celery status. The operating system selects an ephemeral source port for browser connections; this is separate from the API listening port.",
                "No server-port change is required. Keep API target fixed at localhost:8003. Adjust or replace polling only if load requires WebSocket/SSE or a longer interval.",
                "Every request still reaches 127.0.0.1:8003 and receives a normal 200 response.",
            ),
            Spacer(1, 10),
            table(
                [
                    ["Log part", "Meaning"],
                    ["127.0.0.1:52473", "Browser/client address plus temporary source port."],
                    ["POST /api/v1/documents", "HTTP method and fixed route."],
                    ["HTTP/1.1 202 Accepted", "Server response sent through the same connection."],
                    ["Server 127.0.0.1:8003", "Fixed Uvicorn listening address and port; often omitted from the log line."],
                ],
                [145, 355],
            ),
            Spacer(1, 12),
            *scenario(
                "Example network scenario",
                "The browser opens a TCP connection from 127.0.0.1:52473 to 127.0.0.1:8003. The API sends 202 back through that connection. A later poll may use 127.0.0.1:52482, but its destination is still 127.0.0.1:8003. The temporary port lets Windows match response packets to the correct browser socket.",
                CYAN,
                CYAN_LIGHT,
            ),
            Spacer(1, 10),
            P("Frontend proxy", "h2"),
            command_block(
                "Vite browser URL: http://localhost:5176",
                "Frontend request: /api/v1/cases",
                "Vite proxy target: http://localhost:8003",
                "FastAPI route: /api/v1/cases",
            ),
            P(
                "Repeated successful polling is expected. Repeated 401, 429, 500 or 503 responses require investigation.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("11. Frontend directory and dashboard preservation", "h1"),
            P("I-12 and I-13", "h2"),
            issue_summary(
                "Verification UI changes appeared in the wrong project or replaced the intended dashboard layout.",
                "The machine contained multiple dashboard/front-end directories, and the desired integration boundary was the More menu inside grd-document-verf/frontend/src.",
                "Restrict edits to the specified frontend source, preserve the base dashboard and expose verification features under More / Verification Command Centre and its case/upload pages.",
                "npm run build passes and existing dashboard sections remain available.",
            ),
            Spacer(1, 9),
            P("Working directory checks", "h2"),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\frontend",
                "Get-Location",
                "Get-ChildItem .\\src",
                "npm run build",
                "npm run dev",
            ),
            Spacer(1, 9),
            P("Frontend behavior now covered", "h2"),
            table(
                [
                    ["Feature", "Behavior"],
                    ["Submit document", "Calls POST /api/v1/documents and shows API detail on failure."],
                    ["Cases", "Polls API, expands documents and displays observations."],
                    ["Retry", "Shown only for eligible FAILED, non-infected, non-expired documents."],
                    ["Storage", "Displays Available or Expired."],
                    ["Statuses", "Shows UPLOADED, QUARANTINED, SCANNING, PROCESSING and final states."],
                    ["Navigation", "Verification features remain under the More experience instead of removing the base dashboard."],
                ],
                [120, 380],
            ),
            Spacer(1, 10),
            *scenario(
                "Example UI scenario",
                "A verification executive uploads a bank statement. The page returns immediately, then Cases shows QUARANTINED, SCANNING and PROCESSING as the worker commits each stage. If the PDF is password protected under review policy, the final badge is MANUAL REVIEW and the observation explains why.",
                BLUE,
                BLUE_LIGHT,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("12. Docker Compose, ClamAV and MinIO", "h1"),
            P("I-14 and I-24: multi-service startup", "h2"),
            issue_summary(
                "A separate ClamAV container was considered, but antivirus.py executed a local clamscan command. Services also required several manual terminals.",
                "A ClamAV daemon container would require a network protocol client. The existing implementation was command-based and expected the executable beside the Celery process.",
                "Install ClamAV and freshclam in the Celery worker image. Compose starts MySQL, Redis, MinIO, backend, Celery and Celery Beat with dependencies and health checks.",
                "docker compose config passes; worker lists verify_document and expire_quarantined_documents tasks.",
            ),
            Spacer(1, 7),
            P("I-17: what MINIO_ENDPOINT means", "h2"),
            P(
                "MINIO_ENDPOINT is the base URL used by boto3 for the S3-compatible API. Inside Compose it is <b>http://minio:9000</b> because service names resolve on the private network. From Windows it is <b>http://localhost:9000</b>. The web console uses port 9001.",
            ),
            table(
                [
                    ["Mode", "Storage setting", "Endpoint"],
                    ["Local F5", "STORAGE_BACKEND=local", "Protected storage/quarantine folder"],
                    ["Compose", "STORAGE_BACKEND=minio", "http://minio:9000"],
                    ["Host tools", "MinIO S3/console", "http://localhost:9000 / http://localhost:9001"],
                    ["Production", "STORAGE_BACKEND=minio", "TLS endpoint for managed/redundant MinIO"],
                ],
                [90, 165, 245],
            ),
            Spacer(1, 8),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf",
                "docker compose up -d --build",
                "docker compose ps",
                "docker compose logs -f backend celery celery-beat minio",
                "docker compose down",
            ),
            P(
                "Do not use docker compose down -v unless volume removal is intentional. The bundled MinIO is suitable for local integration; production requires TLS, changed credentials, redundancy and backups.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("13. Rate limiting and retry processing", "h1"),
            P("I-15: rate limiting", "h2"),
            issue_summary(
                "Upload and API endpoints could be called repeatedly without an application limit.",
                "Authentication alone verifies identity but does not control request volume or expensive file-processing demand.",
                "Redis Lua counters now enforce general API, upload and login limits. API/upload limits use user and tenant identities; login uses client IP. Fail-closed mode returns 503 if Redis is unavailable.",
                "Exceeded limits return 429 plus Retry-After and X-RateLimit headers.",
            ),
            Spacer(1, 8),
            P("Default policy", "h2"),
            table(
                [
                    ["Scope", "User/IP", "Tenant", "Window"],
                    ["General API", "120", "1000", "60 seconds"],
                    ["Upload", "10", "100", "600 seconds"],
                    ["Login", "10 per IP", "Not applicable", "300 seconds"],
                ],
                [145, 105, 105, 145],
            ),
            Spacer(1, 8),
            P("I-16: retry processing", "h2"),
            P(
                "POST /api/v1/documents/{document_id}/retry is permitted only for the owning tenant and FAILED documents. INFECTED and expired documents cannot retry. A database row lock prevents concurrent retries. If queue dispatch fails, the previous document and case state is restored.",
            ),
            StatusRail(),
            Spacer(1, 7),
            *scenario(
                "Example retry scenario",
                "ClamAV was temporarily unavailable, so fail-closed processing marked the document FAILED with malware status ERROR. After ClamAV is restored, the user clicks Retry processing. The API verifies the quarantine object, resets QUARANTINED/QUEUED and publishes a new task. An INFECTED result would not expose the retry action.",
                GREEN,
                GREEN_LIGHT,
            ),
            Spacer(1, 8),
            command_block(
                "curl.exe -X POST http://127.0.0.1:8003/api/v1/documents/<DOCUMENT_UUID>/retry `",
                "  -H \"Authorization: Bearer <ACCESS_TOKEN>\"",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("14. Expiry and clear lifecycle statuses", "h1"),
            P("I-18: document expiry", "h2"),
            issue_summary(
                "Quarantined file bytes could remain indefinitely after processing.",
                "No scheduler selected documents that exceeded a configurable retention period.",
                "Celery Beat publishes expire_quarantined_documents hourly. The worker deletes local/MinIO bytes, records storage_deleted_at and retains database metadata for audit.",
                "The dashboard shows Storage: Expired, retry is suppressed and tests confirm content deletion plus metadata retention.",
            ),
            Spacer(1, 8),
            command_block(
                "DOCUMENT_EXPIRY_ENABLED=true",
                "DOCUMENT_RETENTION_DAYS=30",
                "DOCUMENT_EXPIRY_SWEEP_SECONDS=3600",
                "DOCUMENT_EXPIRY_BATCH_SIZE=100",
            ),
            P("I-19: processing statuses", "h2"),
            P(
                "Earlier states exposed internal OCR/extraction/check names and the worker jumped from quarantine directly to a final state. The public lifecycle now records clear operational stages. Legacy enum values remain readable for existing rows.",
            ),
            StatusRail(),
            Spacer(1, 10),
            table(
                [
                    ["Stage", "Trigger"],
                    ["UPLOADED", "Intake request accepted in the application workflow."],
                    ["QUARANTINED", "Validated bytes stored with random key and SHA-256 metadata."],
                    ["SCANNING", "Celery starts malware scanning."],
                    ["PROCESSING", "Malware gate passed or policy allowed continuation."],
                    ["COMPLETED", "Automated processing succeeded."],
                    ["MANUAL_REVIEW", "Password/policy or review condition requires a person."],
                    ["FAILED", "Malware, storage, scanner or processing failure stopped safely."],
                ],
                [120, 380],
            ),
            Spacer(1, 8),
            P(
                "Existing MySQL deployments receive an additive startup compatibility update for the new enum values, storage_deleted_at column and index.",
                "callout",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("15. Git history and Firefox configuration", "h1"),
            P("I-20: fatal bad revision refs/heads/main", "h2"),
            issue_summary(
                "VS Code Git History requested refs/heads/main and Git reported bad revision.",
                "The repository was initialized but had no first commit, so the main branch did not yet reference a commit object.",
                "Review changes, create the initial commit and explicitly name the branch main.",
                "git log --oneline returns the new commit and VS Code history loads normally.",
            ),
            Spacer(1, 8),
            command_block(
                r"cd D:\newdata\grd_document_verf",
                "git status",
                "git add .",
                "git commit -m \"Initial GRD document verification implementation\"",
                "git branch -M main",
                "git log --oneline --decorate -5",
            ),
            P(
                "The .gitignore excludes virtual environments, Python caches, frontend build artifacts, active .env secrets, local quarantine data, logs and editor caches. Confirm staged files before committing.",
                "callout",
            ),
            P("I-21: open VS Code authentication links in Firefox", "h2"),
            P(
                "The workspace sets <b>workbench.externalBrowser</b> to <b>firefox</b>. VS Code then opens external links, including authentication URLs, with Firefox when supported by the command/extension.",
            ),
            command_block(
                "# .vscode/settings.json",
                "{",
                "  \"python.defaultInterpreterPath\": \"${workspaceFolder}/backend/.venv/Scripts/python.exe\",",
                "  \"python.terminal.activateEnvironment\": true,",
                "  \"workbench.externalBrowser\": \"firefox\"",
                "}",
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            P("16. Final architecture and command runbook", "h1"),
            P(
                "The resolved architecture gives each component one clear responsibility and provides safe failure behavior at every boundary.",
            ),
            P(
                "Browser -> FastAPI -> MySQL / Redis / MinIO -> Celery / ClamAV. MySQL is authoritative for business state; MinIO is authoritative for file bytes; Redis coordinates short-lived work and limits.",
                "callout",
            ),
            table(
                [
                    ["Question", "Final answer"],
                    ["Where is the file?", "MinIO in Compose/production; protected local quarantine in local F5 mode."],
                    ["What is in Redis?", "Celery messages/results and rate-limit counters, never document bytes."],
                    ["What is durable?", "MySQL metadata plus MySQL/MinIO named volumes and external backups."],
                    ["Who scans malware?", "ClamAV executable inside the Celery worker image."],
                    ["Who cleans old files?", "Celery Beat schedules; Celery worker deletes through the storage adapter."],
                    ["How does the UI update?", "It polls tenant-scoped case data and displays MySQL status/observations."],
                ],
                [145, 355],
            ),
            Spacer(1, 8),
            P("One-command stack", "h2"),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf",
                "docker compose up -d --build",
                "docker compose ps",
                "curl.exe http://127.0.0.1:8003/health",
                "docker compose logs -f backend celery celery-beat minio",
            ),
            P("Verification commands used during implementation", "h2"),
            command_block(
                r"cd D:\newdata\grd_document_verf\grd-document-verf\backend",
                "python -m pytest -q",
                "python -m ruff check app tests --ignore B008",
                "python -m compileall -q app",
                r"cd ..\frontend",
                "npm run build",
                r"cd ..",
                "docker compose config --quiet",
            ),
            P(
                "Recorded result: 27 backend tests passed, Python lint/compilation passed, the frontend production build passed, both Celery tasks registered and Docker Compose configuration validated. Container runtime launch remains a local operational step whenever Docker Desktop is stopped.",
                "callout",
            ),
        ]
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(PDF_PATH)


if __name__ == "__main__":
    build_pdf()
