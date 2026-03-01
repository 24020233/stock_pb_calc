# -*- coding: utf-8 -*-
"""Pipeline repository - Database operations for pipeline data."""

import json
import logging
from typing import Any, Dict, List, Optional

from aiomysql import Connection

logger = logging.getLogger(__name__)


# ============================================================================
# Report Operations
# ============================================================================

async def get_report_by_date(conn: Connection, report_date: str) -> Optional[Dict[str, Any]]:
    """Get report by date.

    Args:
        conn: Database connection
        report_date: Date string in YYYY-MM-DD format

    Returns:
        Report dictionary or None
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, report_date, status, created_at, updated_at FROM reports WHERE report_date = %s",
            (report_date,),
        )
        row = await cur.fetchone()
        if row:
            return {
                "id": row[0],
                "report_date": row[1].strftime("%Y-%m-%d") if row[1] else None,
                "status": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
        return None


async def create_report(conn: Connection, report_date: str) -> int:
    """Create a new report.

    Args:
        conn: Database connection
        report_date: Date string in YYYY-MM-DD format

    Returns:
        Report ID
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO reports (report_date, status) VALUES (%s, 'pending')",
            (report_date,),
        )
        return cur.lastrowid


async def update_report_status(conn: Connection, report_id: int, status: str) -> None:
    """Update report status.

    Args:
        conn: Database connection
        report_id: Report ID
        status: New status (pending, processing, completed, error)
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE reports SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, report_id),
        )


async def clear_step_data(conn: Connection, report_id: int, step_number: int) -> Dict[str, int]:
    """Clear data for a specific step and all subsequent steps.

    Args:
        conn: Database connection
        report_id: Report ID
        step_number: Step number (2, 3, or 4)

    Returns:
        Dictionary with counts of deleted records per table
    """
    deleted_counts = {}

    # Step 4: Clear stock_pool_2
    if step_number <= 4:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM stock_pool_2 WHERE report_id = %s", (report_id,))
            deleted_counts["stock_pool_2"] = cur.rowcount

    # Step 3: Clear stock_pool_1
    if step_number <= 3:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM stock_pool_1 WHERE report_id = %s", (report_id,))
            deleted_counts["stock_pool_1"] = cur.rowcount

    # Step 2: Clear hot_topics
    if step_number <= 2:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM hot_topics WHERE report_id = %s", (report_id,))
            deleted_counts["hot_topics"] = cur.rowcount

    logger.info(f"Cleared step {step_number}+ data for report {report_id}: {deleted_counts}")
    return deleted_counts


# ============================================================================
# Article Operations
# ============================================================================

async def get_report_articles(conn: Connection, report_id: int) -> List[Dict[str, Any]]:
    """Get articles for a report.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        List of article dictionaries
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, title, content, source_account, publish_time, url FROM raw_articles WHERE report_id = %s",
            (report_id,),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "source_account": row[3],
                "publish_time": row[4],
                "url": row[5],
            }
            for row in rows
        ]


async def add_articles(conn: Connection, report_id: int, articles: List[Dict[str, Any]]) -> List[int]:
    """Add articles to a report.

    Args:
        conn: Database connection
        report_id: Report ID
        articles: List of article dictionaries

    Returns:
        List of article IDs
    """
    article_ids = []
    async with conn.cursor() as cur:
        for article in articles:
            await cur.execute(
                """INSERT INTO raw_articles (report_id, title, content, source_account, publish_time, url, article_detail_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    report_id,
                    article.get("title"),
                    article.get("content"),
                    article.get("source_account"),
                    article.get("publish_time"),
                    article.get("url"),
                    article.get("article_detail_id"),
                ),
            )
            article_ids.append(cur.lastrowid)

    return article_ids


# ============================================================================
# Topic Operations
# ============================================================================

async def get_report_topics(conn: Connection, report_id: int) -> List[Dict[str, Any]]:
    """Get topics for a report.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        List of topic dictionaries
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, topic_name, related_boards, logic_summary FROM hot_topics WHERE report_id = %s",
            (report_id,),
        )
        rows = await cur.fetchall()
        result = []
        for row in rows:
            # Handle JSON field - may be string or list depending on driver
            related_boards = row[2]
            if isinstance(related_boards, str):
                try:
                    related_boards = json.loads(related_boards)
                except (json.JSONDecodeError, TypeError):
                    related_boards = []
            elif not isinstance(related_boards, list):
                related_boards = []

            result.append({
                "id": row[0],
                "topic_name": row[1],
                "related_boards": related_boards,
                "logic_summary": row[3],
            })
        return result


