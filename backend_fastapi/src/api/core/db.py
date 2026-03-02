from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Sequence

import psycopg
from psycopg.rows import dict_row

from src.api.core.settings import get_settings


@contextmanager
def _get_conn() -> Iterator[psycopg.Connection]:
    settings = get_settings()
    conn = psycopg.connect(settings.POSTGRES_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


# PUBLIC_INTERFACE
def fetch_one(query: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
    """Execute a query and return a single row.

    Args:
        query: SQL query.
        params: SQL parameters.

    Returns:
        Row as dict if found, else None.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
            return dict(row) if row else None


# PUBLIC_INTERFACE
def fetch_all(query: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    """Execute a query and return all rows.

    Args:
        query: SQL query.
        params: SQL parameters.

    Returns:
        List of rows as dicts.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# PUBLIC_INTERFACE
def execute(query: str, params: Optional[Sequence[Any]] = None) -> int:
    """Execute a statement and return affected row count.

    Args:
        query: SQL query.
        params: SQL parameters.

    Returns:
        Affected row count.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
            return cur.rowcount


# PUBLIC_INTERFACE
def execute_returning_one(query: str, params: Optional[Sequence[Any]] = None) -> Optional[Dict[str, Any]]:
    """Execute a statement with RETURNING and return one row.

    Args:
        query: SQL query (should include RETURNING).
        params: SQL parameters.

    Returns:
        Returned row dict if any.
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None


# PUBLIC_INTERFACE
def execute_many(query: str, params_seq: Sequence[Sequence[Any]]) -> int:
    """Execute many statements with same query.

    Args:
        query: SQL query.
        params_seq: Sequence of parameter sequences.

    Returns:
        Total number of affected rows (best-effort; psycopg may return sum of rowcounts).
    """
    total = 0
    with _get_conn() as conn:
        with conn.cursor() as cur:
            for params in params_seq:
                cur.execute(query, params)
                if cur.rowcount and cur.rowcount > 0:
                    total += cur.rowcount
            conn.commit()
    return total
