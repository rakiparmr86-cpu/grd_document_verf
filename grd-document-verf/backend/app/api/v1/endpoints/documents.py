from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.cases import (
    case_documents,
    case_records,
    create_case_record,
    document_hash_index,
    document_model_to_record,
    secure_add_document,
    status_history,
)
from app.core.permissions import Permission
from app.core.security import AuthContext, require_permission
from app.db.session import get_db
from app.models.document import Document as DocumentModel
from app.models.verification_case import VerificationCase
from app.schemas.case import CaseStatus, DocumentStatus
from app.schemas.document import (
    DocumentRead,
    DocumentRetryAccepted,
    DocumentStatusRead,
    DocumentType,
    MalwareScanStatus,
)
from app.schemas.verification import (
    ProcessingEvent,
    VerificationResult,
    VerificationStatus,
)
from app.services.rate_limit import enforce_upload_rate_limit
from app.services.storage import (
    StorageOperationError,
    delete_quarantined,
    quarantined_exists,
)
from app.workers.tasks import (
    ProcessingQueueUnavailable,
    cancel_document_processing,
    enqueue_document_processing,
)

router = APIRouter()
verification_cases: dict[str, VerificationResult] = {}


def _get_document(document_id: str, context: AuthContext, db: Session) -> dict:
    document = case_documents.get(document_id)
    try:
        database_document = db.get(DocumentModel, UUID(document_id))
    except ValueError:
        database_document = None
    if (
        database_document is not None
        and database_document.tenant_id == context.tenant_id
    ):
        document = document_model_to_record(database_document)
        case_documents[document_id] = document
        document_hash_index[(document["tenant_id"], document["sha256"])] = document_id
        return document
    if document is not None and document["tenant_id"] == str(context.tenant_id):
        return document
    if document is None or document["tenant_id"] != str(context.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return document


@router.post(
    "",
    response_model=VerificationResult,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_upload_rate_limit)],
)
async def upload_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    issuer_or_organisation: str | None = Form(default=None),
    context: AuthContext = Depends(require_permission(Permission.CASE_SUBMIT)),
    db: Session = Depends(get_db),
):
    case = create_case_record(
        file.filename or "Document verification case", None, context, db
    )
    try:
        await secure_add_document(
            case, file, document_type, issuer_or_organisation, context, db
        )
    except Exception:
        db.rollback()
        database_case = db.get(VerificationCase, UUID(case["id"]))
        if database_case is not None:
            db.delete(database_case)
            db.commit()
        case_records.pop(case["id"], None)
        status_history[:] = [
            event for event in status_history if event["entity_id"] != case["id"]
        ]
        raise
    case_id = case["id"]
    now = datetime.now(timezone.utc)
    result = VerificationResult(
        case_id=case_id,
        tenant_id=str(context.tenant_id),
        created_by=str(context.user_id),
        created_at=now,
        updated_by=str(context.user_id),
        updated_at=now,
        filename=file.filename or "unnamed-document",
        document_type=document_type,
        issuer_or_organisation=issuer_or_organisation or None,
        risk_level=VerificationStatus.UNABLE_TO_VERIFY,
        recommended_action=(
            "Processing queued. Review the completed verification before taking action."
        ),
        human_review_required=True,
        processing_history=[
            ProcessingEvent(
                stage="Document received",
                status="Completed",
                occurred_at=now,
            ),
            ProcessingEvent(
                stage="Verification",
                status="Queued",
                occurred_at=now,
            ),
        ],
    )
    verification_cases[case_id] = result
    return result


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: str,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    return _get_document(document_id, context, db)


