"""
Test-only fake DB. Monkeypatches execute_query/execute_many on every service
module that imported them directly (they used `from ... import execute_query`,
so patching the database module alone wouldn't reach already-bound names).
"""
import re
import itertools
from datetime import datetime

_ids = itertools.count(1)
TABLES = {
    "users": [],
    "wishlist": [],
    "search_history": [],
    "budget_plans": [],
    "products": [],
}


def _next_id():
    return next(_ids)


def fake_execute_query(query, params=None, fetch=True):
    q = " ".join(query.split()).upper()
    params = params or ()

    if q.startswith("SELECT ID FROM USERS WHERE EMAIL"):
        return [{"id": u["id"]} for u in TABLES["users"] if u["email"] == params[0]]

    if q.startswith("SELECT ID, NAME, EMAIL, PASSWORD_HASH FROM USERS WHERE EMAIL"):
        return [u for u in TABLES["users"] if u["email"] == params[0]]

    if q.startswith("SELECT ID, NAME, EMAIL FROM USERS WHERE ID"):
        return [{"id": u["id"], "name": u["name"], "email": u["email"]} for u in TABLES["users"] if u["id"] == params[0]]

    if q.startswith("INSERT INTO USERS"):
        uid = _next_id()
        TABLES["users"].append({"id": uid, "name": params[0], "email": params[1], "password_hash": params[2]})
        return uid

    if q.startswith("INSERT INTO WISHLIST"):
        wid = _next_id()
        TABLES["wishlist"].append({
            "id": wid, "user_id": params[0], "product_name": params[1], "website": params[2],
            "price": params[3], "discount": params[4], "rating": params[5], "image_url": params[6],
            "product_url": params[7], "brand": params[8], "saved_at": datetime.now(),
        })
        return wid

    if q.startswith("SELECT ID, USER_ID, PRODUCT_NAME"):
        return [w for w in TABLES["wishlist"] if w["user_id"] == params[0]]

    if q.startswith("DELETE FROM WISHLIST WHERE ID"):
        TABLES["wishlist"][:] = [w for w in TABLES["wishlist"] if not (w["id"] == params[0] and w["user_id"] == params[1])]
        return None

    if q.startswith("DELETE FROM WISHLIST WHERE USER_ID"):
        TABLES["wishlist"][:] = [w for w in TABLES["wishlist"] if w["user_id"] != params[0]]
        return None

    if q.startswith("INSERT INTO SEARCH_HISTORY"):
        hid = _next_id()
        TABLES["search_history"].append({
            "id": hid, "user_id": params[0], "query": params[1], "filters": params[2],
            "result_count": params[3], "created_at": datetime.now(),
        })
        return hid

    if q.startswith("SELECT ID, USER_ID, QUERY"):
        rows = [h for h in TABLES["search_history"] if h["user_id"] == params[0]]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[:params[1]]

    if q.startswith("DELETE FROM SEARCH_HISTORY WHERE ID"):
        TABLES["search_history"][:] = [h for h in TABLES["search_history"] if not (h["id"] == params[0] and h["user_id"] == params[1])]
        return None

    if q.startswith("DELETE FROM SEARCH_HISTORY WHERE USER_ID"):
        TABLES["search_history"][:] = [h for h in TABLES["search_history"] if h["user_id"] != params[0]]
        return None

    if q.startswith("INSERT INTO BUDGET_PLANS"):
        bid = _next_id()
        TABLES["budget_plans"].append({
            "id": bid, "user_id": params[0], "budget": params[1], "category": params[2],
            "description": params[3], "ai_plan": params[4], "created_at": datetime.now(),
        })
        return bid

    if q.startswith("SELECT ID, BUDGET, CATEGORY"):
        rows = [b for b in TABLES["budget_plans"] if b["user_id"] == params[0]]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[:10]

    if q.startswith("DELETE FROM PRODUCTS"):
        TABLES["products"][:] = [p for p in TABLES["products"] if p.get("search_query") != params[0]]
        return None

    raise AssertionError(f"fake_execute_query: unhandled query: {query}")


def fake_execute_many(query, params_list):
    q = " ".join(query.split()).upper()
    if q.startswith("INSERT INTO PRODUCTS"):
        for row in params_list:
            TABLES["products"].append({
                "name": row[0], "website": row[1], "price": row[2], "original_price": row[3],
                "discount": row[4], "rating": row[5], "rating_count": row[6], "image_url": row[7],
                "product_url": row[8], "brand": row[9], "category": row[10], "search_query": row[11],
            })
        return len(params_list)
    raise AssertionError(f"fake_execute_many: unhandled query: {query}")


def patch_all():
    """Patch execute_query/execute_many on every module that imported them directly."""
    import backend.services.wishlist_service as wishlist_service
    import backend.services.history_service as history_service
    import backend.services.budget_service as budget_service
    import backend.services.product_service as product_service
    import backend.services.auth_service as auth_service

    for mod in (wishlist_service, history_service, budget_service, product_service, auth_service):
        mod.execute_query = fake_execute_query
    product_service.execute_many = fake_execute_many
