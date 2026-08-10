from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from botocore.exceptions import ClientError

from app.api.v1.endpoints.cases import case_documents
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document as DocumentModel
from app.schemas.case import DocumentStatus
from app.services import storage
from app.services.antivirus import MalwareScanResult, ScanOutcome
from app.workers import tasks
from tests import make_pdf_bytes
from tests.test_secure_document_upload import create_case, upload
from tests.test_tenant_isolation import auth_headers, client


class FakeMinioClient:
    def __init__(self):
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}

    @staticmethod
    def _missing(operation: str, code: str = "404") -> ClientError:
        return ClientError(
            {
                "Error": {"Code": code},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            operation,
        )

    def head_bucket(self, *, Bucket: str):
        if Bucket not in self.buckets:
            raise self._missing("HeadBucket", "NoSuchBucket")

    def create_bucket(self, *, Bucket: str, **_kwargs):
        self.buckets.add(Bucket)

    def upload_file(self, filename: str, bucket: str, key: str, ExtraArgs=None):
        assert ExtraArgs["Metadata"]["state"] == "quarantined"
        self.objects[(bucket, key)] = Path(filename).read_bytes()

    def download_file(self, bucket: str, key: str, filename: str):
        try:
            content = self.objects[(bucket, key)]
        except KeyError:
            raise self._missing("GetObject", "NoSuchKey") from None
        Path(filename).write_bytes(content)

    def head_object(self, *, Bucket: str, Key: str):
        if (Bucket, Key) not in self.objects:
            raise self._missing("HeadObject", "NoSuchKey")

    def delete_object(self, *, Bucket: str, Key: str):
        self.objects.pop((Bucket, Key), None)


def test_worker_persists_clear_processing_stages(monkeypatch):
    headers = auth_headers(uuid4())
    case_id = create_case(headers, "Status stages")
    created = upload(
        case_id,
        headers,
        "stages.pdf",
        make_pdf_bytes("status stages"),
    )
    assert created.status_code == 202
    document_id = created.json()["document_id"]
    storage_key = case_documents[document_id]["storage_key"]
    recorded_statuses: list[DocumentStatus] = []
    update_record = tasks._update_document_record

    def capture_update(document_id, malware_status, document_status):
        recorded_statuses.append(document_status)
        update_record(document_id, malware_status, document_status)

    monkeypatch.setattr(tasks, "_update_document_record", capture_update)
    monkeypatch.setattr(
        tasks,
        "scan_file",
        lambda _path: ScanOutcome(MalwareScanResult.CLEAN, "No malware detected"),
    )

    result = tasks.verify_document(document_id, case_id, storage_key)

    assert result["status"] == "completed"
    assert recorded_statuses == [
        DocumentStatus.SCANNING,
        DocumentStatus.PROCESSING,
        DocumentStatus.COMPLETED,
    ]


def test_expiry_deletes_content_but_retains_audit_metadata():
    headers = auth_headers(uuid4())
    case_id = create_case(headers, "Retention policy")
    created = upload(
        case_id,
        headers,
        "expired.pdf",
        make_pdf_bytes("expired document"),
    )
    document_id = created.json()["document_id"]
    storage_key = case_documents[document_id]["storage_key"]
    stored_path = settings.quarantine_storage_path / storage_key
    assert stored_path.is_file()

    with SessionLocal() as session:
        document = session.get(DocumentModel, UUID(document_id))
        assert document is not None
        document.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        session.commit()

    result = tasks.expire_quarantined_documents()

    assert result == {"status": "completed", "expired": 1, "errors": 0}
    assert not stored_path.exists()
    case_documents.clear()
    response = client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["storage_available"] is False
    assert response.json()["storage_deleted_at"] is not None
    assert response.json()["status"] == DocumentStatus.FAILED.value
    assert any("retention limit" in item for item in response.json()["observations"])

    retry = client.post(
        f"/api/v1/documents/{document_id}/retry", headers=headers
    )
    assert retry.status_code == 409


def test_minio_backend_stores_materializes_and_deletes_objects(monkeypatch):
    fake_minio = FakeMinioClient()
    monkeypatch.setattr(settings, "storage_backend", "minio")
    monkeypatch.setattr(storage, "_minio_client", lambda: fake_minio)
    headers = auth_headers(uuid4())
    case_id = create_case(headers, "MinIO storage")
    content = make_pdf_bytes("minio document")

    created = upload(case_id, headers, "minio.pdf", content)

    assert created.status_code == 202
    document_id = created.json()["document_id"]
    storage_key = case_documents[document_id]["storage_key"]
    object_id = (settings.minio_bucket_name, storage_key)
    assert fake_minio.objects[object_id] == content
    assert not (settings.quarantine_storage_path / storage_key).exists()
    assert storage.quarantined_exists(storage_key) is True
    with storage.materialize_quarantined(storage_key) as local_path:
        assert local_path.read_bytes() == content
        materialized_path = local_path
    assert not materialized_path.exists()

    deleted = client.delete(f"/api/v1/documents/{document_id}", headers=headers)

    assert deleted.status_code == 204
    assert object_id not in fake_minio.objects
