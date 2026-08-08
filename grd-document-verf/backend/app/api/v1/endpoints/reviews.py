from fastapi import APIRouter, Depends

from app.api.v1.endpoints.documents import verification_cases
from app.core.permissions import Permission
from app.core.security import AuthContext, require_permission

router = APIRouter()


@router.get("/queue")
async def review_queue(
    context: AuthContext = Depends(require_permission(Permission.FINDING_REVIEW)),
):
    items = [
        result
        for result in verification_cases.values()
        if result.tenant_id == str(context.tenant_id) and result.human_review_required
    ]
    return {"items": items}
