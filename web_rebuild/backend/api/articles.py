# -*- coding: utf-8 -*-
"""Article API routes."""

import logging
from typing import Any, Dict, List, Optional

from aiomysql import Connection
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db
from services.crawler import (
    DajialaAPIError,
    fetch_article_detail,
    fetch_article_list_by_name,
    parse_article_detail,
    parse_article_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


# Request/Response models
class FetchListRequest(BaseModel):
    """Request model for fetching article list."""

    name: str


class FetchDetailRequest(BaseModel):
    """Request model for fetching article detail."""

    url: str


class ArticleListItem(BaseModel):
    """Article list item in response."""

    id: int
    title: str
    url: str
    post_time: Optional[int]
    post_time_str: Optional[str]


class ArticleListResponse(BaseModel):
    """Response model for article list."""

    mp_nickname: str
    article_count: int
    articles: List[ArticleListItem]


class ArticleDetailItem(BaseModel):
    """Article detail item in response."""

    id: int
    title: str
    url: str
    pubtime: Optional[int]
    hashid: Optional[str]
    nick_name: Optional[str]
    author: Optional[str]
    content: Optional[str]


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    code: int = 0
    msg: str = "success"
    data: Optional[Any] = None


async def upsert_account(
    conn: Connection,
    mp_nickname: str,
    mp_wxid: Optional[str],
    mp_ghid: Optional[str],
) -> int:
    """Insert or update MP account, return account ID."""
    async with conn.cursor() as cur:
        # Try to find by ghid first
        if mp_ghid:
            await cur.execute(
                "SELECT id FROM wx_mp_account WHERE mp_ghid = %s LIMIT 1",
                (mp_ghid,),
            )
            row = await cur.fetchone()
            if row:
                await cur.execute(
                    "UPDATE wx_mp_account SET mp_nickname = %s, mp_wxid = %s WHERE id = %s",
                    (mp_nickname, mp_wxid, row[0]),
                )
                return row[0]

        # Try to find by wxid
        if mp_wxid:
            await cur.execute(
                "SELECT id FROM wx_mp_account WHERE mp_wxid = %s LIMIT 1",
                (mp_wxid,),
            )
            row = await cur.fetchone()
            if row:
                await cur.execute(
                    "UPDATE wx_mp_account SET mp_nickname = %s, mp_ghid = %s WHERE id = %s",
                    (mp_nickname, mp_ghid, row[0]),
                )
                return row[0]

        # Insert new account
        await cur.execute(
            "INSERT INTO wx_mp_account (mp_nickname, mp_wxid, mp_ghid) VALUES (%s, %s, %s)",
            (mp_nickname, mp_wxid, mp_ghid),
        )
        return cur.lastrowid


async def upsert_article_list(
    conn: Connection,
    account_id: int,
    article: Dict[str, Any],
) -> int:
    """Insert or update article list item, return article ID."""
    url = article["url"]

    async with conn.cursor() as cur:
        # Check if article exists by URL hash
        await cur.execute(
            "SELECT id FROM wx_article_list WHERE MD5(url) = MD5(%s) LIMIT 1",
            (url,),
        )
        row = await cur.fetchone()
        if row:
            # Update existing record
            await cur.execute(
                """
                UPDATE wx_article_list
                SET title = %s, post_time = %s, post_time_str = %s, fetched_at = NOW()
                WHERE id = %s
                """,
                (article["title"], article["post_time"], article["post_time_str"], row[0]),
            )
            return row[0]

        # Insert new record
        await cur.execute(
            """
            INSERT INTO wx_article_list (account_id, mp_nickname, title, url, post_time, post_time_str)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                account_id,
                article["mp_nickname"],
                article["title"],
                url,
                article["post_time"],
                article["post_time_str"],
            ),
        )
        return cur.lastrowid


async def upsert_article_detail(
    conn: Connection,
    article_list_id: Optional[int],
    detail: Dict[str, Any],
) -> int:
    """Insert or update article detail, return detail ID."""
    url = detail["url"]

    async with conn.cursor() as cur:
        # Check if detail exists by URL hash
        await cur.execute(
            "SELECT id FROM wx_article_detail WHERE MD5(url) = MD5(%s) LIMIT 1",
            (url,),
        )
        row = await cur.fetchone()
        if row:
            # Update existing record
            await cur.execute(
                """
                UPDATE wx_article_detail
                SET title = %s, pubtime = %s, hashid = %s, nick_name = %s, author = %s, content = %s, fetched_at = NOW()
                WHERE id = %s
                """,
                (
                    detail["title"],
                    detail["pubtime"],
                    detail["hashid"],
                    detail["nick_name"],
                    detail["author"],
                    detail["content"],
                    row[0],
                ),
            )
            return row[0]

        # Insert new record
        await cur.execute(
            """
            INSERT INTO wx_article_detail (article_list_id, title, url, pubtime, hashid, nick_name, author, content)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                article_list_id,
                detail["title"],
                url,
                detail["pubtime"],
                detail["hashid"],
                detail["nick_name"],
                detail["author"],
                detail["content"],
            ),
        )
        return cur.lastrowid


