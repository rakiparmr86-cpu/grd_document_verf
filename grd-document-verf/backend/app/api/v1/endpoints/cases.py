from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import Permission, Role
from app.core.security import AuthContext, require_permission
from app.db.session import get_db
from app.models.document import Document as DocumentModel
from app.models.verification_case import VerificationCase
from app.schemas.case import (
    CaseCreate,
    CaseRead,
    CaseStatus,
    DocumentStatus,
    StatusChange,
    StatusHistoryRead,
)
from app.schemas.document import DocumentType, DocumentUploadAccepted, MalwareScanStatus
from app.services.case_workflow import (
    CASE_TRANSITIONS,
    DOCUMENT_TRANSITIONS,
    transition,
)
from app.services.rate_limit import enforce_upload_rate_limit
from app.services.storage import (
    QuarantinedUpload,
    UploadValidationError,
    delete_quarantined,
    quarantine_upload,
)
from app.workers.tasks import ProcessingQueueUnavailable, enqueue_document_processing

router = APIRouter()
case_records: dict[str, dict] = {}
case_documents: dict[str, dict] = {}
document_hash_index: dict[tuple[str, str], str] = {}
status_history: list[dict] = []


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")


def document_observations(
    *,
    detected_file_type,
    size_bytes: int,
    page_count: int,
    password_protected: bool,
    malware_scan_status,
    document_status,
) -> list[str]:
    detected = getattr(detected_file_type, "value", detected_file_type)
    malware = getattr(malware_scan_status, "value", malware_scan_status)
    current_status = getattr(document_status, "value", document_status)
    observations = [
        f"File signature validated as {str(detected).upper()}.",
        f"Document is readable with {page_count} page(s) and is {size_bytes:,} bytes.",
    ]
    if password_protected:
        observations.append("The document is password-protected and requires manual review.")
    if malware == MalwareScanStatus.CLEAN.value:
        observations.append("Malware scan completed successfully; no malware was detected.")
    elif malware == MalwareScanStatus.INFECTED.value:
        observations.append("Malware was detected and the document was rejected.")
    elif malware == MalwareScanStatus.ERROR.value:
        observations.append("Malware scanning could not complete; processing stopped safely.")
    else:
        observations.append("Malware scanning and background verification are queued.")
    if current_status == DocumentStatus.COMPLETED.value:
        observations.append("Secure intake checks completed. No upload-level anomaly was found.")
    elif current_status == DocumentStatus.MANUAL_REVIEW.value:
        observations.append("Automated processing routed this document to manual review.")
    elif current_status == DocumentStatus.FAILED.value:
        observations.append("Automated processing failed; review the scan result before retrying.")
    else:
        observations.append(f"Current processing status: {current_status}.")
    return observations


def case_status_from_documents(current_status, documents: list[DocumentModel]):
    if not documents:
        return current_status
    statuses = {item.status for item in documents}
    if DocumentStatus.FAILED in statuses:
        return CaseStatus.FAILED
    if DocumentStatus.MANUAL_REVIEW in statuses:
        return CaseStatus.NEEDS_REVIEW
    if statuses == {DocumentStatus.COMPLETED}:
        return CaseStatus.VERIFIED
    return current_status


def document_model_to_record(document: DocumentModel) -> dict:
    record = {
        "id": str(document.id),
        "case_id": str(document.case_id),
        "tenant_id": str(document.tenant_id),
        "filename": document.filename,
        "storage_key": document.storage_key,
        "sha256": document.sha256,
        "size_bytes": document.size_bytes,
        "detected_file_type": document.detected_file_type,
        "page_count": document.page_count,
        "password_protected": document.password_protected,
        "malware_scan_status": document.malware_scan_status,
        "document_type": document.document_type,
        "status": document.status,
        "issuer_or_organisation": document.issuer_or_organisation,
        "created_by": str(document.created_by),
        "created_at": document.created_at,
        "updated_by": str(document.updated_by),
        "updated_at": document.updated_at,
    }
    record["observations"] = document_observations(
        detected_file_type=document.detected_file_type,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        password_protected=document.password_protected,
        malware_scan_status=document.malware_scan_status,
        document_status=document.status,
    )
    return record


