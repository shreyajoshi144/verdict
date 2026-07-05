from typing import List
from backend.models.models import WishlistItem, WishlistAddRequest
from backend.database.database import execute_query
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def add_to_wishlist(request: WishlistAddRequest) -> dict:
    p = request.product
    try:
        wishlist_id = execute_query(
            """INSERT INTO wishlist
               (user_id, product_name, website, price, discount, rating, image_url, product_url, brand)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (request.user_id, p.name, p.website, p.price, p.discount,
             p.rating, p.image_url, p.product_url, p.brand),
            fetch=False
        )
        logger.info(f"Added to wishlist: {p.name} for user {request.user_id}")
        return {"wishlist_id": wishlist_id, "success": True}
    except Exception as e:
        logger.error(f"Wishlist add failed: {e}")
        raise


def remove_from_wishlist(user_id: int, wishlist_id: int) -> bool:
    try:
        execute_query(
            "DELETE FROM wishlist WHERE id = %s AND user_id = %s",
            (wishlist_id, user_id),
            fetch=False
        )
        logger.info(f"Removed wishlist item {wishlist_id} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Wishlist remove failed: {e}")
        raise


def get_wishlist(user_id: int) -> List[WishlistItem]:
    rows = execute_query(
        """SELECT id, user_id, product_name, website, price, discount, rating,
                  image_url, product_url, brand, saved_at
           FROM wishlist WHERE user_id = %s ORDER BY saved_at DESC""",
        (user_id,)
    )
    return [
        WishlistItem(
            id=r["id"],
            user_id=r["user_id"],
            product_name=r["product_name"],
            website=r["website"],
            price=float(r["price"]),
            discount=float(r["discount"] or 0),
            rating=float(r["rating"] or 0),
            image_url=r["image_url"],
            product_url=r["product_url"],
            brand=r["brand"],
            saved_at=r["saved_at"],
        )
        for r in rows
    ]


def clear_wishlist(user_id: int) -> bool:
    try:
        execute_query(
            "DELETE FROM wishlist WHERE user_id = %s",
            (user_id,),
            fetch=False
        )
        return True
    except Exception as e:
        logger.error(f"Wishlist clear failed: {e}")
        raise
