# -*- coding: utf-8 -*-
"""Rule handler base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RuleTaskResult:
    """规则任务执行结果"""

    rule_key: str
    success: bool
    data: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_key": self.rule_key,
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class BaseRuleHandler(ABC):
    """规则处理器基类

    每个规则处理器负责执行一个独立的选股规则任务，
    接收股票代码列表作为输入，返回规则执行结果。
    """

    @property
    @abstractmethod
    def rule_key(self) -> str:
        """规则识别码，用于在配置中关联处理器"""
        pass

    @property
    def description(self) -> str:
        """规则描述"""
        return ""

    @abstractmethod
    async def execute(
        self,
        stock_codes: List[str],
        params: Dict[str, Any],
        conn: Optional[Any] = None,
    ) -> RuleTaskResult:
        """
        执行规则任务

        Args:
            stock_codes: 输入的股票代码列表
            params: 规则参数（从配置中读取）
            conn: 数据库连接（可选，用于保存数据）

        Returns:
            RuleTaskResult: 执行结果，包含每只股票的规则判断数据
        """
        pass