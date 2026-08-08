from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.permissions import ROLE_PERMISSIONS, Permission, Role

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class AuthContext:
    tenant_id: UUID
    user_id: UUID
    role: Role


def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthContext:
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        return AuthContext(
            tenant_id=UUID(claims["tenant_id"]),
            user_id=UUID(claims["sub"]),
            role=Role(claims["role"]),
        )
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def require_permission(permission: Permission):
    def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if permission not in ROLE_PERMISSIONS[context.role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )
        return context

    return dependency