def _get_case(case_id: str, context: AuthContext, db: Session | None = None) -> dict:
    case = case_records.get(case_id)
    if db is not None:
        try:
            database_case = db.get(VerificationCase, UUID(case_id))
        except ValueError:
            database_case = None
        if database_case is not None and database_case.tenant_id == context.tenant_id:
            documents = list(
                db.scalars(
                    select(DocumentModel).where(
                        DocumentModel.case_id == database_case.id,
                        DocumentModel.tenant_id == context.tenant_id,
                    )
                )
            )
            case = {
                "id": str(database_case.id),
                "tenant_id": str(database_case.tenant_id),
                "name": database_case.name,
                "reference": database_case.reference,
                "status": case_status_from_documents(database_case.status, documents),
                "documents": [document_model_to_record(item) for item in documents],
                "created_by": str(database_case.created_by),
                "created_at": database_case.created_at,
                "updated_by": str(database_case.updated_by),
                "updated_at": database_case.updated_at,
            }
            case_records[case_id] = case
            for document in case["documents"]:
                case_documents[document["id"]] = document
                document_hash_index[(document["tenant_id"], document["sha256"])] = (
                    document["id"]
                )
            return case
    if case is not None and case["tenant_id"] == str(context.tenant_id):
        return case
    if case is None or case["tenant_id"] != str(context.tenant_id):
        raise _not_found()
    return case


