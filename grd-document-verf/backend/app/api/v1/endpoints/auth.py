import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt

from app.core.config import settings
from app.core.permissions import ROLE_PERMISSIONS, Role
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.rate_limit import enforce_login_rate_limit

router = APIRouter()
LOCAL_NAMESPACE = UUID("70df075f-a444-4dcc-85b4-640ac956c1e7")


def _verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, expected = encoded.split("$", 1)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 600_000
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
async def login(payload: LoginRequest):
    if not settings.local_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Local login is not available"
        )
    accounts = json.loads(settings.local_accounts_json.get_secret_value())
    email = payload.email.strip().lower()
    account = next((item for item in accounts if item["email"].lower() == email), None)
    if account is None or not _verify_password(
        payload.password, account["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    role = Role(account["role"])
    if role != payload.requested_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selected access does not match this account",
        )
    tenant_id = uuid5(LOCAL_NAMESPACE, f"tenant:{account['tenant']}")
    user_id = uuid5(LOCAL_NAMESPACE, f"user:{email}")
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role.value,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(hours=8),
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return TokenResponse(
        access_token=token,
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        display_name=account["name"],
        email=email,
        role=role,
        permissions=sorted(ROLE_PERMISSIONS[role], key=lambda item: item.value),
    )
