from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.endpoints.documents import verification_cases
from app.core.permissions import Permission
from app.core.security import AuthContext, require_permission
from app.schemas.verification import VerificationResult

router = APIRouter()


@router.get("/{case_id}", response_model=VerificationResult)
async def get_verification_result(
    case_id: str,
    context: AuthContext = Depends(require_permission(Permission.CASE_VIEW)),
):
    result = verification_cases.get(case_id)
    if result is None or result.tenant_id != str(context.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Verification case not found"
        )
    return result
