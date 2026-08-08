from fastapi import APIRouter, Depends

from app.api.v1.endpoints import auth, cases, documents, reviews, verification
from app.services.rate_limit import enforce_api_rate_limit

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
protected = [Depends(enforce_api_rate_limit)]
api_router.include_router(
    cases.router, prefix="/cases", tags=["Cases"], dependencies=protected
)
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
    dependencies=protected,
)
api_router.include_router(
    verification.router,
    prefix="/verification",
    tags=["Verification"],
    dependencies=protected,
)
api_router.include_router(
    reviews.router,
    prefix="/reviews",
    tags=["Human Review"],
    dependencies=protected,
)
