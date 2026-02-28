# -*- coding: utf-8 -*-
"""Database connection management."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import aiomysql
from aiomysql import Connection, Pool

from config import get_settings


class Database:
    """Database connection pool manager."""

    _pool: Optional[Pool] = None

    @classmethod
    async def get_pool(cls) -> Pool:
        """Get or create database connection pool."""
        if cls._pool is None:
            settings = get_settings()
            cls._pool = await aiomysql.create_pool(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                db=settings.mysql_database,
                charset="utf8mb4",
                autocommit=True,
                minsize=1,
                maxsize=10,
                # Connection keep-alive settings
                pool_recycle=1800,  # Recycle connections after 30 minutes
                connect_timeout=10,  # Connection timeout in seconds
            )
        return cls._pool

    @classmethod
    async def close_pool(cls) -> None:
        """Close database connection pool."""
        if cls._pool is not None:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None

    @classmethod
    @asynccontextmanager
    async def get_connection(cls) -> AsyncGenerator[Connection, None]:
        """Get a database connection from the pool."""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            yield conn


async def get_db() -> AsyncGenerator[Connection, None]:
    """FastAPI dependency for database connection."""
    async with Database.get_connection() as conn:
        yield conn
