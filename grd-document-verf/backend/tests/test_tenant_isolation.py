import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-with-at-least-32-characters")

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import app
from tests import make_pdf_bytes

client = TestClient(app)


def auth_headers(tenant_id, role="verification_executive"):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "tenant_id": str(tenant_id),
            "role": role,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def submit_case(tenant_id, role="verification_executive"):
    return client.post(
        "/api/v1/documents",
        headers=auth_headers(tenant_id, role),
        data={"document_type": "bank_statement"},
        files={
            "file": ("statement.pdf", make_pdf_bytes(str(tenant_id)), "application/pdf")
        },
    )


def test_tenant_cannot_read_another_tenants_case():
    bank_a, bank_b = uuid4(), uuid4()
    created = submit_case(bank_a)
    assert created.status_code == 202
    case_id = created.json()["case_id"]

    assert (
        client.get(
            f"/api/v1/verification/{case_id}", headers=auth_headers(bank_a)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/verification/{case_id}", headers=auth_headers(bank_b)
        ).status_code
        == 404
    )


def test_api_client_can_submit_but_cannot_view_results():
    tenant_id = uuid4()
    created = submit_case(tenant_id, "api_client")
    assert created.status_code == 202
    response = client.get(
        f"/api/v1/verification/{created.json()['case_id']}",
        headers=auth_headers(tenant_id, "api_client"),
    )
    assert response.status_code == 403


def test_auditor_cannot_submit_documents():
    assert submit_case(uuid4(), "auditor").status_code == 403
