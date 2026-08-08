from uuid import UUID, uuid4

from app.api.v1.endpoints import documents as document_endpoints
from app.api.v1.endpoints.cases import case_documents, status_history
from app.db.session import SessionLocal
from app.models.document import Document as DocumentModel
from app.models.verification_case import VerificationCase
from app.schemas.case import CaseStatus, DocumentStatus
from app.schemas.document import MalwareScanStatus
from app.workers.tasks import ProcessingQueueUnavailable, pending_processing_tasks
from tests import make_pdf_bytes
from tests.test_secure_document_upload import create_case, upload
from tests.test_tenant_isolation import auth_headers, client


def mark_document_failed(
    document_id: str,
    malware_status: MalwareScanStatus = MalwareScanStatus.ERROR,
) -> None:
    with SessionLocal() as session:
        document = session.get(DocumentModel, UUID(document_id))
        assert document is not None
        document.status = DocumentStatus.FAILED
        document.malware_scan_status = malware_status
        case = session.get(VerificationCase, document.case_id)
        assert case is not None
        case.status = CaseStatus.FAILED
        session.commit()


def create_failed_document(headers) -> tuple[str, str]:
    case_id = create_case(headers, "Retry processing case")
    created = upload(
        case_id,
        headers,
        "retry.pdf",
        make_pdf_bytes("retry processing"),
    )
    assert created.status_code == 202
    document_id = created.json()["document_id"]
    mark_document_failed(document_id)
    return case_id, document_id


def test_failed_document_can_be_requeued_by_its_tenant():
    headers = auth_headers(uuid4())
    case_id, document_id = create_failed_document(headers)
    task_count = len(pending_processing_tasks)

    response = client.post(
        f"/api/v1/documents/{document_id}/retry", headers=headers
    )

    assert response.status_code == 202
    assert response.json()["document_id"] == document_id
    assert response.json()["case_id"] == case_id
    assert response.json()["status"] == DocumentStatus.QUARANTINED.value
    assert response.json()["malware_scan_status"] == MalwareScanStatus.QUEUED.value
    assert len(pending_processing_tasks) == task_count + 1
    assert status_history[-1]["reason"] == "Failed document processing retried"
    with SessionLocal() as session:
        document = session.get(DocumentModel, UUID(document_id))
        case = session.get(VerificationCase, UUID(case_id))
        assert document is not None
        assert case is not None
        assert document.status == DocumentStatus.QUARANTINED
        assert document.malware_scan_status == MalwareScanStatus.QUEUED
        assert case.status == CaseStatus.QUEUED


def test_retry_is_tenant_scoped_and_only_allows_failed_documents():
    owner_headers = auth_headers(uuid4())
    foreign_headers = auth_headers(uuid4())
    case_id = create_case(owner_headers, "Active processing case")
    created = upload(
        case_id,
        owner_headers,
        "active.pdf",
        make_pdf_bytes("active processing"),
    )
    document_id = created.json()["document_id"]

    active = client.post(
        f"/api/v1/documents/{document_id}/retry", headers=owner_headers
    )
    foreign = client.post(
        f"/api/v1/documents/{document_id}/retry", headers=foreign_headers
    )

    assert active.status_code == 409
    assert active.json()["detail"] == "Only failed document processing can be retried"
    assert foreign.status_code == 404


def test_malware_infected_document_cannot_be_retried():
    headers = auth_headers(uuid4())
    _, document_id = create_failed_document(headers)
    mark_document_failed(document_id, MalwareScanStatus.INFECTED)
    task_count = len(pending_processing_tasks)

    response = client.post(
        f"/api/v1/documents/{document_id}/retry", headers=headers
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Malware-infected documents cannot be retried"
    assert len(pending_processing_tasks) == task_count


def test_queue_failure_restores_failed_document_and_case(monkeypatch):
    headers = auth_headers(uuid4())
    case_id, document_id = create_failed_document(headers)

    def queue_unavailable(*_args, **_kwargs):
        raise ProcessingQueueUnavailable("queue unavailable")

    monkeypatch.setattr(
        document_endpoints, "enqueue_document_processing", queue_unavailable
    )
    response = client.post(
        f"/api/v1/documents/{document_id}/retry", headers=headers
    )

    assert response.status_code == 503
    with SessionLocal() as session:
        document = session.get(DocumentModel, UUID(document_id))
        case = session.get(VerificationCase, UUID(case_id))
        assert document is not None
        assert case is not None
        assert document.status == DocumentStatus.FAILED
        assert document.malware_scan_status == MalwareScanStatus.ERROR
        assert case.status == CaseStatus.FAILED
    assert case_documents[document_id]["status"] == DocumentStatus.FAILED
