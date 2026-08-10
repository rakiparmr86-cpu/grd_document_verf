from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.verification_case import VerificationCase
from app.schemas.case import CaseStatus, DocumentStatus
from app.schemas.document import MalwareScanStatus
from app.services.antivirus import MalwareScanResult, scan_file
from app.services.storage import (
    StorageOperationError,
    delete_quarantined,
    materialize_quarantined,
)
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
        document = session.scalar(
            select(Document).where(Document.id == identifier).with_for_update()
        )
        if document is None:
            return
        document.malware_scan_status = malware_status
        document.status = document_status
        verification_case = session.get(VerificationCase, document.case_id)
        if verification_case is not None:
            session.flush()
            document_statuses = set(
                session.scalars(
                    select(Document.status).where(
                        Document.case_id == document.case_id,
                        Document.tenant_id == document.tenant_id,
                    )
                )
            )
            if DocumentStatus.FAILED in document_statuses:
                verification_case.status = CaseStatus.FAILED
            elif DocumentStatus.MANUAL_REVIEW in document_statuses:
                verification_case.status = CaseStatus.NEEDS_REVIEW
            elif document_statuses == {DocumentStatus.COMPLETED}:
                verification_case.status = CaseStatus.VERIFIED
            else:
                verification_case.status = CaseStatus.PROCESSING
        session.commit()


@celery_app.task(name="verify_document")
def verify_document(
    document_id: str,
    case_id: str,
    object_key: str,
    password_protected: bool = False,
) -> dict:
    # Malware scanning is a mandatory gate before any parser, OCR, or ML processing.
    _update_document_record(
        document_id, MalwareScanStatus.QUEUED, DocumentStatus.SCANNING
    )
    try:
        with materialize_quarantined(object_key) as local_path:
            scan = scan_file(local_path)
    except (StorageOperationError, ValueError) as exc:
        _update_document_record(
            document_id, MalwareScanStatus.ERROR, DocumentStatus.FAILED
        )
        return {
            "document_id": document_id,
            "case_id": case_id,
            "object_key": object_key,
            "malware_scan_status": MalwareScanStatus.ERROR.value,
            "malware_scan_detail": str(exc),
            "status": "failed",
        }
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

    scan_status = MalwareScanStatus(scan.result.value)
    _update_document_record(
        document_id,
        scan_status,
        DocumentStatus.PROCESSING,
    )
    if password_protected:
        _update_document_record(
            document_id,
            scan_status,
            DocumentStatus.MANUAL_REVIEW,
        )
        return {**base, "status": "manual_review"}

    # Pipeline: OCR -> extraction -> consistency -> tamper -> duplicate -> risk.
    _update_document_record(
        document_id,
        scan_status,
        DocumentStatus.COMPLETED,
    )
    return {**base, "status": "completed"}


@celery_app.task(name="expire_quarantined_documents")
def expire_quarantined_documents() -> dict:
    """Delete expired file content while retaining database audit metadata."""
    if not settings.document_expiry_enabled:
        return {"status": "disabled", "expired": 0, "errors": 0}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.document_retention_days)
    expired = 0
    errors = 0
    affected_case_ids: set[UUID] = set()

    with SessionLocal() as session:
        documents = list(
            session.scalars(
                select(Document)
                .where(
                    Document.storage_deleted_at.is_(None),
                    Document.created_at < cutoff,
                )
                .order_by(Document.created_at)
                .limit(settings.document_expiry_batch_size)
                .with_for_update()
            )
        )
        for document in documents:
            try:
                delete_quarantined(document.storage_key)
            except (StorageOperationError, ValueError):
                errors += 1
                continue

            document.storage_deleted_at = now
            if document.status not in {
                DocumentStatus.COMPLETED,
                DocumentStatus.MANUAL_REVIEW,
                DocumentStatus.FAILED,
            }:
                document.status = DocumentStatus.FAILED
                document.malware_scan_status = MalwareScanStatus.ERROR
            affected_case_ids.add(document.case_id)
            expired += 1

        session.flush()
        for case_id in affected_case_ids:
            verification_case = session.get(VerificationCase, case_id)
            if verification_case is None:
                continue
            statuses = set(
                session.scalars(
                    select(Document.status).where(Document.case_id == case_id)
                )
            )
            if DocumentStatus.FAILED in statuses:
                verification_case.status = CaseStatus.FAILED
            elif DocumentStatus.MANUAL_REVIEW in statuses:
                verification_case.status = CaseStatus.NEEDS_REVIEW
            elif statuses == {DocumentStatus.COMPLETED}:
                verification_case.status = CaseStatus.VERIFIED
        session.commit()

    return {"status": "completed", "expired": expired, "errors": errors}
