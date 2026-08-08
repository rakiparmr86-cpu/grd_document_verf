from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import fitz
from PIL import Image

from app.api.v1.endpoints.cases import (
    case_documents,
    case_records,
    document_hash_index,
)
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document as DocumentModel
from app.workers.tasks import pending_processing_tasks, verify_document
from tests import make_pdf_bytes
from tests.test_tenant_isolation import auth_headers, client


def create_case(headers, name="Secure upload case") -> str:
    response = client.post("/api/v1/cases", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def upload(
    case_id: str,
    headers: dict,
    filename: str,
    content: bytes,
    mime_type="application/octet-stream",
):
    return client.post(
        f"/api/v1/cases/{case_id}/documents",
        headers=headers,
        data={"document_type": "bank_statement"},
        files={"file": (filename, content, mime_type)},
    )


def png_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (16, 16), color="white").save(stream, format="PNG")
    return stream.getvalue()


def tiff_bytes(pages: int = 2) -> bytes:
    stream = BytesIO()
    frames = [Image.new("RGB", (16, 16), color="white") for _ in range(pages)]
    frames[0].save(
        stream,
        format="TIFF",
        save_all=True,
        append_images=frames[1:],
    )
    return stream.getvalue()


def encrypted_pdf_bytes() -> bytes:
    source = fitz.open()
    encrypted = BytesIO()
    try:
        source.new_page().insert_text((72, 72), "protected")
        source.save(
            encrypted,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner-password",
            user_pw="user-password",
        )
        return encrypted.getvalue()
    finally:
        source.close()


def test_upload_authenticates_ignores_browser_mime_and_queues_quarantined_file():
    headers = auth_headers(uuid4())
    case_id = create_case(headers)

    no_auth = upload(case_id, {}, "image.png", png_bytes(), "image/png")
    assert no_auth.status_code in (401, 403)

    response = upload(case_id, headers, "folder\\image.png", png_bytes(), "text/plain")
    assert response.status_code == 202
    accepted = response.json()
    assert accepted["status"] == "QUARANTINED"
    assert accepted["malware_scan_status"] == "QUEUED"
    assert len(pending_processing_tasks) == 1

    document = case_documents[accepted["document_id"]]
    assert document["filename"] == "image.png"
    assert document["storage_key"] != "image.png"
    assert Path(document["storage_key"]).name == document["storage_key"]
    assert (settings.quarantine_storage_path / document["storage_key"]).exists()


def test_rejects_spoofed_mismatched_corrupted_and_disabled_tiff_files():
    headers = auth_headers(uuid4())
    case_id = create_case(headers)

    assert (
        upload(
            case_id, headers, "fake.pdf", b"not a pdf", "application/pdf"
        ).status_code
        == 415
    )
    assert (
        upload(
            case_id, headers, "image.pdf", png_bytes(), "application/pdf"
        ).status_code
        == 415
    )
    assert (
        upload(
            case_id, headers, "broken.pdf", b"%PDF-1.7\ncorrupt", "application/pdf"
        ).status_code
        == 422
    )
    assert (
        upload(
            case_id, headers, "scan.tiff", b"II*\x00invalid", "image/tiff"
        ).status_code
        == 415
    )
    assert case_documents == {}


def test_enforces_size_page_and_per_case_limits(monkeypatch):
    headers = auth_headers(uuid4())
    case_id = create_case(headers)

    monkeypatch.setattr(settings, "max_upload_size_bytes", 100)
    assert (
        upload(case_id, headers, "large.pdf", make_pdf_bytes("large")).status_code
        == 413
    )

    monkeypatch.setattr(settings, "max_upload_size_bytes", 25 * 1024 * 1024)
    monkeypatch.setattr(settings, "max_document_pages", 1)
    assert (
        upload(
            case_id, headers, "two-pages.pdf", make_pdf_bytes("pages", pages=2)
        ).status_code
        == 413
    )

    monkeypatch.setattr(settings, "max_document_pages", 100)
    monkeypatch.setattr(settings, "max_files_per_case", 1)
    assert (
        upload(case_id, headers, "first.pdf", make_pdf_bytes("first")).status_code
        == 202
    )
    assert (
        upload(case_id, headers, "second.pdf", make_pdf_bytes("second")).status_code
        == 409
    )


def test_rejects_password_protected_pdf_by_default():
    headers = auth_headers(uuid4())
    case_id = create_case(headers)
    response = upload(
        case_id, headers, "protected.pdf", encrypted_pdf_bytes(), "application/pdf"
    )
    assert response.status_code == 422
    assert "Password-protected" in response.json()["detail"]


