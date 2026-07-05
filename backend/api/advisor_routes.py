from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.models import AdvisorRequest, AdvisorResponse, ComparisonRequest, ComparisonResponse, UserPublic
from backend.services import advisor_service, comparison_service
from backend.api.auth_routes import get_current_user
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/advisor", tags=["Advisor"])


@router.post("/chat", response_model=AdvisorResponse)
def chat(request: AdvisorRequest, current_user: UserPublic = Depends(get_current_user)):
    try:
        return advisor_service.chat(request)
    except Exception as e:
        logger.error(f"Advisor chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advisor error: {str(e)}"
        )


@router.post("/compare", response_model=ComparisonResponse)
def compare(request: ComparisonRequest, current_user: UserPublic = Depends(get_current_user)):
    if len(request.products) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 products required for comparison"
        )
    try:
        return comparison_service.compare_products(request.products)
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )
