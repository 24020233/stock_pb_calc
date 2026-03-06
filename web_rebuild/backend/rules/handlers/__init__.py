# -*- coding: utf-8 -*-
"""Rule handlers module."""

from rules.handlers.base import BaseRuleHandler, RuleTaskResult
from rules.handlers.registry import HANDLER_REGISTRY, register_handler, get_handler

# 导入所有处理器以触发注册
from rules.handlers import continuous_rise  # noqa: F401

__all__ = [
    "BaseRuleHandler",
    "RuleTaskResult",
    "HANDLER_REGISTRY",
    "register_handler",
    "get_handler",
]