# -*- coding: utf-8 -*-
"""Continuous rise rule handler."""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from rules.handlers.base import BaseRuleHandler, RuleTaskResult
from rules.handlers.registry import register_handler

logger = logging.getLogger(__name__)


@register_handler
class ContinuousRiseHandler(BaseRuleHandler):
    """连续上涨规则处理器

    功能：
    1. 调用 akshare 的 stock_rank_lxsz_ths() 接口获取当日连续上涨股票
    2. 将数据保存到 continuous_rise_data 表
    3. 匹配输入的股票代码列表，返回各股票的连续上涨情况

    输入：股票代码列表
    输出：每只股票的连续上涨数据（连涨天数、连续涨跌幅等）
    """

    @property
    def rule_key(self) -> str:
        return "continuous_rise"

    @property
    def description(self) -> str:
        return "连续上涨规则 - 筛选连续上涨的股票"

    async def execute(
        self,
        stock_codes: List[str],
        params: Dict[str, Any],
        conn: Optional[Any] = None,
    ) -> RuleTaskResult:
        """
        执行连续上涨规则

        Args:
            stock_codes: 输入的股票代码列表
            params: 规则参数（暂未使用，预留扩展）
            conn: 数据库连接

        Returns:
            RuleTaskResult: 包含每只股票的连续上涨数据
        """
        try:
            # 1. 调用 akshare 接口获取连续上涨股票
            import akshare as ak

            logger.info(f"Fetching continuous rise data from akshare...")
            df = ak.stock_rank_lxsz_ths()
            today = date.today()
            logger.info(f"Got {len(df)} continuous rise stocks for {today}")

            # 2. 构建连续上涨股票映射
            rise_stock_map: Dict[str, Dict[str, Any]] = {}
            rows_to_save = []

            for _, row in df.iterrows():
                stock_code = str(row["股票代码"])
                rise_stock_map[stock_code] = {
                    "stock_code": stock_code,
                    "stock_name": row["股票简称"],
                    "close_price": float(row["收盘价"]) if row["收盘价"] else None,
                    "high_price": float(row["最高价"]) if row["最高价"] else None,
                    "low_price": float(row["最低价"]) if row["最低价"] else None,
                    "rise_days": int(row["连涨天数"]) if row["连涨天数"] else 0,
                    "rise_pct": float(row["连续涨跌幅"]) if row["连续涨跌幅"] else 0.0,
                    "turnover_rate": float(row["累计换手率"]) if row["累计换手率"] else 0.0,
                    "industry": row["所属行业"] if row["所属行业"] else "",
                }
                rows_to_save.append(row)

            # 3. 保存数据到数据库
            if conn and rows_to_save:
                await self._save_to_db(conn, rows_to_save, today)

            # 4. 匹配输入股票
            results = []
            for code in stock_codes:
                # 确保股票代码格式一致
                normalized_code = code.zfill(6) if len(code) < 6 else code

                if normalized_code in rise_stock_map:
                    results.append({
                        "stock_code": code,
                        "is_continuous_rise": True,
                        **rise_stock_map[normalized_code],
                    })
                else:
                    results.append({
                        "stock_code": code,
                        "is_continuous_rise": False,
                        "stock_name": "",
                        "rise_days": 0,
                        "rise_pct": 0.0,
                        "close_price": None,
                        "high_price": None,
                        "low_price": None,
                        "turnover_rate": None,
                        "industry": "",
                    })

            logger.info(
                f"Continuous rise check completed: {sum(1 for r in results if r['is_continuous_rise'])} stocks matched"
            )

            return RuleTaskResult(
                rule_key=self.rule_key,
                success=True,
                data=results,
            )

        except Exception as e:
            logger.exception(f"Continuous rise handler error: {e}")
            return RuleTaskResult(
                rule_key=self.rule_key,
                success=False,
                data=[],
                error=str(e),
            )

    async def _save_to_db(
        self, conn: Any, rows: List[Any], data_date: date
    ) -> None:
        """保存数据到数据库

        Args:
            conn: 数据库连接
            rows: 数据行列表
            data_date: 数据日期
        """
        try:
            async with conn.cursor() as cur:
                for row in rows:
                    await cur.execute(
                        """
                        INSERT INTO continuous_rise_data
                        (stock_code, stock_name, close_price, high_price, low_price,
                         rise_days, rise_pct, turnover_rate, industry, data_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        stock_name = VALUES(stock_name),
                        close_price = VALUES(close_price),
                        high_price = VALUES(high_price),
                        low_price = VALUES(low_price),
                        rise_days = VALUES(rise_days),
                        rise_pct = VALUES(rise_pct),
                        turnover_rate = VALUES(turnover_rate),
                        industry = VALUES(industry)
                        """,
                        (
                            str(row["股票代码"]),
                            row["股票简称"],
                            float(row["收盘价"]) if row["收盘价"] else None,
                            float(row["最高价"]) if row["最高价"] else None,
                            float(row["最低价"]) if row["最低价"] else None,
                            int(row["连涨天数"]) if row["连涨天数"] else 0,
                            float(row["连续涨跌幅"]) if row["连续涨跌幅"] else 0.0,
                            float(row["累计换手率"]) if row["累计换手率"] else 0.0,
                            row["所属行业"] if row["所属行业"] else "",
                            data_date,
                        ),
                    )
            logger.info(f"Saved {len(rows)} continuous rise records to database")
        except Exception as e:
            logger.exception(f"Failed to save continuous rise data: {e}")
            # 不抛出异常，允许任务继续执行并返回结果