def create_case_record(
    name: str,
    reference: str | None,
    context: AuthContext,
    db: Session | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    case_id = str(uuid4())
    case = {
        "id": case_id,
        "tenant_id": str(context.tenant_id),
        "name": name,
        "reference": reference,
        "status": CaseStatus.DRAFT,
        "documents": [],
        "created_by": str(context.user_id),
        "created_at": now,
        "updated_by": str(context.user_id),
        "updated_at": now,
    }
    case_records[case_id] = case
    if db is not None:
        try:
            db.add(
                VerificationCase(
                    id=UUID(case_id),
                    tenant_id=context.tenant_id,
                    name=name,
                    reference=reference,
                    status=CaseStatus.DRAFT,
                    created_by=context.user_id,
                    updated_by=context.user_id,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            case_records.pop(case_id, None)
            raise
    status_history.append(
        {
            "id": str(uuid4()),
            "tenant_id": str(context.tenant_id),
            "entity_type": "case",
            "entity_id": case_id,
            "from_status": None,
            "to_status": CaseStatus.DRAFT.value,
            "reason": "Case created",
            "changed_by": str(context.user_id),
            "changed_at": now,
        }
    )
    return case


def _persist_document_record(document: dict, case: dict, db: Session) -> None:
    db.add(
        DocumentModel(
            id=UUID(document["id"]),
            case_id=UUID(document["case_id"]),
            tenant_id=UUID(document["tenant_id"]),
            filename=document["filename"],
            storage_key=document["storage_key"],
            sha256=document["sha256"],
            size_bytes=document["size_bytes"],
            detected_file_type=document["detected_file_type"],
            page_count=document["page_count"],
            password_protected=document["password_protected"],
            malware_scan_status=document["malware_scan_status"],
            document_type=document["document_type"],
            status=document["status"],
            issuer_or_organisation=document["issuer_or_organisation"],
            created_by=UUID(document["created_by"]),
            updated_by=UUID(document["updated_by"]),
        )
    )
    database_case = db.get(VerificationCase, UUID(case["id"]))
    if database_case is not None:
        database_case.status = case["status"]
        database_case.updated_by = UUID(case["updated_by"])
    db.commit()


def add_document_record(
    case: dict,
    upload: QuarantinedUpload,
    document_type: DocumentType,
    issuer: str | None,
    context: AuthContext,
) -> dict:
    now = datetime.now(timezone.utc)
    document_id = str(uuid4())
    document = {
        "id": document_id,
        "case_id": case["id"],
        "tenant_id": str(context.tenant_id),
        "filename": upload.original_filename,
        "storage_key": upload.storage_key,
        "sha256": upload.sha256,
        "size_bytes": upload.size_bytes,
        "detected_file_type": upload.detected_file_type,
        "page_count": upload.page_count,
        "password_protected": upload.password_protected,
        "malware_scan_status": MalwareScanStatus.QUEUED,
        "document_type": document_type,
        "status": DocumentStatus.RECEIVED,
        "issuer_or_organisation": issuer,
        "created_by": str(context.user_id),
        "created_at": now,
        "updated_by": str(context.user_id),
        "updated_at": now,
    }
    document["observations"] = document_observations(
        detected_file_type=upload.detected_file_type,
        size_bytes=upload.size_bytes,
        page_count=upload.page_count,
        password_protected=upload.password_protected,
        malware_scan_status=MalwareScanStatus.QUEUED,
        document_status=DocumentStatus.RECEIVED,
    )
    case_documents[document_id] = document
    case["documents"].append(document)
    case["updated_by"] = str(context.user_id)
    case["updated_at"] = now
    status_history.append(
        {
            "id": str(uuid4()),
            "tenant_id": str(context.tenant_id),
            "entity_type": "document",
            "entity_id": document_id,
            "from_status": None,
            "to_status": DocumentStatus.RECEIVED.value,
            "reason": "Document received",
            "changed_by": str(context.user_id),
            "changed_at": now,
        }
    )
    transition(
        document,
        DocumentStatus.QUARANTINED,
        DOCUMENT_TRANSITIONS,
        "document",
        context,
        status_history,
        "File validated and saved to quarantine",
    )
    if case["status"] == CaseStatus.DRAFT:
        transition(
            case,
            CaseStatus.UPLOADED,
            CASE_TRANSITIONS,
            "case",
            context,
            status_history,
            "First document uploaded",
        )
    return document


async def secure_add_document(
    case: dict,
    file: UploadFile,
    document_type: DocumentType,
    issuer_or_organisation: str | None,
    context: AuthContext,
    db: Session | None = None,
) -> dict:
    if len(case["documents"]) >= settings.max_files_per_case:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"The case has reached its {settings.max_files_per_case}-document limit"
            ),
        )

    try:
        upload = await quarantine_upload(file)
    except UploadValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    hash_key = (str(context.tenant_id), upload.sha256)
    duplicate_id = document_hash_index.get(hash_key)
    duplicate_exists = duplicate_id is not None and duplicate_id in case_documents
    if db is not None:
        database_duplicate_id = db.scalar(
            select(DocumentModel.id).where(
                DocumentModel.tenant_id == context.tenant_id,
                DocumentModel.sha256 == upload.sha256,
            )
        )
        if database_duplicate_id is not None:
            duplicate_id = str(database_duplicate_id)
            duplicate_exists = True
    if duplicate_exists:
        delete_quarantined(upload.storage_key)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "An exact duplicate already exists",
                "document_id": duplicate_id,
            },
        )

    try:
        previous_case_status = case["status"]
        previous_case_updated_by = case["updated_by"]
        previous_case_updated_at = case["updated_at"]
        previous_history_length = len(status_history)
        document = None
        document = add_document_record(
            case, upload, document_type, issuer_or_organisation, context
        )
        document_hash_index[hash_key] = document["id"]
        if db is not None:
            _persist_document_record(document, case, db)
        task = enqueue_document_processing(
            document["id"],
            case["id"],
            upload.storage_key,
            upload.password_protected,
        )
        document["processing_task_id"] = task["id"]
        return document
    except Exception as exc:
        if db is not None:
            db.rollback()
        document_hash_index.pop(hash_key, None)
        if document is not None:
            case_documents.pop(document["id"], None)
            case["documents"] = [
                item for item in case["documents"] if item["id"] != document["id"]
            ]
            case["status"] = previous_case_status
            case["updated_by"] = previous_case_updated_by
            case["updated_at"] = previous_case_updated_at
            del status_history[previous_history_length:]
            if db is not None:
                database_document = db.get(DocumentModel, UUID(document["id"]))
                if database_document is not None:
                    db.delete(database_document)
                database_case = db.get(VerificationCase, UUID(case["id"]))
                if database_case is not None:
                    database_case.status = previous_case_status
                    database_case.updated_by = UUID(previous_case_updated_by)
                db.commit()
        delete_quarantined(upload.storage_key)
        if isinstance(exc, IntegrityError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An exact duplicate already exists",
            ) from None
        if isinstance(exc, ProcessingQueueUnavailable):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The document processing queue is unavailable",
            ) from None
        raise


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    context: AuthContext = Depends(require_permission(Permission.CASE_SUBMIT)),
    db: Session = Depends(get_db),
):
    return create_case_record(payload.name, payload.reference, context, db)


