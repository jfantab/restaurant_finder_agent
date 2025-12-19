"""Neon DB connection module for restaurant finder agent."""

import os
from contextlib import contextmanager
from typing import Optional, Generator, Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class NeonDBConnection:
    """Manages connections to Neon PostgreSQL database."""

    _instance: Optional['NeonDBConnection'] = None
    _pool: Optional[pool.SimpleConnectionPool] = None

    def __new__(cls) -> 'NeonDBConnection':
        """Singleton pattern to ensure single connection pool."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the connection pool if not already initialized."""
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize the connection pool with Neon DB credentials."""
        database_url = os.getenv("NEON_DATABASE_URL")

        if not database_url:
            raise ValueError(
                "NEON_DATABASE_URL environment variable is not set. "
                "Please set it to your Neon PostgreSQL connection string."
            )

        self._pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url
        )

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get a connection from the pool.

        Yields:
            A psycopg2 connection object.
        """
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True) -> Generator[Any, None, None]:
        """Get a cursor from a pooled connection.

        Args:
            dict_cursor: If True, returns results as dictionaries.

        Yields:
            A psycopg2 cursor object.
        """
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        dict_cursor: bool = True
    ) -> list[dict]:
        """Execute a SELECT query and return results.

        Args:
            query: SQL query string.
            params: Query parameters for parameterized queries.
            dict_cursor: If True, returns results as dictionaries.

        Returns:
            List of query results.
        """
        with self.get_cursor(dict_cursor=dict_cursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_write(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE query.

        Args:
            query: SQL query string.
            params: Query parameters for parameterized queries.

        Returns:
            Number of affected rows.
        """
        with self.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None


def get_db_connection() -> NeonDBConnection:
    """Get the singleton NeonDBConnection instance.

    Returns:
        NeonDBConnection instance.
    """
    return NeonDBConnection()
