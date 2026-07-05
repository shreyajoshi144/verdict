from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.models import InsightRequest, InsightResponse, UserPublic
from backend.services import insight_service
from backend.api.auth_routes import get_current_user
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/insights", tags=["Insights"])


@router.post("/generate", response_model=InsightResponse)
def generate_insights(request: InsightRequest, current_user: UserPublic = Depends(get_current_user)):
    try:
        return insight_service.generate_insights(request.products, request.query)
    except Exception as e:
        logger.error(f"Insight generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insight generation failed: {str(e)}"
        )