def test_password_protected_pdf_can_be_routed_for_review(monkeypatch):
    monkeypatch.setattr(settings, "password_protected_pdf_policy", "review")
    headers = auth_headers(uuid4())
    case_id = create_case(headers)

    response = upload(case_id, headers, "protected.pdf", encrypted_pdf_bytes())

    assert response.status_code == 202
    document = case_documents[response.json()["document_id"]]
    assert document["password_protected"] is True


def test_tiff_requires_explicit_configuration(monkeypatch):
    monkeypatch.setattr(settings, "allow_tiff_uploads", True)
    headers = auth_headers(uuid4())
    case_id = create_case(headers)

    response = upload(case_id, headers, "scan.tiff", tiff_bytes())

    assert response.status_code == 202
    document = case_documents[response.json()["document_id"]]
    assert document["detected_file_type"] == "tiff"
    assert document["page_count"] == 2


def test_exact_duplicate_is_rejected_with_existing_document_id():
    tenant_id = uuid4()
    headers = auth_headers(tenant_id)
    first_case = create_case(headers, "First")
    second_case = create_case(headers, "Second")
    content = make_pdf_bytes("same content")

    first = upload(first_case, headers, "first.pdf", content)
    duplicate = upload(second_case, headers, "renamed.pdf", content)

    assert first.status_code == 202
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["document_id"] == first.json()["document_id"]
    assert len(case_documents) == 1


def test_document_read_status_and_delete_are_tenant_scoped():
    owner_headers = auth_headers(uuid4())
    foreign_headers = auth_headers(uuid4())
    case_id = create_case(owner_headers)
    assert (
        upload(
            case_id, foreign_headers, "foreign.pdf", make_pdf_bytes("foreign")
        ).status_code
        == 404
    )
    created = upload(case_id, owner_headers, "statement.pdf", make_pdf_bytes("private"))
    document_id = created.json()["document_id"]
    storage_key = case_documents[document_id]["storage_key"]

    with SessionLocal() as session:
        database_document = session.get(DocumentModel, UUID(document_id))
        assert database_document is not None
        assert database_document.sha256 == case_documents[document_id]["sha256"]

    # Prove reads can recover from the durable database, not only memory.
    case_documents.clear()
    document_hash_index.clear()

    document = client.get(f"/api/v1/documents/{document_id}", headers=owner_headers)
    assert document.status_code == 200
    assert document.json()["sha256"]
    assert "storage_key" not in document.json()
    document_status = client.get(
        f"/api/v1/documents/{document_id}/status", headers=owner_headers
    )
    assert document_status.status_code == 200
    assert document_status.json()["status"] == "QUARANTINED"

    assert (
        client.get(
            f"/api/v1/documents/{document_id}", headers=foreign_headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/documents/{document_id}/status", headers=foreign_headers
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/documents/{document_id}", headers=foreign_headers
        ).status_code
        == 404
    )

    deleted = client.delete(f"/api/v1/documents/{document_id}", headers=owner_headers)
    assert deleted.status_code == 204
    assert not (settings.quarantine_storage_path / storage_key).exists()
    assert (
        client.get(
            f"/api/v1/documents/{document_id}", headers=owner_headers
        ).status_code
        == 404
    )
    with SessionLocal() as session:
        assert session.get(DocumentModel, UUID(document_id)) is None
    assert pending_processing_tasks[0]["status"] == "CANCELLED"


def test_malware_scan_blocks_processing_before_pipeline():
    headers = auth_headers(uuid4())
    case_id = create_case(headers)
    content = make_pdf_bytes("malware test") + (b"\nEICAR-STANDARD-ANTIVIRUS-TEST-FILE")
    created = upload(case_id, headers, "eicar.pdf", content)
    document_id = created.json()["document_id"]
    storage_key = case_documents[document_id]["storage_key"]

    result = verify_document(document_id, case_id, storage_key)

    assert result["malware_scan_status"] == "INFECTED"
    assert result["status"] == "rejected"
    case_documents.clear()
    status_response = client.get(
        f"/api/v1/documents/{document_id}/status", headers=headers
    )
    assert status_response.json()["malware_scan_status"] == "INFECTED"
    assert status_response.json()["status"] == "FAILED"


def test_queue_failure_returns_503_and_rolls_back_file_and_record(monkeypatch):
    def unavailable_queue(*args, **kwargs):
        raise OSError("queue unavailable")

    monkeypatch.setattr(settings, "celery_dispatch_enabled", True)
    monkeypatch.setattr(verify_document, "delay", unavailable_queue)
    headers = auth_headers(uuid4())
    case_id = create_case(headers)

    response = upload(case_id, headers, "statement.pdf", make_pdf_bytes("queue"))

    assert response.status_code == 503
    assert case_documents == {}
    assert pending_processing_tasks == []
    assert case_records[case_id]["documents"] == []
    assert case_records[case_id]["status"] == "DRAFT"
    assert list(settings.quarantine_storage_path.glob("*")) == []
