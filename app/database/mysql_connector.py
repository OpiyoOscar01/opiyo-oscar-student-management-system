import time
from contextlib import contextmanager
from typing import Any, Optional

import mysql.connector
from mysql.connector import pooling, Error

from app.config import settings
from app.middleware.logging import app_logger, get_request_id, log_json

connection_pool: Optional[pooling.MySQLConnectionPool] = None

pool_stats = {
    "acquired": 0,
    "released": 0,
    "failed_acquires": 0,
    "total_queries": 0,
}


def init_connection_pool():
    global connection_pool

    if connection_pool is not None:
        return connection_pool

    db_config = {
        "host": settings.MYSQL_HOST,
        "port": settings.MYSQL_PORT,
        "user": settings.MYSQL_USER,
        "password": settings.MYSQL_PASSWORD,
        "database": settings.MYSQL_DATABASE,
        "connection_timeout": settings.MYSQL_CONNECT_TIMEOUT,
        "autocommit": False,
    }

    connection_pool = pooling.MySQLConnectionPool(
        pool_name=settings.MYSQL_POOL_NAME,
        pool_size=settings.MYSQL_POOL_SIZE,
        pool_reset_session=settings.MYSQL_POOL_RESET_SESSION,
        **db_config,
    )

    log_json(
        "info",
        "db_pool_initialized",
        pool_name=settings.MYSQL_POOL_NAME,
        pool_size=settings.MYSQL_POOL_SIZE,
        host=settings.MYSQL_HOST,
        database=settings.MYSQL_DATABASE,
    )
    return connection_pool


def get_connection():
    global connection_pool

    if connection_pool is None:
        init_connection_pool()

    last_error = None
    for attempt in range(1, settings.MYSQL_MAX_RETRIES + 1):
        try:
            conn = connection_pool.get_connection()
            pool_stats["acquired"] += 1
            return conn
        except Error as exc:
            last_error = exc
            pool_stats["failed_acquires"] += 1
            log_json(
                "warning",
                "db_connection_retry",
                attempt=attempt,
                max_retries=settings.MYSQL_MAX_RETRIES,
                error=str(exc),
                request_id=get_request_id(),
            )
            time.sleep(settings.MYSQL_RETRY_DELAY_SECONDS)

    raise last_error


@contextmanager
def get_db_connection():
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        finally:
            pool_stats["released"] += 1


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    *,
    fetch_one: bool = False,
    fetch_all: bool = False,
    commit: bool = False,
    dictionary: bool = True,
) -> Any:
    start = time.perf_counter()
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=dictionary)
        try:
            cursor.execute(query, params or ())
            pool_stats["total_queries"] += 1

            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()

            if commit:
                conn.commit()

            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_json(
                "info",
                "db_query",
                duration_ms=duration_ms,
                request_id=get_request_id(),
                query_preview=" ".join(query.strip().split())[:180],
            )
            return result
        except Exception:
            if commit:
                conn.rollback()
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            app_logger.exception(
                {
                    "event": "db_query_error",
                    "duration_ms": duration_ms,
                    "request_id": get_request_id(),
                    "query_preview": " ".join(query.strip().split())[:180],
                }
            )
            raise
        finally:
            cursor.close()


def ping_database() -> bool:
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        return True
    except Exception:
        return False


def get_pool_status():
    in_use = max(pool_stats["acquired"] - pool_stats["released"], 0)
    return {
        "pool_name": settings.MYSQL_POOL_NAME,
        "pool_size": settings.MYSQL_POOL_SIZE,
        "acquired_connections": pool_stats["acquired"],
        "released_connections": pool_stats["released"],
        "in_use_connections": in_use,
        "failed_acquires": pool_stats["failed_acquires"],
        "total_queries": pool_stats["total_queries"],
    }