async def add_topic(conn: Connection, report_id: int, topic: Dict[str, Any], article_ids: List[int]) -> int:
    """Add a topic to a report.

    Args:
        conn: Database connection
        report_id: Report ID
        topic: Topic dictionary
        article_ids: List of source article IDs

    Returns:
        Topic ID
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO hot_topics (report_id, topic_name, related_boards, logic_summary, source_article_ids)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                report_id,
                topic.get("topic_name"),
                json.dumps(topic.get("related_boards", []), ensure_ascii=False),
                topic.get("logic_summary"),
                json.dumps(article_ids, ensure_ascii=False),
            ),
        )
        return cur.lastrowid


# ============================================================================
# Stock Pool Operations
# ============================================================================

async def get_report_pool1(conn: Connection, report_id: int) -> List[Dict[str, Any]]:
    """Get stock pool 1 for a report.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        List of stock pool 1 dictionaries
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """SELECT id, stock_code, stock_name, related_topic_id, snapshot_data, match_reason
               FROM stock_pool_1 WHERE report_id = %s""",
            (report_id,),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "stock_code": row[1],
                "stock_name": row[2],
                "related_topic_id": row[3],
                "snapshot_data": row[4] if isinstance(row[4], dict) else {},
                "match_reason": row[5],
            }
            for row in rows
        ]


async def add_pool1_stock(conn: Connection, report_id: int, stock: Dict[str, Any]) -> int:
    """Add a stock to pool 1.

    Args:
        conn: Database connection
        report_id: Report ID
        stock: Stock dictionary with stock_code, stock_name, related_topic_id, snapshot_data, match_reason

    Returns:
        Stock pool 1 ID
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO stock_pool_1 (report_id, stock_code, stock_name, related_topic_id, snapshot_data, match_reason)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                report_id,
                stock.get("stock_code"),
                stock.get("stock_name"),
                stock.get("related_topic_id"),
                stock.get("snapshot_data"),
                stock.get("match_reason"),
            ),
        )
        return cur.lastrowid


async def get_report_pool2(conn: Connection, report_id: int, selected_only: bool = False) -> List[Dict[str, Any]]:
    """Get stock pool 2 for a report.

    Args:
        conn: Database connection
        report_id: Report ID
        selected_only: Only return selected stocks

    Returns:
        List of stock pool 2 dictionaries
    """
    async with conn.cursor() as cur:
        if selected_only:
            await cur.execute(
                """SELECT id, stock_code, stock_name, tech_score, fund_score, total_score, ai_analysis, is_selected
                   FROM stock_pool_2 WHERE report_id = %s AND is_selected = TRUE""",
                (report_id,),
            )
        else:
            await cur.execute(
                """SELECT id, stock_code, stock_name, tech_score, fund_score, total_score, ai_analysis, is_selected
                   FROM stock_pool_2 WHERE report_id = %s""",
                (report_id,),
            )
        rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "stock_code": row[1],
                "stock_name": row[2],
                "tech_score": float(row[3]) if row[3] else None,
                "fund_score": float(row[4]) if row[4] else None,
                "total_score": float(row[5]) if row[5] else None,
                "ai_analysis": row[6],
                "is_selected": bool(row[7]),
            }
            for row in rows
        ]


async def add_pool2_stock(conn: Connection, report_id: int, stock: Dict[str, Any]) -> int:
    """Add a stock to pool 2.

    Args:
        conn: Database connection
        report_id: Report ID
        stock: Stock dictionary with pool_1_id, stock_code, stock_name, tech_score, fund_score, total_score, rule_results, is_selected

    Returns:
        Stock pool 2 ID
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO stock_pool_2 (report_id, pool_1_id, stock_code, stock_name, tech_score, fund_score, total_score, rule_results, is_selected)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                report_id,
                stock.get("pool_1_id"),
                stock.get("stock_code"),
                stock.get("stock_name"),
                stock.get("tech_score"),
                stock.get("fund_score"),
                stock.get("total_score"),
                stock.get("rule_results"),
                stock.get("is_selected", False),
            ),
        )
        return cur.lastrowid


# ============================================================================
# Config Operations
# ============================================================================

async def get_enabled_rules(conn: Connection) -> List[Dict[str, Any]]:
    """Get enabled rule configurations.

    Args:
        conn: Database connection

    Returns:
        List of rule configurations
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT rule_key, rule_value, is_enabled FROM strategy_config WHERE is_enabled = TRUE ORDER BY sort_order",
        )
        rows = await cur.fetchall()
        return [
            {"rule_key": row[0], "rule_value": row[1], "is_enabled": row[2]}
            for row in rows
        ]


async def get_active_target_accounts(conn: Connection) -> List[tuple]:
    """Get active target accounts for crawling.

    Args:
        conn: Database connection

    Returns:
        List of (account_name, wx_id) tuples
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT account_name, wx_id FROM target_accounts WHERE status = 'active' ORDER BY sort_order"
        )
        return await cur.fetchall()