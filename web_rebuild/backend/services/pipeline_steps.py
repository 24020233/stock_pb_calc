# -*- coding: utf-8 -*-
"""Pipeline steps - Individual step execution logic."""

import logging
from typing import Any, Dict, List

from aiomysql import Connection

import services.llm_service as llm_service
import services.stock_service as stock_service
from rules.registry import get_rule_class
from services import pipeline_repository as repo

logger = logging.getLogger(__name__)


# ============================================================================
# Step 1: Articles (情报源)
# ============================================================================

async def step1_add_articles(conn: Connection, report_id: int, articles: List[Dict[str, Any]]) -> List[int]:
    """Step 1: Add articles to report.

    Args:
        conn: Database connection
        report_id: Report ID
        articles: List of article dictionaries

    Returns:
        List of article IDs
    """
    return await repo.add_articles(conn, report_id, articles)


# ============================================================================
# Step 2: Topics (热点风口)
# ============================================================================

async def step2_extract_topics(conn: Connection, report_id: int) -> List[Dict[str, Any]]:
    """Step 2: Extract topics from articles using LLM.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        List of topic dictionaries
    """
    articles = await repo.get_report_articles(conn, report_id)

    if not articles:
        logger.warning(f"No articles found for report {report_id}")
        return []

    # Extract topics using LLM
    topics = await llm_service.extract_topics_from_articles(articles)

    # Save topics to database
    article_ids = [a.get("id") for a in articles if a.get("id")]
    for topic in topics:
        await repo.add_topic(conn, report_id, topic, article_ids)

    return topics


# ============================================================================
# Step 3: Board Stocks (异动初筛)
# ============================================================================

async def step3_get_board_stocks(conn: Connection, report_id: int) -> int:
    """Step 3: Get stocks from board names in topics.

    Args:
        conn: Database connection
        report_id: Report ID

    Returns:
        Number of stocks added to pool 1
    """
    topics = await repo.get_report_topics(conn, report_id)

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
                    await repo.add_pool1_stock(conn, report_id, {
                        "stock_code": stock_code,
                        "stock_name": stock.get("name"),
                        "related_topic_id": topic_id,
                        "snapshot_data": snapshot,
                        "match_reason": f"来自板块: {board_name}",
                    })
                    stock_count += 1

            except Exception as e:
                logger.error(f"Failed to get stocks for board {board_name}: {e}")

    return stock_count


# ============================================================================
# Step 4: Apply Rules (深度精选)
# ============================================================================

# Rule type classification
TECH_RULES = {"volume_ratio", "price_change", "turnover_rate"}
FUND_RULES = {"pe_ratio", "pb_ratio", "roe"}


async def step4_apply_rules(conn: Connection, report_id: int, rules_config: List[Dict[str, Any]]) -> int:
    """Step 4: Apply rules to stock pool 1 to create pool 2.

    Args:
        conn: Database connection
        report_id: Report ID
        rules_config: List of enabled rule configurations

    Returns:
        Number of selected stocks in pool 2
    """
    pool1_stocks = await repo.get_report_pool1(conn, report_id)

    if not pool1_stocks:
        logger.warning(f"No stocks in pool 1 for report {report_id}")
        return 0

    selected_count = 0

    for stock in pool1_stocks:
        is_selected, tech_score, fund_score, total_score, rule_results = _apply_rules_to_stock(
            stock, rules_config
        )

        # Save to pool 2
        await repo.add_pool2_stock(conn, report_id, {
            "pool_1_id": stock["id"],
            "stock_code": stock.get("stock_code"),
            "stock_name": stock.get("stock_name"),
            "tech_score": tech_score,
            "fund_score": fund_score,
            "total_score": total_score,
            "rule_results": rule_results,
            "is_selected": is_selected,
        })

        if is_selected:
            selected_count += 1

    return selected_count


def _apply_rules_to_stock(
    stock: Dict[str, Any], rules_config: List[Dict[str, Any]]
) -> tuple[bool, float, float, float, List[Dict[str, Any]]]:
    """Apply all rules to a single stock.

    Args:
        stock: Stock dictionary from pool 1
        rules_config: List of enabled rule configurations

    Returns:
        Tuple of (is_selected, tech_score, fund_score, total_score, rule_results)
    """
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

            # Accumulate scores by type
            if rule_key in TECH_RULES:
                tech_score += result.score
            elif rule_key in FUND_RULES:
                fund_score += result.score

            total_score += result.score

        except Exception as e:
            logger.error(f"Error applying rule {rule_key} to {stock_code}: {e}")
            all_passed = False

    # Normalize scores
    num_tech_rules = sum(1 for r in rules_config if r.get("rule_key") in TECH_RULES)
    num_fund_rules = sum(1 for r in rules_config if r.get("rule_key") in FUND_RULES)

    if num_tech_rules > 0:
        tech_score = tech_score / num_tech_rules
    if num_fund_rules > 0:
        fund_score = fund_score / num_fund_rules

    is_selected = all_passed and total_score > 0

    return is_selected, tech_score, fund_score, total_score, rule_results