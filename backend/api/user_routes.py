from fastapi import APIRouter, HTTPException, Depends
from backend.models.models import WishlistAddRequest, BudgetRequest, UserPublic
from backend.services import wishlist_service, history_service, budget_service
from backend.api.auth_routes import get_current_user, require_owner
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/user", tags=["User"])


# ── Wishlist ──────────────────────────────────────────────────────────────────

@router.get("/wishlist/{user_id}")
def get_wishlist(user_id: int, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        items = wishlist_service.get_wishlist(user_id)
        return {"items": [i.dict() for i in items], "count": len(items)}
    except Exception as e:
        logger.error(f"Get wishlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wishlist/add")
def add_to_wishlist(request: WishlistAddRequest, current_user: UserPublic = Depends(get_current_user)):
    # Ignore whatever user_id the client sent — it's always the caller's own.
    request.user_id = current_user.id
    try:
        result = wishlist_service.add_to_wishlist(request)
        return {"success": True, "wishlist_id": result["wishlist_id"], "message": "Added to wishlist"}
    except Exception as e:
        logger.error(f"Add wishlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wishlist/{user_id}/clear")
def clear_wishlist(user_id: int, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        wishlist_service.clear_wishlist(user_id)
        return {"success": True, "message": "Wishlist cleared"}
    except Exception as e:
        logger.error(f"Clear wishlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wishlist/{user_id}/{wishlist_id}")
def remove_from_wishlist(user_id: int, wishlist_id: int, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        wishlist_service.remove_from_wishlist(user_id, wishlist_id)
        return {"success": True, "message": "Removed from wishlist"}
    except Exception as e:
        logger.error(f"Remove wishlist error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Search History ────────────────────────────────────────────────────────────

@router.get("/history/{user_id}")
def get_history(user_id: int, limit: int = 20, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        items = history_service.get_history(user_id, limit)
        return {"items": [i.dict() for i in items], "count": len(items)}
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{user_id}/clear")
def clear_history(user_id: int, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        history_service.clear_history(user_id)
        return {"success": True, "message": "History cleared"}
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{user_id}/{history_id}")
def delete_history_item(user_id: int, history_id: int, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        history_service.delete_history_item(user_id, history_id)
        return {"success": True, "message": "History item deleted"}
    except Exception as e:
        logger.error(f"Delete history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Budget ────────────────────────────────────────────────────────────────────

@router.post("/budget/plan")
def create_budget_plan(request: BudgetRequest, current_user: UserPublic = Depends(get_current_user)):
    request.user_id = current_user.id
    try:
        result = budget_service.create_budget_plan(request)
        return result.dict()
    except Exception as e:
        logger.error(f"Budget plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget/history/{user_id}")
def get_budget_history(user_id: int, current_user: UserPublic = Depends(get_current_user)):
    require_owner(user_id, current_user)
    try:
        rows = budget_service.get_budget_history(user_id)
        return {"plans": rows}
    except Exception as e:
        logger.error(f"Budget history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
