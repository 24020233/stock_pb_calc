# -*- coding: utf-8 -*-
"""Rule task executor for parallel execution of rule tasks."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from aiomysql import Connection

from rules.handlers.base import RuleTaskResult
from rules.handlers.registry import get_handler

logger = logging.getLogger(__name__)


async def execute_rule_tasks(
    conn: Connection,
    stock_codes: List[str],
    rules_config: List[Dict[str, Any]],
) -> Dict[str, RuleTaskResult]:
    """
    并行执行多个规则任务

    Args:
        conn: 数据库连接
        stock_codes: 输入的股票代码列表
        rules_config: 启用的规则配置列表，每项包含：
            - rule_key: 规则标识
            - rule_handler: 处理器识别码
            - rule_value: 规则参数
            - is_enabled: 是否启用

    Returns:
        Dict[str, RuleTaskResult]: 各规则的执行结果，key 为 rule_key
    """
    # 过滤启用的规则并构建任务
    tasks = []

    for rule in rules_config:
        if not rule.get("is_enabled", False):
            continue

        rule_key = rule.get("rule_key")
        rule_handler = rule.get("rule_handler")

        if not rule_handler:
            logger.warning(f"Rule '{rule_key}' has no handler, skipping")
            continue

        handler = get_handler(rule_handler)
        if handler is None:
            logger.warning(f"Handler '{rule_handler}' not found for rule '{rule_key}', skipping")
            continue

        # 创建任务
        task = handler.execute(
            stock_codes=stock_codes,
            params=rule.get("rule_value", {}),
            conn=conn,
        )
        tasks.append((rule_key, task))
        logger.info(f"Scheduled rule task: {rule_key} -> {rule_handler}")

    if not tasks:
        logger.info("No rule tasks to execute")
        return {}

    # 并行执行所有任务
    logger.info(f"Executing {len(tasks)} rule tasks in parallel...")
    coroutines = [task for _, task in tasks]
    task_results = await asyncio.gather(*coroutines, return_exceptions=True)

    # 收集结果
    results: Dict[str, RuleTaskResult] = {}
    for (rule_key, _), result in zip(tasks, task_results):
        if isinstance(result, Exception):
            logger.exception(f"Rule task '{rule_key}' failed with exception: {result}")
            results[rule_key] = RuleTaskResult(
                rule_key=rule_key,
                success=False,
                data=[],
                error=str(result),
            )
        elif isinstance(result, RuleTaskResult):
            results[rule_key] = result
            if result.success:
                logger.info(f"Rule task '{rule_key}' completed: {len(result.data)} results")
            else:
                logger.error(f"Rule task '{rule_key}' failed: {result.error}")
        else:
            logger.warning(f"Rule task '{rule_key}' returned unexpected type: {type(result)}")
            results[rule_key] = RuleTaskResult(
                rule_key=rule_key,
                success=False,
                data=[],
                error=f"Unexpected result type: {type(result)}",
            )

    return results


async def get_enabled_rules(conn: Connection) -> List[Dict[str, Any]]:
    """
    获取启用的规则配置

    Args:
        conn: 数据库连接

    Returns:
        List[Dict]: 规则配置列表
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT rule_key, rule_name, rule_handler, rule_value, is_enabled, sort_order
            FROM strategy_config
            WHERE is_enabled = TRUE
            ORDER BY sort_order, id
            """
        )
        rows = await cur.fetchall()

    return [
        {
            "rule_key": row[0],
            "rule_name": row[1],
            "rule_handler": row[2],
            "rule_value": row[3] if isinstance(row[3], dict) else {},
            "is_enabled": row[4],
            "sort_order": row[5],
        }
        for row in rows
    ]


def merge_rule_results(
    stock_codes: List[str],
    rule_results: Dict[str, RuleTaskResult],
) -> List[Dict[str, Any]]:
    """
    合并多个规则的结果

    Args:
        stock_codes: 股票代码列表
        rule_results: 各规则的执行结果

    Returns:
        List[Dict]: 合并后的结果，每只股票一个字典，包含所有规则的数据
    """
    merged = {}

    # 初始化所有股票
    for code in stock_codes:
        merged[code] = {"stock_code": code, "rules": {}}

    # 合并各规则结果
    for rule_key, result in rule_results.items():
        if not result.success:
            continue

        for stock_data in result.data:
            code = stock_data.get("stock_code")
            if code in merged:
                merged[code]["rules"][rule_key] = stock_data

    return list(merged.values())