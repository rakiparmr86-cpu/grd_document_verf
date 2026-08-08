from pydantic import BaseModel

from app.core.permissions import Permission, Role


class LoginRequest(BaseModel):
    email: str
    password: str
    requested_role: Role
    business_type: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    display_name: str
    email: str
    role: Role
    permissions: list[Permission]
