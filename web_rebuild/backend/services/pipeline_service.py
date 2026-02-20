# -*- coding: utf-8 -*-
"""Pipeline service for stock selection workflow."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiomysql import Connection

import services.llm_service as llm_service
import services.stock_service as stock_service
import services.crawler as crawler
from rules.registry import get_rule_class

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Exception raised for pipeline execution errors."""

    def __init__(self, message: str, step: Optional[str] = None):
        self.message = message
        self.step = step
        super().__init__(message)


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
        return [
            {
                "id": row[0],
                "topic_name": row[1],
                "related_boards": row[2] if isinstance(row[2], list) else [],
                "logic_summary": row[3],
            }
            for row in rows
        ]


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


async def step1_add_articles(conn: Connection, report_id: int, articles: List[Dict[str, Any]]) -> List[int]:
    """Step 1: Add articles to report.

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


async def step2_extract_topics(conn: Connection, report_id: int) -> List[Dict[str, Any]]:
    """Step 2: Extract topics from articles using LLM.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        List of topic dictionaries
    """
    articles = await get_report_articles(conn, report_id)

    if not articles:
        logger.warning(f"No articles found for report {report_id}")
        return []

    # Extract topics using LLM
    topics = await llm_service.extract_topics_from_articles(articles)

    # Save topics to database
    topic_ids = []
    async with conn.cursor() as cur:
        for topic in topics:
            await cur.execute(
                """INSERT INTO hot_topics (report_id, topic_name, related_boards, logic_summary, source_article_ids)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    report_id,
                    topic.get("topic_name"),
                    topic.get("related_boards", []),
                    topic.get("logic_summary"),
                    articles,  # Store all article IDs for now
                ),
            )
            topic_ids.append(cur.lastrowid)

    return topics


