# -*- coding: utf-8 -*-
"""Rule engine base classes for stock selection."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuleResult:
    """Result of a rule check."""

    passed: bool
    score: float = 0.0
    reason: str = ""
    details: Optional[Dict[str, Any]] = field(default_factory=dict)


class BaseRule:
    """Base class for stock selection rules."""

    def __init__(self, params: Dict[str, Any]):
        """Initialize rule with parameters.

        Args:
            params: Dictionary containing rule-specific parameters
        """
        self.params = params

    def check(self, stock_context: Dict[str, Any]) -> RuleResult:
        """Check if a stock passes this rule.

        Args:
            stock_context: Dictionary containing stock data including:
                - stock_code: str
                - stock_name: str
                - snapshot_data: dict with price, change_pct, volume_ratio, etc.
                - related_topic: optional topic data

        Returns:
            RuleResult with pass/fail status, score, and reason
        """
        raise NotImplementedError(f"{self.__class__.__name__}.check() not implemented")

    @property
    def rule_key(self) -> str:
        """Return unique identifier for this rule type."""
        raise NotImplementedError(f"{self.__class__.__name__}.rule_key not implemented")

    @property
    def rule_name(self) -> str:
        """Return human-readable name for this rule."""
        raise NotImplementedError(f"{self.__class__.__name__}.rule_name not implemented")

    @property
    def description(self) -> str:
        """Return description of what this rule does."""
        return ""