@router.get("/{document_id}/status", response_model=DocumentStatusRead)
async def get_document_status(
    document_id: str,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    return _get_document(document_id, context, db)


@router.post(
    "/{document_id}/retry",
    response_model=DocumentRetryAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_document_processing(
    document_id: str,
    context: Annotated[
        AuthContext, Depends(require_permission(Permission.CASE_SUBMIT))
    ],
    db: Annotated[Session, Depends(get_db)],
):
    _get_document(document_id, context, db)
    try:
        identifier = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from None

    database_document = db.scalar(
        select(DocumentModel)
        .where(
            DocumentModel.id == identifier,
            DocumentModel.tenant_id == context.tenant_id,
        )
        .with_for_update()
    )
    if database_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    if database_document.status != DocumentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed document processing can be retried",
        )
    if database_document.malware_scan_status == MalwareScanStatus.INFECTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Malware-infected documents cannot be retried",
        )

    if database_document.storage_deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The quarantined file is unavailable; upload the document again",
        )
    try:
        storage_available = quarantined_exists(database_document.storage_key)
    except (StorageOperationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quarantine storage is unavailable",
        ) from exc
    if not storage_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The quarantined file is unavailable; upload the document again",
        )

    database_case = db.get(VerificationCase, database_document.case_id)
    previous_document_status = database_document.status
    previous_malware_status = database_document.malware_scan_status
    previous_document_updated_by = database_document.updated_by
    previous_case_status = database_case.status if database_case is not None else None
    previous_case_updated_by = (
        database_case.updated_by if database_case is not None else None
    )

    database_document.status = DocumentStatus.QUARANTINED
    database_document.malware_scan_status = MalwareScanStatus.QUEUED
    database_document.updated_by = context.user_id
    if database_case is not None:
        database_case.status = CaseStatus.QUEUED
        database_case.updated_by = context.user_id
    db.commit()

    try:
        task = enqueue_document_processing(
            document_id,
            str(database_document.case_id),
            database_document.storage_key,
            database_document.password_protected,
        )
    except ProcessingQueueUnavailable as exc:
        database_document.status = previous_document_status
        database_document.malware_scan_status = previous_malware_status
        database_document.updated_by = previous_document_updated_by
        if database_case is not None and previous_case_status is not None:
            database_case.status = previous_case_status
            database_case.updated_by = previous_case_updated_by
        db.commit()
        case_documents[document_id] = document_model_to_record(database_document)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document processing queue is unavailable",
        ) from exc

    db.refresh(database_document)
    case_documents[document_id] = document_model_to_record(database_document)
    case = case_records.get(str(database_document.case_id))
    if case is not None:
        case["status"] = CaseStatus.QUEUED
        case["updated_by"] = str(context.user_id)
        case["updated_at"] = database_document.updated_at
        case["documents"] = [
            case_documents[document_id] if item["id"] == document_id else item
            for item in case["documents"]
        ]
    status_history.append(
        {
            "id": str(uuid4()),
            "tenant_id": str(context.tenant_id),
            "entity_type": "document",
            "entity_id": document_id,
            "from_status": DocumentStatus.FAILED.value,
            "to_status": DocumentStatus.QUARANTINED.value,
            "reason": "Failed document processing retried",
            "changed_by": str(context.user_id),
            "changed_at": datetime.now(timezone.utc),
        }
    )
    return DocumentRetryAccepted(
        document_id=document_id,
        case_id=str(database_document.case_id),
        status=database_document.status.value,
        malware_scan_status=database_document.malware_scan_status,
        processing_task_id=task["id"],
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    context: AuthContext = Depends(require_permission(Permission.CASE_SUBMIT)),
    db: Session = Depends(get_db),
):
    document = _get_document(document_id, context, db)
    try:
        delete_quarantined(document["storage_key"])
    except (StorageOperationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The quarantined file could not be deleted",
        ) from exc
    cancel_document_processing(document_id)
    database_document = db.get(DocumentModel, UUID(document_id))
    if database_document is not None:
        db.delete(database_document)
        db.commit()
    case_documents.pop(document_id, None)
    document_hash_index.pop((document["tenant_id"], document["sha256"]), None)

    case = case_records.get(document["case_id"])
    if case is not None:
        case["documents"] = [
            item for item in case["documents"] if item["id"] != document_id
        ]
        case["updated_by"] = str(context.user_id)
        case["updated_at"] = datetime.now(timezone.utc)

    status_history.append(
        {
            "id": str(uuid4()),
            "tenant_id": document["tenant_id"],
            "entity_type": "document",
            "entity_id": document_id,
            "from_status": document["status"].value,
            "to_status": "DELETED",
            "reason": "Document and quarantined file deleted",
            "changed_by": str(context.user_id),
            "changed_at": datetime.now(timezone.utc),
        }
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