async def step3_get_board_stocks(conn: Connection, report_id: int) -> int:
    """Step 3: Get stocks from board names in topics.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        Number of stocks added to pool 1
    """
    topics = await get_report_topics(conn, report_id)

    stock_count = 0
    for topic in topics:
        topic_id = topic["id"]
        related_boards = topic.get("related_boards", [])

        for board_name in related_boards:
            try:
                stocks = stock_service.get_stocks_by_board(board_name)

                for stock in stocks:
                    # Get stock snapshot
                    stock_code = stock.get("code")
                    snapshot = stock_service.get_stock_snapshot(stock_code)

                    # Save to pool 1
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """INSERT INTO stock_pool_1 (report_id, stock_code, stock_name, related_topic_id, snapshot_data, match_reason)
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            (
                                report_id,
                                stock_code,
                                stock.get("name"),
                                topic_id,
                                snapshot,
                                f"来自板块: {board_name}",
                            ),
                        )
                    stock_count += 1

            except Exception as e:
                logger.error(f"Failed to get stocks for board {board_name}: {e}")

    return stock_count


async def step4_apply_rules(conn: Connection, report_id: int, rules_config: List[Dict[str, Any]]) -> int:
    """Step 4: Apply rules to stock pool 1 to create pool 2.

    Args:
        conn: Database connection
        report_id: Report ID
        rules_config: List of enabled rule configurations

    Returns:
        Number of selected stocks in pool 2
    """
    pool1_stocks = await get_report_pool1(conn, report_id)

    if not pool1_stocks:
        logger.warning(f"No stocks in pool 1 for report {report_id}")
        return 0

    selected_count = 0

    for stock in pool1_stocks:
        stock_code = stock.get("stock_code")
        stock_name = stock.get("stock_name")
        snapshot_data = stock.get("snapshot_data", {})

        # Build stock context for rule checking
        stock_context = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "snapshot_data": snapshot_data,
            "related_topic_id": stock.get("related_topic_id"),
        }

        # Apply all rules
        rule_results = []
        total_score = 0.0
        tech_score = 0.0
        fund_score = 0.0
        all_passed = True

        for rule_config in rules_config:
            rule_key = rule_config.get("rule_key")
            rule_params = rule_config.get("rule_value", {})

            try:
                rule_class = get_rule_class(rule_key)
                rule_instance = rule_class(rule_params)
                result = rule_instance.check(stock_context)

                rule_results.append({
                    "rule_key": rule_key,
                    "passed": result.passed,
                    "score": result.score,
                    "reason": result.reason,
                    "details": result.details,
                })

                if not result.passed:
                    all_passed = False

                # Accumulate scores (simplified logic)
                if rule_key in ["volume_ratio", "price_change", "turnover_rate"]:
                    tech_score += result.score
                elif rule_key in ["pe_ratio", "pb_ratio", "roe"]:
                    fund_score += result.score

                total_score += result.score

            except Exception as e:
                logger.error(f"Error applying rule {rule_key} to {stock_code}: {e}")
                all_passed = False

        # Normalize scores
        num_tech_rules = sum(1 for r in rules_config if r.get("rule_key") in ["volume_ratio", "price_change", "turnover_rate"])
        num_fund_rules = sum(1 for r in rules_config if r.get("rule_key") in ["pe_ratio", "pb_ratio", "roe"])

        if num_tech_rules > 0:
            tech_score = tech_score / num_tech_rules
        if num_fund_rules > 0:
            fund_score = fund_score / num_fund_rules

        # Save to pool 2
        is_selected = all_passed and total_score > 0
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO stock_pool_2 (report_id, pool_1_id, stock_code, stock_name, tech_score, fund_score, total_score, rule_results, is_selected)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    report_id,
                    stock["id"],
                    stock_code,
                    stock_name,
                    tech_score,
                    fund_score,
                    total_score,
                    rule_results,
                    is_selected,
                ),
            )

        if is_selected:
            selected_count += 1

    return selected_count


async def run_full_pipeline(conn: Connection, report_date: str) -> Dict[str, Any]:
    """Run the full stock selection pipeline.

    Args:
        conn: Database connection
        report_date: Date string in YYYY-MM-DD format

    Returns:
        Pipeline execution result
    """
    # Get or create report
    report = await get_report_by_date(conn, report_date)
    if report is None:
        report_id = await create_report(conn, report_date)
    else:
        report_id = report["id"]

    # Update status to processing
    await update_report_status(conn, report_id, "processing")

    result = {
        "report_id": report_id,
        "report_date": report_date,
        "status": "processing",
        "steps": {},
    }

    try:
        # Step 1: Check articles (should already exist from crawler)
        articles = await get_report_articles(conn, report_id)

        # If no articles, try to crawl from enabled target accounts
        if not articles:
            logger.info(f"No articles in raw_articles for report {report_id}, crawling from target accounts...")

            # Get enabled target accounts
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT account_name, wx_id FROM target_accounts WHERE status = 'active' ORDER BY sort_order"
                )
                account_rows = await cur.fetchall()

            if not account_rows:
                logger.warning(f"No active target accounts configured")
            else:
                # Crawl articles from each account
                for account_name, wx_id in account_rows:
                    try:
                        logger.info(f"Crawling articles from {account_name}...")

                        # Fetch article list
                        api_response = await crawler.fetch_article_list_by_name(account_name)
                        article_list_data = crawler.parse_article_list(api_response, mp_name_fallback=account_name)

                        # Fetch article details
                        for article in article_list_data[:5]:  # Limit to 5 latest articles
                            try:
                                url = article.get("url")
                                if url:
                                    detail_response = await crawler.fetch_article_detail(url)
                                    detail = crawler.parse_article_detail(detail_response)

                                    # Check if article already exists in wx_article_detail
                                    async with conn.cursor() as cur2:
                                        await cur2.execute(
                                            "SELECT id FROM wx_article_detail WHERE url_hash = UNHEX(MD5(%s)) LIMIT 1",
                                            (url,),
                                        )
                                        existing = await cur2.fetchone()

                                    if not existing:
                                        # Insert into wx_article_detail
                                        async with conn.cursor() as cur2:
                                            await cur2.execute(
                                                """INSERT INTO wx_article_detail (article_list_id, title, url, pubtime, hashid, nick_name, author, content)
                                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                                                (
                                                    None,  # article_list_id
                                                    detail.get("title", ""),
                                                    detail.get("url", ""),
                                                    crawler._parse_pubtime(detail.get("pubtime")),
                                                    detail.get("hashid", ""),
                                                    detail.get("nick_name", ""),
                                                    detail.get("author", ""),
                                                    detail.get("content", ""),
                                                ),
                                            )
                                        logger.info(f"Fetched article: {detail.get('title', '')[:50]}")

                            except Exception as e:
                                logger.error(f"Failed to fetch article detail for {account_name}: {e}")

                    except Exception as e:
                        logger.error(f"Failed to crawl articles from {account_name}: {e}")

                # Now sync articles from wx_article_detail to raw_articles
                async with conn.cursor() as cur:
                    await cur.execute(
                        """SELECT id, title, url, pubtime, nick_name, content
                           FROM wx_article_detail
                           WHERE DATE(FROM_UNIXTIME(pubtime)) = %s""",
                        (report_date,),
                    )
                    rows = await cur.fetchall()

                    if rows:
                        # Insert into raw_articles
                        for row in rows:
                            await cur.execute(
                                """INSERT INTO raw_articles (report_id, title, content, source_account, publish_time, url, article_detail_id)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (
                                    report_id,
                                    row[1],  # title
                                    row[4],  # content
                                    row[3],  # source_account (nick_name)
                                    row[2],  # publish_time (pubtime)
                                    row[1],  # url
                                    row[0],  # article_detail_id
                                ),
                            )
                        logger.info(f"Synced {len(rows)} articles from wx_article_detail to raw_articles")

                    # Reload articles
                    articles = await get_report_articles(conn, report_id)

        result["steps"]["step1"] = {
            "name": "情报源",
            "completed": True,
            "article_count": len(articles),
        }

        if not articles:
            logger.warning(f"No articles for report {report_id}, cannot continue pipeline")
            await update_report_status(conn, report_id, "error")
            result["status"] = "error"
            result["error"] = "No articles found"
            return result

        # Step 2: Extract topics
        topics = await step2_extract_topics(conn, report_id)
        result["steps"]["step2"] = {
            "name": "热点风口",
            "completed": True,
            "topic_count": len(topics),
        }

        if not topics:
            logger.warning(f"No topics extracted for report {report_id}")
            await update_report_status(conn, report_id, "error")
            result["status"] = "error"
            result["error"] = "No topics extracted"
            return result

        # Step 3: Get board stocks
        pool1_count = await step3_get_board_stocks(conn, report_id)
        result["steps"]["step3"] = {
            "name": "异动初筛",
            "completed": True,
            "pool1_count": pool1_count,
        }

        if pool1_count == 0:
            logger.warning(f"No stocks in pool 1 for report {report_id}")
            await update_report_status(conn, report_id, "error")
            result["status"] = "error"
            result["error"] = "No stocks found"
            return result

        # Step 4: Apply rules
        # Get rule configurations
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT rule_key, rule_value, is_enabled FROM strategy_config WHERE is_enabled = TRUE ORDER BY sort_order",
            )
            rows = await cur.fetchall()
            rules_config = [
                {"rule_key": row[0], "rule_value": row[1], "is_enabled": row[2]}
                for row in rows
            ]

        selected_count = await step4_apply_rules(conn, report_id, rules_config)
        result["steps"]["step4"] = {
            "name": "深度精选",
            "completed": True,
            "selected_count": selected_count,
            "rules_applied": len(rules_config),
        }

        # Update status to completed
        await update_report_status(conn, report_id, "completed")
        result["status"] = "completed"

    except Exception as e:
        logger.exception(f"Pipeline error for report {report_id}: {e}")
        await update_report_status(conn, report_id, "error")
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def get_pipeline_nodes(conn: Connection, report_id: int) -> Dict[str, Any]:
    """Get all pipeline node data for a report.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        Dictionary with data for each pipeline node
    """
    return {
        "step1": {
            "name": "情报源",
            "data": await get_report_articles(conn, report_id),
        },
        "step2": {
            "name": "热点风口",
            "data": await get_report_topics(conn, report_id),
        },
        "step3": {
            "name": "异动初筛",
            "data": await get_report_pool1(conn, report_id),
        },
        "step4": {
            "name": "深度精选",
            "data": await get_report_pool2(conn, report_id),
        },
    }