@router.get("", response_model=list[CaseRead])
async def list_cases(
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    database_case_ids = list(
        db.scalars(
            select(VerificationCase.id).where(
                VerificationCase.tenant_id == context.tenant_id
            )
        )
    )
    return [_get_case(str(case_id), context, db) for case_id in database_case_ids]


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: str,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    return _get_case(case_id, context, db)


@router.post(
    "/{case_id}/documents",
    response_model=DocumentUploadAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_upload_rate_limit)],
)
async def add_document(
    case_id: str,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    issuer_or_organisation: str | None = Form(default=None),
    context: AuthContext = Depends(require_permission(Permission.CASE_SUBMIT)),
    db: Session = Depends(get_db),
):
    case = _get_case(case_id, context, db)
    if case["status"] == CaseStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Documents cannot be added to an archived case",
        )
    document = await secure_add_document(
        case, file, document_type, issuer_or_organisation, context, db
    )
    return DocumentUploadAccepted(
        document_id=document["id"],
        case_id=case_id,
        status=document["status"].value,
        malware_scan_status=document["malware_scan_status"],
    )


@router.post("/{case_id}/status", response_model=CaseRead)
async def change_case_status(
    case_id: str,
    payload: StatusChange,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    case = _get_case(case_id, context, db)
    try:
        target = CaseStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown case status") from None
    role_targets = {
        CaseStatus.HIGH_RISK: {Role.FRAUD_ANALYST},
        CaseStatus.VERIFIED: {Role.REVIEWER, Role.SENIOR_APPROVER},
        CaseStatus.REJECTED: {Role.REVIEWER, Role.SENIOR_APPROVER},
        CaseStatus.ARCHIVED: {Role.ORGANISATION_ADMIN},
    }
    allowed_roles = role_targets.get(
        target, {Role.VERIFICATION_EXECUTIVE, Role.ORGANISATION_ADMIN}
    )
    if context.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot set this case status",
        )
    updated = transition(
        case, target, CASE_TRANSITIONS, "case", context, status_history, payload.reason
    )
    database_case = db.get(VerificationCase, UUID(case_id))
    if database_case is not None:
        database_case.status = target
        database_case.updated_by = context.user_id
        db.commit()
    return updated


@router.post("/{case_id}/documents/{document_id}/status")
async def change_document_status(
    case_id: str,
    document_id: str,
    payload: StatusChange,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    _get_case(case_id, context, db)
    document = case_documents.get(document_id)
    if (
        document is None
        or document["case_id"] != case_id
        or document["tenant_id"] != str(context.tenant_id)
    ):
        raise HTTPException(status_code=404, detail="Document not found")
    if context.role not in {
        Role.VERIFICATION_EXECUTIVE,
        Role.FRAUD_ANALYST,
        Role.REVIEWER,
        Role.ORGANISATION_ADMIN,
    }:
        raise HTTPException(
            status_code=403, detail="Role cannot update document processing status"
        )
    try:
        target = DocumentStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown document status") from None
    updated = transition(
        document,
        target,
        DOCUMENT_TRANSITIONS,
        "document",
        context,
        status_history,
        payload.reason,
    )
    database_document = db.get(DocumentModel, UUID(document_id))
    if database_document is not None:
        database_document.status = target
        database_document.updated_by = context.user_id
        db.commit()
    return updated


@router.get("/{case_id}/history", response_model=list[StatusHistoryRead])
async def get_case_history(
    case_id: str,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
    db: Session = Depends(get_db),
):
    case = _get_case(case_id, context, db)
    document_ids = {document["id"] for document in case["documents"]}
    return [
        event
        for event in status_history
        if event["tenant_id"] == str(context.tenant_id)
        and (event["entity_id"] == case_id or event["entity_id"] in document_ids)
    ]
