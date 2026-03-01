# -*- coding: utf-8 -*-
"""Pipeline service - Main orchestration for stock selection workflow.

This module provides the main pipeline orchestration functions.
For database operations, see pipeline_repository.py
For individual step logic, see pipeline_steps.py
"""

import logging
from typing import Any, Dict, List, Optional

from aiomysql import Connection

import services.crawler as crawler
from database import Database
from services import pipeline_repository as repo
from services import pipeline_steps as steps

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Exception raised for pipeline execution errors."""

    def __init__(self, message: str, step: Optional[str] = None):
        self.message = message
        self.step = step
        super().__init__(message)


# ============================================================================
# Re-export functions for backward compatibility
# ============================================================================

# Repository functions
get_report_by_date = repo.get_report_by_date
create_report = repo.create_report
update_report_status = repo.update_report_status
clear_step_data = repo.clear_step_data
get_report_articles = repo.get_report_articles
get_report_topics = repo.get_report_topics
get_report_pool1 = repo.get_report_pool1
get_report_pool2 = repo.get_report_pool2

# Step functions
step1_add_articles = steps.step1_add_articles
step2_extract_topics = steps.step2_extract_topics
step3_get_board_stocks = steps.step3_get_board_stocks
step4_apply_rules = steps.step4_apply_rules


# ============================================================================
# Pipeline Orchestration
# ============================================================================

async def run_full_pipeline(report_date: str) -> Dict[str, Any]:
    """Run the full stock selection pipeline.

    This function manages its own database connections from the pool to handle
    long-running operations (like HTTP requests for crawling) without connection timeout issues.

    Args:
        report_date: Date string in YYYY-MM-DD format

    Returns:
        Pipeline execution result
    """
    result = {
        "report_id": None,
        "report_date": report_date,
        "status": "processing",
        "steps": {},
    }

    # Step 1: Get or create report
    async with Database.get_connection() as conn:
        report = await repo.get_report_by_date(conn, report_date)
        if report is None:
            report_id = await repo.create_report(conn, report_date)
        else:
            report_id = report["id"]

        # Update status to processing
        await repo.update_report_status(conn, report_id, "processing")

    result["report_id"] = report_id

    try:
        # Step 1: Check articles (should already exist from crawler)
        await _run_step1(result, report_id, report_date)

        if result["status"] == "error":
            return result

        # Step 2: Extract topics
        await _run_step2(result, report_id)

        if result["status"] == "error":
            return result

        # Step 3: Get board stocks
        await _run_step3(result, report_id)

        if result["status"] == "error":
            return result

        # Step 4: Apply rules
        await _run_step4(result, report_id)

        # Update status to completed
        async with Database.get_connection() as conn:
            await repo.update_report_status(conn, report_id, "completed")
        result["status"] = "completed"

    except Exception as e:
        logger.exception(f"Pipeline error for report {report_id}: {e}")
        try:
            async with Database.get_connection() as conn:
                await repo.update_report_status(conn, report_id, "error")
        except Exception:
            pass
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def _run_step1(result: Dict[str, Any], report_id: int, report_date: str) -> None:
    """Run step 1: Collect articles."""
    async with Database.get_connection() as conn:
        articles = await repo.get_report_articles(conn, report_id)

    # If no articles, try to crawl from enabled target accounts
    if not articles:
        logger.info(f"No articles in raw_articles for report {report_id}, crawling from target accounts...")
        await _crawl_articles(report_id, report_date)

        # Reload articles after crawling
        async with Database.get_connection() as conn:
            articles = await repo.get_report_articles(conn, report_id)

    result["steps"]["step1"] = {
        "name": "情报源",
        "completed": True,
        "article_count": len(articles),
    }

    if not articles:
        logger.warning(f"No articles for report {report_id}, cannot continue pipeline")
        async with Database.get_connection() as conn:
            await repo.update_report_status(conn, report_id, "error")
        result["status"] = "error"
        result["error"] = "No articles found"


async def _crawl_articles(report_id: int, report_date: str) -> None:
    """Crawl articles from active target accounts."""
    async with Database.get_connection() as conn:
        account_rows = await repo.get_active_target_accounts(conn)

    if not account_rows:
        logger.warning(f"No active target accounts configured")
        return

    # Crawl articles from each account
    for account_name, wx_id in account_rows:
        try:
            logger.info(f"Crawling articles from {account_name}...")

            # Fetch article list
            api_response = await crawler.fetch_article_list_by_name(account_name)
            article_list_data = crawler.parse_article_list(api_response, mp_name_fallback=account_name)

            # Fetch article details
            for article in article_list_data[:5]:  # Limit to 5 latest articles
                await _crawl_single_article(article, account_name)

        except Exception as e:
            logger.exception(f"Failed to crawl articles from {account_name}: {e}")

    # Sync articles from wx_article_detail to raw_articles
    await _sync_articles_to_raw(report_id, report_date)


async def _crawl_single_article(article: Dict[str, Any], account_name: str) -> None:
    """Crawl a single article detail."""
    url = article.get("url")
    if not url:
        return

    try:
        detail_response = await crawler.fetch_article_detail(url)
        detail = crawler.parse_article_detail(detail_response)

        async with Database.get_connection() as conn:
            # Check if article already exists
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM wx_article_detail WHERE url_hash = UNHEX(MD5(%s)) LIMIT 1",
                    (url,),
                )
                existing = await cur.fetchone()

            if not existing:
                # Insert into wx_article_detail
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO wx_article_detail (article_list_id, title, url, pubtime, hashid, nick_name, author, content)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            None,
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
        logger.exception(f"Failed to fetch article detail for {account_name}: {e}")


async def _sync_articles_to_raw(report_id: int, report_date: str) -> None:
    """Sync articles from wx_article_detail to raw_articles."""
    async with Database.get_connection() as conn:
        async with conn.cursor() as cur:
            logger.info(f"Querying wx_article_detail for date: {report_date}")
            await cur.execute(
                """SELECT id, title, url, pubtime, nick_name, content
                   FROM wx_article_detail
                   WHERE DATE(FROM_UNIXTIME(pubtime)) = %s""",
                (report_date,),
            )
            rows = await cur.fetchall()
            logger.info(f"Found {len(rows)} articles in wx_article_detail for date {report_date}")

            if rows:
                for row in rows:
                    # Check if already exists
                    await cur.execute(
                        "SELECT id FROM raw_articles WHERE article_detail_id = %s",
                        (row[0],),
                    )
                    if await cur.fetchone():
                        continue

                    await cur.execute(
                        """INSERT INTO raw_articles (report_id, title, content, source_account, publish_time, url, article_detail_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            report_id,
                            row[1],  # title
                            row[5],  # content
                            row[4],  # nick_name
                            row[3],  # pubtime
                            row[2],  # url
                            row[0],  # article_detail_id
                        ),
                    )
                logger.info(f"Synced {len(rows)} articles from wx_article_detail to raw_articles")


