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


async def update_report_progress(conn: Connection, report_id: int, progress_info: Dict[str, Any]) -> None:
    """Update report progress info.

    Args:
        conn: Database connection
        report_id: Report ID
        progress_info: Progress information dict with step, current, total, message
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE reports SET progress_info = %s, updated_at = NOW() WHERE id = %s",
            (json.dumps(progress_info, ensure_ascii=False), report_id),
        )


async def get_report_progress(conn: Connection, report_id: int) -> Optional[Dict[str, Any]]:
    """Get report progress info.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        Progress info dict or None
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT progress_info FROM reports WHERE id = %s",
            (report_id,),
        )
        row = await cur.fetchone()
        if row and row[0]:
            if isinstance(row[0], str):
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    return None
            return row[0]
        return None


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

async def get_pool1_config(conn: Connection) -> Dict[str, Any]:
    """Get pool 1 configuration.

    Args:
        conn: Database connection

    Returns:
        Configuration dictionary
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT config_key, config_value FROM pool1_config"
        )
        rows = await cur.fetchall()
        config = {}
        for row in rows:
            key = row[0]
            value = row[1]
            # Try to parse as int if possible
            try:
                config[key] = int(value) if isinstance(value, str) else value
            except (ValueError, TypeError):
                config[key] = value
        # Return default config if empty
        if not config:
            config = {"top_n_per_board": 10}
        return config


async def update_pool1_config(conn: Connection, config_key: str, config_value: Any) -> None:
    """Update pool 1 configuration.

    Args:
        conn: Database connection
        config_key: Configuration key
        config_value: Configuration value
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO pool1_config (config_key, config_value) VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)""",
            (config_key, str(config_value)),
        )


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
            """SELECT id, stock_code, stock_name, related_topic_id, related_board,
                      latest_price, change_pct, change_amount, volume, turnover,
                      amplitude, high_price, low_price, open_price, prev_close,
                      turnover_rate, pe_ratio, pb_ratio, snapshot_data, match_reason
               FROM stock_pool_1 WHERE report_id = %s
               ORDER BY related_board, change_pct DESC""",
            (report_id,),
        )
        rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "stock_code": row[1],
                "stock_name": row[2],
                "related_topic_id": row[3],
                "related_board": row[4],
                "latest_price": float(row[5]) if row[5] else None,
                "change_pct": float(row[6]) if row[6] else None,
                "change_amount": float(row[7]) if row[7] else None,
                "volume": float(row[8]) if row[8] else None,
                "turnover": float(row[9]) if row[9] else None,
                "amplitude": float(row[10]) if row[10] else None,
                "high_price": float(row[11]) if row[11] else None,
                "low_price": float(row[12]) if row[12] else None,
                "open_price": float(row[13]) if row[13] else None,
                "prev_close": float(row[14]) if row[14] else None,
                "turnover_rate": float(row[15]) if row[15] else None,
                "pe_ratio": float(row[16]) if row[16] else None,
                "pb_ratio": float(row[17]) if row[17] else None,
                "snapshot_data": row[18] if isinstance(row[18], dict) else {},
                "match_reason": row[19],
            }
            for row in rows
        ]


async def add_pool1_stock(conn: Connection, report_id: int, stock: Dict[str, Any]) -> int:
    """Add a stock to pool 1.

    Args:
        conn: Database connection
        report_id: Report ID
        stock: Stock dictionary with all fields

    Returns:
        Stock pool 1 ID
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO stock_pool_1
               (report_id, stock_code, stock_name, related_topic_id, related_board,
                latest_price, change_pct, change_amount, volume, turnover,
                amplitude, high_price, low_price, open_price, prev_close,
                turnover_rate, pe_ratio, pb_ratio, snapshot_data, match_reason)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                report_id,
                stock.get("stock_code"),
                stock.get("stock_name"),
                stock.get("related_topic_id"),
                stock.get("related_board"),
                stock.get("latest_price"),
                stock.get("change_pct"),
                stock.get("change_amount"),
                stock.get("volume"),
                stock.get("turnover"),
                stock.get("amplitude"),
                stock.get("high_price"),
                stock.get("low_price"),
                stock.get("open_price"),
                stock.get("prev_close"),
                stock.get("turnover_rate"),
                stock.get("pe_ratio"),
                stock.get("pb_ratio"),
                json.dumps(stock.get("snapshot_data", {}), ensure_ascii=False),
                stock.get("match_reason"),
            ),
        )
        return cur.lastrowid


async def check_pool1_stock_exists(conn: Connection, report_id: int, stock_code: str) -> bool:
    """Check if a stock already exists in pool 1.

    Args:
        conn: Database connection
        report_id: Report ID
        stock_code: Stock code

    Returns:
        True if exists, False otherwise
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT 1 FROM stock_pool_1 WHERE report_id = %s AND stock_code = %s LIMIT 1",
            (report_id, stock_code),
        )
        return await cur.fetchone() is not None


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