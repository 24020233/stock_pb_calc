# -*- coding: utf-8 -*-
"""Technical analysis rules for stock selection."""

import logging
from typing import Any, Dict

import akshare as ak

from rules.base import BaseRule, RuleResult
from rules.registry import register_rule

logger = logging.getLogger(__name__)


@register_rule
class MarketCapRule(BaseRule):
    """Rule to filter stocks by market capitalization."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.min_market_cap = params.get("min_market_cap", 50)  # in 亿, default 50亿
        self.max_market_cap = params.get("max_market_cap", 500)  # in 亿, default 500亿

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock market cap is within range."""
        stock_code = stock_context.get("stock_code")
        snapshot_data = stock_context.get("snapshot_data", {})

        # Try to get market cap from snapshot data first
        market_cap = snapshot_data.get("market_cap")

        # If not in snapshot, fetch from akshare
        if market_cap is None:
            try:
                stock_info = ak.stock_individual_info_em(stock=f"{stock_code}SH")
                if stock_info.empty:
                    stock_info = ak.stock_individual_info_em(stock=f"{stock_code}SZ")

                if not stock_info.empty:
                    # Market cap is usually in "总市值" field in 亿元
                    for _, row in stock_info.iterrows():
                        if "总市值" in str(row.get("item", "")):
                            value = row.get("value", "")
                            if isinstance(value, (int, float)):
                                market_cap = float(value) / 100000000  # convert to 亿
                                break
            except Exception as e:
                logger.warning(f"Failed to fetch market cap for {stock_code}: {e}")

        if market_cap is None:
            return RuleResult(
                passed=True,  # Pass if we can't get market cap
                score=0.5,
                reason="无法获取市值数据",
                details={"market_cap": None},
            )

        passed = self.min_market_cap <= market_cap <= self.max_market_cap
        score = 1.0 if passed else 0.0
        reason = f"市值 {market_cap:.2f}亿" + (
            f"在[{self.min_market_cap}, {self.max_market_cap}]范围内"
            if passed
            else f"不在[{self.min_market_cap}, {self.max_market_cap}]范围内"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"market_cap": market_cap},
        )

    @property
    def rule_key(self) -> str:
        return "market_cap"

    @property
    def rule_name(self) -> str:
        return "市值筛选"

    @property
    def description(self) -> str:
        return f"筛选市值在 {self.min_market_cap}-{self.max_market_cap} 亿之间的股票"


@register_rule
class VolumeRatioRule(BaseRule):
    """Rule to filter stocks by volume ratio (量比)."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.min_volume_ratio = params.get("min_volume_ratio", 1.5)  # default 1.5

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock volume ratio meets minimum."""
        snapshot_data = stock_context.get("snapshot_data", {})
        volume_ratio = snapshot_data.get("volume_ratio", 0)

        passed = volume_ratio >= self.min_volume_ratio
        score = min(volume_ratio / self.min_volume_ratio, 1.0) if passed else 0.0
        reason = f"量比 {volume_ratio:.2f}" + (
            f" >= {self.min_volume_ratio}" if passed else f" < {self.min_volume_ratio}"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"volume_ratio": volume_ratio},
        )

    @property
    def rule_key(self) -> str:
        return "volume_ratio"

    @property
    def rule_name(self) -> str:
        return "量比筛选"

    @property
    def description(self) -> str:
        return f"筛选量比大于等于 {self.min_volume_ratio} 的股票"


@register_rule
class PriceChangeRule(BaseRule):
    """Rule to filter stocks by price change percentage."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.min_change_pct = params.get("min_change_pct", -10)  # default -10%
        self.max_change_pct = params.get("max_change_pct", 10)  # default 10%

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock price change is within range."""
        snapshot_data = stock_context.get("snapshot_data", {})
        change_pct = snapshot_data.get("change_pct", 0)

        passed = self.min_change_pct <= change_pct <= self.max_change_pct
        score = 1.0 if passed else 0.0
        reason = f"涨跌幅 {change_pct:.2f}%" + (
            f"在[{self.min_change_pct}%, {self.max_change_pct}%]范围内"
            if passed
            else f"不在[{self.min_change_pct}%, {self.max_change_pct}%]范围内"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"change_pct": change_pct},
        )

    @property
    def rule_key(self) -> str:
        return "price_change"

    @property
    def rule_name(self) -> str:
        return "涨跌幅筛选"

    @property
    def description(self) -> str:
        return f"筛选涨跌幅在 {self.min_change_pct}%-{self.max_change_pct}% 范围内的股票"


@register_rule
class TurnoverRateRule(BaseRule):
    """Rule to filter stocks by turnover rate (换手率)."""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.min_turnover = params.get("min_turnover", 2.0)  # default 2%
        self.max_turnover = params.get("max_turnover", 20.0)  # default 20%

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if stock turnover rate is within range."""
        snapshot_data = stock_context.get("snapshot_data", {})
        turnover_rate = snapshot_data.get("turnover_rate", 0)

        passed = self.min_turnover <= turnover_rate <= self.max_turnover
        score = 1.0 if passed else 0.0
        reason = f"换手率 {turnover_rate:.2f}%" + (
            f"在[{self.min_turnover}%, {self.max_turnover}%]范围内"
            if passed
            else f"不在[{self.min_turnover}%, {self.max_turnover}%]范围内"
        )

        return RuleResult(
            passed=passed,
            score=score,
            reason=reason,
            details={"turnover_rate": turnover_rate},
        )

    @property
    def rule_key(self) -> str:
        return "turnover_rate"

    @property
    def rule_name(self) -> str:
        return "换手率筛选"

    @property
    def description(self) -> str:
        return f"筛选换手率在 {self.min_turnover}%-{self.max_turnover}% 范围内的股票"