async def _run_step2(result: Dict[str, Any], report_id: int) -> None:
    """Run step 2: Extract topics."""
    async with Database.get_connection() as conn:
        topics = await steps.step2_extract_topics(conn, report_id)

    result["steps"]["step2"] = {
        "name": "热点风口",
        "completed": True,
        "topic_count": len(topics),
    }

    if not topics:
        logger.warning(f"No topics extracted for report {report_id}")
        async with Database.get_connection() as conn:
            await repo.update_report_status(conn, report_id, "error")
        result["status"] = "error"
        result["error"] = "No topics extracted"


async def _run_step3(result: Dict[str, Any], report_id: int) -> None:
    """Run step 3: Get board stocks."""
    async with Database.get_connection() as conn:
        pool1_count = await steps.step3_get_board_stocks(conn, report_id)

    result["steps"]["step3"] = {
        "name": "异动初筛",
        "completed": True,
        "pool1_count": pool1_count,
    }

    if pool1_count == 0:
        logger.warning(f"No stocks in pool 1 for report {report_id}")
        async with Database.get_connection() as conn:
            await repo.update_report_status(conn, report_id, "error")
        result["status"] = "error"
        result["error"] = "No stocks found"


async def _run_step4(result: Dict[str, Any], report_id: int) -> None:
    """Run step 4: Apply rules."""
    async with Database.get_connection() as conn:
        rules_config = await repo.get_enabled_rules(conn)
        selected_count = await steps.step4_apply_rules(conn, report_id, rules_config)

    result["steps"]["step4"] = {
        "name": "深度精选",
        "completed": True,
        "selected_count": selected_count,
        "rules_applied": len(rules_config),
    }


# ============================================================================
# Query Functions
# ============================================================================

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
            "data": await repo.get_report_articles(conn, report_id),
        },
        "step2": {
            "name": "热点风口",
            "data": await repo.get_report_topics(conn, report_id),
        },
        "step3": {
            "name": "异动初筛",
            "data": await repo.get_report_pool1(conn, report_id),
        },
        "step4": {
            "name": "深度精选",
            "data": await repo.get_report_pool2(conn, report_id),
        },
    }