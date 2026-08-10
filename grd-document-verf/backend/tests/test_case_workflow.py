from uuid import uuid4

from tests import make_pdf_bytes
from tests.test_tenant_isolation import auth_headers, client


def test_case_supports_multiple_documents_and_records_history():
    tenant_id = uuid4()
    headers = auth_headers(tenant_id)
    created = client.post(
        "/api/v1/cases",
        headers=headers,
        json={"name": "Loan Application Case", "reference": "LN-1001"},
    )
    assert created.status_code == 201
    case_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"

    for filename, document_type in (
        ("salary-1.pdf", "salary_slip"),
        ("salary-2.pdf", "salary_slip"),
        ("statement.pdf", "bank_statement"),
    ):
        response = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=headers,
            data={"document_type": document_type},
            files={"file": (filename, make_pdf_bytes(filename), "application/pdf")},
        )
        assert response.status_code == 202

    case = client.get(f"/api/v1/cases/{case_id}", headers=headers).json()
    assert case["status"] == "UPLOADED"
    assert len(case["documents"]) == 3

    history = client.get(f"/api/v1/cases/{case_id}/history", headers=headers).json()
    document_events = [
        event for event in history if event["entity_type"] == "document"
    ]
    assert [event["to_status"] for event in document_events].count("UPLOADED") == 3
    assert [event["to_status"] for event in document_events].count("QUARANTINED") == 3
    assert any(
        event["from_status"] == "DRAFT" and event["to_status"] == "UPLOADED"
        for event in history
    )


def test_invalid_status_jump_is_rejected_and_not_recorded():
    tenant_id = uuid4()
    headers = auth_headers(tenant_id)
    case_id = client.post(
        "/api/v1/cases", headers=headers, json={"name": "Test case"}
    ).json()["id"]
    response = client.post(
        f"/api/v1/cases/{case_id}/status",
        headers=headers,
        json={"status": "VERIFIED", "reason": "Invalid jump"},
    )
    assert response.status_code in (403, 409)
    history = client.get(f"/api/v1/cases/{case_id}/history", headers=headers).json()
    assert all(event["to_status"] != "VERIFIED" for event in history)


def test_other_tenant_cannot_access_case_or_history():
    owner_headers = auth_headers(uuid4())
    case_id = client.post(
        "/api/v1/cases", headers=owner_headers, json={"name": "Private case"}
    ).json()["id"]
    foreign_headers = auth_headers(uuid4())
    assert (
        client.get(f"/api/v1/cases/{case_id}", headers=foreign_headers).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/cases/{case_id}/history", headers=foreign_headers
        ).status_code
        == 404
    )