async def get_article_list_id_by_url(conn: Connection, url: str) -> Optional[int]:
    """Get article list ID by URL."""
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id FROM wx_article_list WHERE MD5(url) = MD5(%s) LIMIT 1",
            (url,),
        )
        row = await cur.fetchone()
        return row[0] if row else None


@router.post("/fetch-list", response_model=ApiResponse)
async def fetch_list(
    request: FetchListRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """
    Fetch article list for a WeChat MP account by name.

    This endpoint:
    1. Calls Dajiala API to get today's articles for the MP account
    2. Saves post_time, title, url, mp_nickname to database
    3. Returns the article list
    """
    try:
        # Fetch from Dajiala API
        api_response = await fetch_article_list_by_name(request.name)

        # Parse articles
        articles = parse_article_list(api_response, mp_name_fallback=request.name)

        if not articles:
            return ApiResponse(
                code=0,
                msg="success",
                data={
                    "mp_nickname": api_response.get("mp_nickname", request.name),
                    "article_count": 0,
                    "articles": [],
                },
            )

        # Get MP account info
        mp_nickname = articles[0]["mp_nickname"]
        mp_wxid = articles[0].get("mp_wxid")
        mp_ghid = articles[0].get("mp_ghid")

        # Upsert account
        account_id = await upsert_account(conn, mp_nickname, mp_wxid, mp_ghid)

        # Upsert articles
        saved_articles = []
        for article in articles:
            article_id = await upsert_article_list(conn, account_id, article)
            saved_articles.append(
                ArticleListItem(
                    id=article_id,
                    title=article["title"],
                    url=article["url"],
                    post_time=article.get("post_time"),
                    post_time_str=article.get("post_time_str"),
                )
            )

        return ApiResponse(
            code=0,
            msg="success",
            data={
                "mp_nickname": mp_nickname,
                "article_count": len(saved_articles),
                "articles": [a.model_dump() for a in saved_articles],
            },
        )

    except DajialaAPIError as e:
        logger.error(f"Dajiala API error: {e}")
        return ApiResponse(
            code=e.code,
            msg=e.message,
            data=None,
        )
    except Exception as e:
        logger.exception(f"Failed to fetch article list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-detail", response_model=ApiResponse)
async def fetch_detail(
    request: FetchDetailRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """
    Fetch article detail by URL.

    This endpoint:
    1. Calls Dajiala API to get article detail
    2. Saves title, url, pubtime, hashid, nick_name, author, content to database
    3. Returns the article detail
    """
    try:
        # Fetch from Dajiala API
        api_response = await fetch_article_detail(request.url)

        # Parse detail
        detail = parse_article_detail(api_response)

        # Find related article_list_id if exists
        article_list_id = await get_article_list_id_by_url(conn, request.url)

        # Upsert detail
        detail_id = await upsert_article_detail(conn, article_list_id, detail)

        return ApiResponse(
            code=0,
            msg="success",
            data={
                "id": detail_id,
                "title": detail["title"],
                "url": detail["url"],
                "pubtime": detail.get("pubtime"),
                "hashid": detail.get("hashid"),
                "nick_name": detail.get("nick_name"),
                "author": detail.get("author"),
                "content": detail.get("content"),
            },
        )

    except DajialaAPIError as e:
        logger.error(f"Dajiala API error: {e}")
        return ApiResponse(
            code=e.code,
            msg=e.message,
            data=None,
        )
    except Exception as e:
        logger.exception(f"Failed to fetch article detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
