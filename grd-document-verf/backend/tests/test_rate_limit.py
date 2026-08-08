from uuid import uuid4

from redis.exceptions import RedisError

from app.core.config import settings
from app.services import rate_limit
from tests import make_pdf_bytes
from tests.test_tenant_isolation import auth_headers, client


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}

    async def eval(self, _script, _number_of_keys, key, expiry):
        self.counts[key] = self.counts.get(key, 0) + 1
        return [self.counts[key], int(expiry)]

    async def aclose(self):
        return None


class UnavailableRedis(FakeRedis):
    async def eval(self, _script, _number_of_keys, key, expiry):
        raise RedisError("Redis is unavailable")


def enable_rate_limits(monkeypatch, redis_client: FakeRedis) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_fail_open", False)
    monkeypatch.setattr(rate_limit, "_redis_client", redis_client)


def test_general_api_limit_is_enforced_per_authenticated_user(monkeypatch):
    enable_rate_limits(monkeypatch, FakeRedis())
    monkeypatch.setattr(settings, "api_rate_limit_user_requests", 2)
    monkeypatch.setattr(settings, "api_rate_limit_tenant_requests", 20)
    headers = auth_headers(uuid4())

    first = client.get("/api/v1/cases", headers=headers)
    second = client.get("/api/v1/cases", headers=headers)
    limited = client.get("/api/v1/cases", headers=headers)

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Remaining"] == "1"
    assert second.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] == "0"
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_general_api_limit_is_also_enforced_across_tenant_users(monkeypatch):
    enable_rate_limits(monkeypatch, FakeRedis())
    monkeypatch.setattr(settings, "api_rate_limit_user_requests", 10)
    monkeypatch.setattr(settings, "api_rate_limit_tenant_requests", 2)
    tenant_id = uuid4()

    assert client.get(
        "/api/v1/cases", headers=auth_headers(tenant_id)
    ).status_code == 200
    assert client.get(
        "/api/v1/cases", headers=auth_headers(tenant_id)
    ).status_code == 200
    limited = client.get("/api/v1/cases", headers=auth_headers(tenant_id))

    assert limited.status_code == 429
    assert limited.json()["detail"] == "Rate limit exceeded. Try again later."


def test_upload_limit_is_stricter_than_general_api_limit(monkeypatch):
    enable_rate_limits(monkeypatch, FakeRedis())
    monkeypatch.setattr(settings, "api_rate_limit_user_requests", 100)
    monkeypatch.setattr(settings, "api_rate_limit_tenant_requests", 100)
    monkeypatch.setattr(settings, "upload_rate_limit_user_requests", 1)
    monkeypatch.setattr(settings, "upload_rate_limit_tenant_requests", 20)
    headers = auth_headers(uuid4())
    created = client.post(
        "/api/v1/cases",
        headers=headers,
        json={"name": "Rate-limited upload case"},
    )
    assert created.status_code == 201
    case_id = created.json()["id"]

    def upload(content: str):
        return client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=headers,
            data={"document_type": "bank_statement"},
            files={
                "file": (
                    f"{content}.pdf",
                    make_pdf_bytes(content),
                    "application/pdf",
                )
            },
        )

    assert upload("first").status_code == 202
    limited = upload("second")

    assert limited.status_code == 429
    assert limited.headers["X-RateLimit-Limit"] == "1"


def test_redis_failure_blocks_requests_when_configured_fail_closed(monkeypatch):
    enable_rate_limits(monkeypatch, UnavailableRedis())

    response = client.get("/api/v1/cases", headers=auth_headers(uuid4()))

    assert response.status_code == 503
    assert response.json()["detail"] == "Rate limiting service is unavailable"
