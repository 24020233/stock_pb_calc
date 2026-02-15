# -*- coding: utf-8 -*-
"""Fundamental analysis rules for stock selection."""

import logging
from typing import Any, Dict

import akshare as ak

from rules.base import BaseRule, RuleResult
from rules.registry import register_rule

logger = logging.getLogger(__name__)


@register_rule
class PERatioRule(BaseRule):
    """Rule to filter stocks by P/E ratio (市盈率)."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.max_pe = params.get("max_pe", 50)  # default max PE 50
        self.min_pe = params.get("min_pe", 0)  # default min PE 0

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock P/E ratio is within range."""
        stock_code = stock_context.get("stock_code")
        snapshot_data = stock_context.get("snapshot_data", {})

        # Try to get PE from snapshot data first
        pe_ratio = snapshot_data.get("pe_ratio")

        # If not in snapshot, fetch from akshare
        if pe_ratio is None:
            try:
                # Get stock real-time data
                stock_zh_a_spot_df = ak.stock_zh_a_spot_em()
                stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df["代码"] == stock_code]

                if not stock_data.empty:
                    pe_ratio = stock_data.iloc[0].get("市盈率-动态", 0)
                    if pe_ratio == "-":
                        pe_ratio = None
                    elif pe_ratio is not None:
                        pe_ratio = float(pe_ratio)
            except Exception as e:
                logger.warning(f"Failed to fetch PE ratio for {stock_code}: {e}")

        if pe_ratio is None:
            return RuleResult(
                passed=True,  # Pass if we can't get PE ratio
                score=0.5,
                reason="无法获取市盈率数据",
                details={"pe_ratio": None},
            )

        passed = self.min_pe <= pe_ratio <= self.max_pe
        score = 1.0 if passed else 0.0
        reason = f"市盈率 {pe_ratio:.2f}" + (
            f"在[{self.min_pe}, {self.max_pe}]范围内"
            if passed
            else f"不在[{self.min_pe}, {self.max_pe}]范围内"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"pe_ratio": pe_ratio},
        )

    @property
    def rule_key(self) -> str:
        return "pe_ratio"

    @property
    def rule_name(self) -> str:
        return "市盈率筛选"

    @property
    def description(self) -> str:
        return f"筛选市盈率在 {self.min_pe}-{self.max_pe} 范围内的股票"


@register_rule
class PBRatioRule(BaseRule):
    """Rule to filter stocks by P/B ratio (市净率)."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.max_pb = params.get("max_pb", 10)  # default max PB 10
        self.min_pb = params.get("min_pb", 0)  # default min PB 0

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock P/B ratio is within range."""
        stock_code = stock_context.get("stock_code")
        snapshot_data = stock_context.get("snapshot_data", {})

        # Try to get PB from snapshot data first
        pb_ratio = snapshot_data.get("pb_ratio")

        # If not in snapshot, fetch from akshare
        if pb_ratio is None:
            try:
                stock_zh_a_spot_df = ak.stock_zh_a_spot_em()
                stock_data = stock_zh_a_spot_df[stock_zh_a_spot_df["代码"] == stock_code]

                if not stock_data.empty:
                    pb_ratio = stock_data.iloc[0].get("市净率", 0)
                    if pb_ratio == "-":
                        pb_ratio = None
                    elif pb_ratio is not None:
                        pb_ratio = float(pb_ratio)
            except Exception as e:
                logger.warning(f"Failed to fetch PB ratio for {stock_code}: {e}")

        if pb_ratio is None:
            return RuleResult(
                passed=True,  # Pass if we can't get PB ratio
                score=0.5,
                reason="无法获取市净率数据",
                details={"pb_ratio": None},
            )

        passed = self.min_pb <= pb_ratio <= self.max_pb
        score = 1.0 if passed else 0.0
        reason = f"市净率 {pb_ratio:.2f}" + (
            f"在[{self.min_pb}, {self.max_pb}]范围内"
            if passed
            else f"不在[{self.min_pb}, {self.max_pb}]范围内"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"pb_ratio": pb_ratio},
        )

    @property
    def rule_key(self) -> str:
        return "pb_ratio"

    @property
    def rule_name(self) -> str:
        return "市净率筛选"

    @property
    def description(self) -> str:
        return f"筛选市净率在 {self.min_pb}-{self.max_pb} 范围内的股票"


@register_rule
class ROERule(BaseRule):
    """Rule to filter stocks by ROE (净资产收益率)."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.min_roe = params.get("min_roe", 0)  # default min ROE 0

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock ROE meets minimum."""
        stock_code = stock_context.get("stock_code")
        snapshot_data = stock_context.get("snapshot_data", {})

        # Try to get ROE from snapshot data first
        roe = snapshot_data.get("roe")

        # If not in snapshot, fetch from akshare (requires historical data)
        if roe is None:
            try:
                # Get financial data
                fin_data = ak.stock_financial_analysis_indicator(stock=stock_code)
                if not fin_data.empty:
                    # Get latest ROE
                    roe = fin_data.iloc[0].get("净资产收益率(ROE)-加权平均(%)", 0)
                    if roe is not None:
                        roe = float(roe)
            except Exception as e:
                logger.warning(f"Failed to fetch ROE for {stock_code}: {e}")

        if roe is None:
            return RuleResult(
                passed=True,  # Pass if we can't get ROE
                score=0.5,
                reason="无法获取ROE数据",
                details={"roe": None},
            )

        passed = roe >= self.min_roe
        score = 1.0 if passed else 0.0
        reason = f"ROE {roe:.2f}%" + (
            f" >= {self.min_roe}%" if passed else f" < {self.min_roe}%"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"roe": roe},
        )

    @property
    def rule_key(self) -> str:
        return "roe"

    @property
    def rule_name(self) -> str:
        return "ROE筛选"

    @property
    def description(self) -> str:
        return f"筛选ROE大于等于 {self.min_roe}% 的股票"
