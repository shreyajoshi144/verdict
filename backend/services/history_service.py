import json
from typing import List
from backend.models.models import SearchHistoryItem
from backend.database.database import execute_query
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def get_history(user_id: int, limit: int = 20) -> List[SearchHistoryItem]:
    rows = execute_query(
        """SELECT id, user_id, query, filters, result_count, created_at
           FROM search_history WHERE user_id = %s
           ORDER BY created_at DESC LIMIT %s""",
        (user_id, limit)
    )
    items = []
    for r in rows:
        filters = r["filters"]
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except Exception:
                filters = {}
        items.append(SearchHistoryItem(
            id=r["id"],
            user_id=r["user_id"],
            query=r["query"],
            filters=filters,
            result_count=r["result_count"],
            created_at=r["created_at"],
        ))
    return items


def delete_history_item(user_id: int, history_id: int) -> bool:
    try:
        execute_query(
            "DELETE FROM search_history WHERE id = %s AND user_id = %s",
            (history_id, user_id),
            fetch=False
        )
        return True
    except Exception as e:
        logger.error(f"Delete history item failed: {e}")
        raise


def clear_history(user_id: int) -> bool:
    try:
        execute_query(
            "DELETE FROM search_history WHERE user_id = %s",
            (user_id,),
            fetch=False
        )
        return True
    except Exception as e:
        logger.error(f"Clear history failed: {e}")
        raise
