from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.models import ProductSearchRequest, ProductSearchResponse, UserPublic
from backend.services import product_service
from backend.api.auth_routes import get_current_user
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/search", response_model=ProductSearchResponse)
def search_products(request: ProductSearchRequest, current_user: UserPublic = Depends(get_current_user)):
    # The client can't spoof another user's history: the authenticated user's
    # id always wins over whatever (if anything) was sent in the request body.
    request.user_id = current_user.id
    try:
        products = product_service.search_products(request)
        return ProductSearchResponse(
            products=products,
            total=len(products),
            query=request.query,
        )
    except Exception as e:
        logger.error(f"Product search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Product search failed: {str(e)}"
        )
