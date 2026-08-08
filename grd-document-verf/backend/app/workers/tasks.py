from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.verification_case import VerificationCase
from app.schemas.case import CaseStatus, DocumentStatus
from app.schemas.document import MalwareScanStatus
from app.services.antivirus import MalwareScanResult, scan_file
from app.services.storage import resolve_quarantined_path
from app.workers.celery_app import celery_app

pending_processing_tasks: list[dict] = []

class ProcessingQueueUnavailable(RuntimeError):
    pass


def enqueue_document_processing(
    document_id: str,
    case_id: str,
    storage_key: str,
    password_protected: bool = False,
) -> dict:
    task = {
        "id": str(uuid4()),
        "document_id": document_id,
        "case_id": case_id,
        "storage_key": storage_key,
        "status": "QUEUED",
        "queued_at": datetime.now(timezone.utc),
    }
    pending_processing_tasks.append(task)
    if settings.celery_dispatch_enabled:
        try:
            result = verify_document.delay(
                document_id, case_id, storage_key, password_protected
            )


            task["celery_task_id"] = result.id
        except Exception as exc:  # Celery transports raise different exception types.
            pending_processing_tasks.remove(task)
            raise ProcessingQueueUnavailable(
                "The document processing queue is unavailable"
            ) from exc
    return task


def cancel_document_processing(document_id: str) -> None:
    for task in pending_processing_tasks:
        if task["document_id"] == document_id and task["status"] == "QUEUED":
            task["status"] = "CANCELLED"


def _update_document_record(
    document_id: str,
    malware_status: MalwareScanStatus,
    document_status: DocumentStatus,
) -> None:
    try:
        identifier = UUID(document_id)
    except ValueError:
        return
    with SessionLocal() as session:
        document = session.get(Document, identifier)
        if document is None:
            return
        document.malware_scan_status = malware_status
        document.status = document_status
        verification_case = session.get(VerificationCase, document.case_id)
        if verification_case is not None:
            verification_case.status = {
                DocumentStatus.COMPLETED: CaseStatus.VERIFIED,
                DocumentStatus.MANUAL_REVIEW: CaseStatus.NEEDS_REVIEW,
                DocumentStatus.FAILED: CaseStatus.FAILED,
            }.get(document_status, verification_case.status)
        session.commit()


@celery_app.task(name="verify_document")
def verify_document(
    document_id: str,
    case_id: str,
    object_key: str,
    password_protected: bool = False,
) -> dict:
    # Malware scanning is a mandatory gate before any parser, OCR, or ML processing.
    scan = scan_file(resolve_quarantined_path(object_key))
    base = {
        "document_id": document_id,
        "case_id": case_id,
        "object_key": object_key,
        "malware_scan_status": scan.result.value,
        "malware_scan_detail": scan.detail,
    }
    if scan.result == MalwareScanResult.INFECTED:
        _update_document_record(
            document_id, MalwareScanStatus.INFECTED, DocumentStatus.FAILED
        )
        return {**base, "status": "rejected"}
    if scan.result == MalwareScanResult.ERROR and settings.malware_scan_fail_closed:
        _update_document_record(
            document_id, MalwareScanStatus.ERROR, DocumentStatus.FAILED
        )
        return {**base, "status": "failed"}
    if password_protected:
        _update_document_record(
            document_id,
            MalwareScanStatus(scan.result.value),
            DocumentStatus.MANUAL_REVIEW,
        )
        return {**base, "status": "manual_review"}

    # Pipeline: OCR -> extraction -> consistency -> tamper -> duplicate -> risk.
    _update_document_record(
        document_id,
        MalwareScanStatus(scan.result.value),
        DocumentStatus.COMPLETED,
    )
    return {**base, "status": "completed"}
