import mysql.connector
from mysql.connector import pooling
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="verdict_pool",
                pool_size=5,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                charset="utf8mb4",
                autocommit=False,
            )
            logger.info("MySQL connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return _pool

def get_connection():
    return get_pool().get_connection()

def execute_query(query: str, params: tuple = None, fetch: bool = True):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Query error: {e} | Query: {query}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_many(query: str, params_list: list):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Batch query error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
