# -*- coding: utf-8 -*-
"""Pipeline steps - Individual step execution logic."""

import asyncio
import logging
from typing import Any, Dict, List

from aiomysql import Connection

import services.llm_service as llm_service
import services.selenium_service as selenium_service
from rules.registry import get_rule_class
from rules.handlers.registry import get_handler
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
    sector_names = await repo.get_sector_names(conn)

    if not articles:
        logger.warning(f"No articles found for report {report_id}")
        return []

    # Extract topics using LLM
    topics = await llm_service.extract_topics_from_articles(articles, sector_names)

    # Save topics to database
    default_article_ids = [a.get("id") for a in articles if a.get("id")]
    for topic in topics:
        topic_article_ids = topic.get("source_article_ids") or default_article_ids
        await repo.add_topic(conn, report_id, topic, topic_article_ids)

    return topics


# ============================================================================
# Step 3: Board Stocks (股票池1)
# ============================================================================

async def step3_get_board_stocks(conn: Connection, report_id: int, top_n: int = 10) -> int:
    """Step 3: Get stocks from board names in topics using Selenium.

    Args:
        conn: Database connection
        report_id: Report ID
        top_n: Number of top stocks to take per board (sorted by change_pct)

    Returns:
        Number of stocks added to pool 1
    """
    topics = await repo.get_report_topics(conn, report_id)

    # Get config
    config = await repo.get_pool1_config(conn)
    top_n = config.get("top_n_per_board", top_n)

    # Collect all unique board names first
    all_boards = []
    for topic in topics:
        related_boards = topic.get("related_boards", [])
        for board_name in related_boards:
            if board_name not in all_boards:
                all_boards.append(board_name)

    total_boards = len(all_boards)
    logger.info(f"Step 3: Processing {total_boards} boards for report {report_id}")

    if not all_boards:
        logger.warning("No boards to process")
        return 0

    # Update progress - starting
    await repo.update_report_progress(conn, report_id, {
        "step": "step3",
        "current": 0,
        "total": total_boards,
        "message": "正在启动浏览器获取板块数据..."
    })

    # Get sector info from database (sector_id and sector_name)
    sector_list = await repo.get_sectors_by_names(conn, all_boards)

    if not sector_list:
        logger.warning("No matching sectors found in database")
        return 0

    logger.info(f"Found {len(sector_list)} matching sectors in database")

    # Update progress
    await repo.update_report_progress(conn, report_id, {
        "step": "step3",
        "current": 0,
        "total": len(sector_list),
        "message": f"正在获取 {len(sector_list)} 个板块的成分股数据..."
    })

    # Fetch all board stocks using selenium (synchronous, runs in thread)
    # Note: progress updates are not available during selenium execution
    # because selenium is synchronous and cannot safely call async functions
    all_results = selenium_service.fetch_all_board_stocks(sector_list, top_n)

    # Save to database and build stock_pool_1
    all_stocks: Dict[str, Dict[str, Any]] = {}
    stock_count = 0

    for sector_name, stocks in all_results.items():
        # Save to board_stocks table
        await repo.save_board_stocks(conn, stocks)

        # Also save to stock_pool_1 for report
        for stock in stocks:
            stock_code = stock.get("stock_code")
            if not stock_code:
                continue

            if stock_code in all_stocks:
                # Deduplication - append board name to existing
                existing = all_stocks[stock_code]
                existing_boards = existing.get("_all_boards", [])
                if sector_name not in existing_boards:
                    existing_boards.append(sector_name)
                    existing["_all_boards"] = existing_boards
                continue

            all_stocks[stock_code] = {
                "stock_code": stock_code,
                "stock_name": stock.get("stock_name"),
                "related_topic_id": None,
                "related_board": sector_name,
                "latest_price": stock.get("latest_price"),
                "change_pct": stock.get("change_pct"),
                "change_amount": stock.get("change_amount"),
                "volume": stock.get("volume"),
                "turnover": stock.get("turnover"),
                "amplitude": stock.get("amplitude"),
                "high_price": stock.get("high_price"),
                "low_price": stock.get("low_price"),
                "open_price": stock.get("open_price"),
                "prev_close": stock.get("prev_close"),
                "turnover_rate": stock.get("turnover_rate"),
                "pe_ratio": stock.get("pe_ratio"),
                "pb_ratio": stock.get("pb_ratio"),
                "snapshot_data": {},
                "match_reason": f"来自板块: {sector_name}",
                "_all_boards": [sector_name],
            }

    # Clear progress
    await repo.update_report_progress(conn, report_id, {
        "step": "step3",
        "current": len(sector_list),
        "total": len(sector_list),
        "message": "正在保存数据..."
    })

    # Save to stock_pool_1
    for stock_data in all_stocks.values():
        all_boards_list = stock_data.pop("_all_boards", [])
        if len(all_boards_list) > 1:
            stock_data["match_reason"] = f"来自板块: {', '.join(all_boards_list)}"

        await repo.add_pool1_stock(conn, report_id, stock_data)
        stock_count += 1

    logger.info(f"Step 3 completed: {stock_count} stocks added to pool 1 (top {top_n} per board, deduplicated)")
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
        rules_config: List of enabled rule configurations (should include rule_handler, rule_value, etc.)

    Returns:
        Number of selected stocks in pool 2
    """
    pool1_stocks = await repo.get_report_pool1(conn, report_id)

    if not pool1_stocks:
        logger.warning(f"No stocks in pool 1 for report {report_id}")
        return 0

    stock_codes = [stock["stock_code"] for stock in pool1_stocks]
    
    # Store aggregated results per stock.
    # aggregated_results[stock_code] = {"rule_results": [], "total_score": 0.0, "tech_score": 0.0, "fund_score": 0.0, "all_passed": True}
    aggregated_results: Dict[str, Dict[str, Any]] = {
        code: {
            "rule_results": [],
            "total_score": 0.0,
            "tech_score": 0.0,
            "fund_score": 0.0,
            "all_passed": True,
        }
        for code in stock_codes
    }

    # Execute rules sequentially
    is_first_rule = True
    for rule_config in rules_config:
        rule_key = rule_config.get("rule_key")
        rule_handler_key = rule_config.get("rule_handler")
        rule_params = rule_config.get("rule_value", {})

        # Sequential delay
        if not is_first_rule:
            logger.info(f"Waiting 10 seconds before executing next rule: {rule_key}")
            await asyncio.sleep(10)
        is_first_rule = False
        
        # Determine if we should use the new BaseRuleHandler or legacy BaseRule
        handler = None
        if rule_handler_key:
            handler = get_handler(rule_handler_key)

        if handler:
            # New handler pattern: execute batch across all stocks
            logger.info(f"Executing rule handler {rule_handler_key} for rule {rule_key}")
            result = await handler.execute(stock_codes, rule_params, conn)
            
            # Match results back to stocks
            results_by_code = {item.get("stock_code"): item for item in result.data}
            for code in stock_codes:
                stock_result = results_by_code.get(code, {})
                passed = stock_result.get("is_continuous_rise", False) if rule_handler_key == "continuous_rise" else result.success
                score = 1.0 if passed else 0.0  # Simple scoring for batch handlers
                
                aggregated_results[code]["rule_results"].append({
                    "rule_key": rule_key,
                    "passed": passed,
                    "score": score,
                    "reason": "Batch handler check",
                    "details": stock_result,
                })
                if not passed:
                    aggregated_results[code]["all_passed"] = False
                
                if rule_key in TECH_RULES:
                    aggregated_results[code]["tech_score"] += score
                elif rule_key in FUND_RULES:
                    aggregated_results[code]["fund_score"] += score
                aggregated_results[code]["total_score"] += score
        else:
            # Legacy rule pattern: process each stock individually
            logger.info(f"Executing legacy rule {rule_key}")
            try:
                rule_class = get_rule_class(rule_key)
                rule_instance = rule_class(rule_params)
                
                for stock in pool1_stocks:
                    code = stock["stock_code"]
                    stock_context = {
                        "stock_code": code,
                        "stock_name": stock.get("stock_name"),
                        "snapshot_data": stock.get("snapshot_data", {}),
                        "related_topic_id": stock.get("related_topic_id"),
                    }
                    
                    try:
                        res = rule_instance.check(stock_context)
                        aggregated_results[code]["rule_results"].append({
                            "rule_key": rule_key,
                            "passed": res.passed,
                            "score": res.score,
                            "reason": res.reason,
                            "details": res.details,
                        })
                        if not res.passed:
                            aggregated_results[code]["all_passed"] = False
                        
                        if rule_key in TECH_RULES:
                            aggregated_results[code]["tech_score"] += res.score
                        elif rule_key in FUND_RULES:
                            aggregated_results[code]["fund_score"] += res.score
                        aggregated_results[code]["total_score"] += res.score
                    except Exception as e:
                        logger.error(f"Error applying rule {rule_key} to {code}: {e}")
                        aggregated_results[code]["all_passed"] = False
            except Exception as e:
                logger.error(f"Error initializing legacy rule {rule_key}: {e}")
                for code in stock_codes:
                    aggregated_results[code]["all_passed"] = False

    # Normalize scores and save to pool 2
    num_tech_rules = sum(1 for r in rules_config if r.get("rule_key") in TECH_RULES)
    num_fund_rules = sum(1 for r in rules_config if r.get("rule_key") in FUND_RULES)
    
    selected_count = 0

    for stock in pool1_stocks:
        code = stock["stock_code"]
        res = aggregated_results[code]
        
        tech_score = res["tech_score"] / num_tech_rules if num_tech_rules > 0 else 0.0
        fund_score = res["fund_score"] / num_fund_rules if num_fund_rules > 0 else 0.0
        total_score = res["total_score"]
        is_selected = res["all_passed"] and total_score > 0
        
        # Save to pool 2
        await repo.add_pool2_stock(conn, report_id, {
            "pool_1_id": stock["id"],
            "stock_code": code,
            "stock_name": stock.get("stock_name"),
            "tech_score": tech_score,
            "fund_score": fund_score,
            "total_score": total_score,
            "rule_results": res["rule_results"],
            "is_selected": is_selected,
        })
        
        if is_selected:
            selected_count += 1

    return selected_count