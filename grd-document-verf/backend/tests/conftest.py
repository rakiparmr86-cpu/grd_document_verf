import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-with-at-least-32-characters")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")

from app.api.v1.endpoints.cases import (
    case_documents,
    case_records,
    document_hash_index,
    status_history,
)
from app.api.v1.endpoints.documents import verification_cases
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.services.storage import _create_s3_client
from app.workers.tasks import pending_processing_tasks


@pytest.fixture(autouse=True)
def isolate_in_memory_repositories(tmp_path, monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    case_documents.clear()
    case_records.clear()
    document_hash_index.clear()
    status_history.clear()
    verification_cases.clear()
    pending_processing_tasks.clear()
    monkeypatch.setattr(settings, "quarantine_storage_path", tmp_path / "quarantine")
    monkeypatch.setattr(settings, "max_upload_size_bytes", 25 * 1024 * 1024)
    monkeypatch.setattr(settings, "max_document_pages", 100)
    monkeypatch.setattr(settings, "max_files_per_case", 20)
    monkeypatch.setattr(settings, "allow_tiff_uploads", False)
    monkeypatch.setattr(settings, "password_protected_pdf_policy", "reject")
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "document_expiry_enabled", True)
    monkeypatch.setattr(settings, "document_retention_days", 30)
    monkeypatch.setattr(settings, "document_expiry_batch_size", 100)
    monkeypatch.setattr(settings, "celery_dispatch_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    _create_s3_client.cache_clear()
    yield
    _create_s3_client.cache_clear()
