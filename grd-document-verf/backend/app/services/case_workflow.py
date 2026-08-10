from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.security import AuthContext
from app.schemas.case import CaseStatus, DocumentStatus

CASE_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.DRAFT: frozenset({CaseStatus.UPLOADED, CaseStatus.ARCHIVED}),
    CaseStatus.UPLOADED: frozenset(
        {CaseStatus.VALIDATING, CaseStatus.FAILED, CaseStatus.ARCHIVED}
    ),
    CaseStatus.VALIDATING: frozenset(
        {CaseStatus.QUEUED, CaseStatus.NEEDS_REVIEW, CaseStatus.FAILED}
    ),
    CaseStatus.QUEUED: frozenset({CaseStatus.PROCESSING, CaseStatus.FAILED}),
    CaseStatus.PROCESSING: frozenset(
        {
            CaseStatus.PARTIALLY_PROCESSED,
            CaseStatus.NEEDS_REVIEW,
            CaseStatus.HIGH_RISK,
            CaseStatus.VERIFIED,
            CaseStatus.FAILED,
        }
    ),
    CaseStatus.PARTIALLY_PROCESSED: frozenset(
        {
            CaseStatus.PROCESSING,
            CaseStatus.NEEDS_REVIEW,
            CaseStatus.HIGH_RISK,
            CaseStatus.FAILED,
        }
    ),
    CaseStatus.NEEDS_REVIEW: frozenset(
        {CaseStatus.HIGH_RISK, CaseStatus.VERIFIED, CaseStatus.REJECTED}
    ),
    CaseStatus.HIGH_RISK: frozenset(
        {CaseStatus.NEEDS_REVIEW, CaseStatus.REJECTED, CaseStatus.VERIFIED}
    ),
    CaseStatus.VERIFIED: frozenset({CaseStatus.ARCHIVED}),
    CaseStatus.REJECTED: frozenset({CaseStatus.ARCHIVED}),
    CaseStatus.FAILED: frozenset({CaseStatus.QUEUED, CaseStatus.ARCHIVED}),
    CaseStatus.ARCHIVED: frozenset(),
}

DOCUMENT_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.UPLOADED: frozenset(
        {DocumentStatus.QUARANTINED, DocumentStatus.FAILED}
    ),
    DocumentStatus.RECEIVED: frozenset(
        {DocumentStatus.QUARANTINED, DocumentStatus.VALIDATED, DocumentStatus.FAILED}
    ),
    DocumentStatus.QUARANTINED: frozenset(
        {
            DocumentStatus.SCANNING,
            DocumentStatus.VALIDATED,
            DocumentStatus.FAILED,
            DocumentStatus.MANUAL_REVIEW,
        }
    ),
    DocumentStatus.SCANNING: frozenset(
        {
            DocumentStatus.PROCESSING,
            DocumentStatus.FAILED,
            DocumentStatus.MANUAL_REVIEW,
        }
    ),
    DocumentStatus.PROCESSING: frozenset(
        {
            DocumentStatus.COMPLETED,
            DocumentStatus.FAILED,
            DocumentStatus.MANUAL_REVIEW,
        }
    ),
    DocumentStatus.VALIDATED: frozenset(
        {DocumentStatus.OCR_RUNNING, DocumentStatus.FAILED}
    ),
    DocumentStatus.OCR_RUNNING: frozenset(
        {
            DocumentStatus.EXTRACTION_RUNNING,
            DocumentStatus.FAILED,
            DocumentStatus.MANUAL_REVIEW,
        }
    ),
    DocumentStatus.EXTRACTION_RUNNING: frozenset(
        {
            DocumentStatus.CHECKS_RUNNING,
            DocumentStatus.FAILED,
            DocumentStatus.MANUAL_REVIEW,
        }
    ),
    DocumentStatus.CHECKS_RUNNING: frozenset(
        {DocumentStatus.COMPLETED, DocumentStatus.FAILED, DocumentStatus.MANUAL_REVIEW}
    ),
    DocumentStatus.COMPLETED: frozenset({DocumentStatus.MANUAL_REVIEW}),
    DocumentStatus.FAILED: frozenset(
        {
            DocumentStatus.QUARANTINED,
            DocumentStatus.VALIDATED,
            DocumentStatus.MANUAL_REVIEW,
        }
    ),
    DocumentStatus.MANUAL_REVIEW: frozenset(
        {DocumentStatus.COMPLETED, DocumentStatus.FAILED}
    ),
}


def transition(
    entity: dict,
    target,
    transitions: dict,
    entity_type: str,
    context: AuthContext,
    history: list[dict],
    reason: str | None = None,
):
    current = entity["status"]
    if target == current:
        return entity
    if target not in transitions[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invalid {entity_type} status transition: "
                f"{current.value} -> {target.value}"
            ),
        )
    now = datetime.now(timezone.utc)
    entity["status"] = target
    entity["updated_by"] = str(context.user_id)
    entity["updated_at"] = now
    history.append(
        {
            "id": str(uuid4()),
            "tenant_id": str(context.tenant_id),
            "entity_type": entity_type,
            "entity_id": entity["id"],
            "from_status": current.value,
            "to_status": target.value,
            "reason": reason,
            "changed_by": str(context.user_id),
            "changed_at": now,
        }
    )
    return entity
