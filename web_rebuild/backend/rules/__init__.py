# -*- coding: utf-8 -*-
"""Stock selection rules package."""

from __future__ import annotations

from rules.base import BaseRule, RuleResult
from rules.registry import (
    get_rule_class,
    list_registered_rules,
    register_rule,
    RULE_REGISTRY,
)

__all__ = [
    "BaseRule",
    "RuleResult",
    "register_rule",
    "get_rule_class",
    "list_registered_rules",
    "RULE_REGISTRY",
]
