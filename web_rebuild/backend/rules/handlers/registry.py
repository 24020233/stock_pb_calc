# -*- coding: utf-8 -*-
"""Rule handler registry."""

import logging
from typing import Dict, Optional, Type

from rules.handlers.base import BaseRuleHandler

logger = logging.getLogger(__name__)

# 规则处理器注册表：rule_key -> handler class
HANDLER_REGISTRY: Dict[str, Type[BaseRuleHandler]] = {}


def register_handler(handler_class: Type[BaseRuleHandler]) -> Type[BaseRuleHandler]:
    """注册规则处理器

    Args:
        handler_class: 处理器类

    Returns:
        注册后的处理器类

    Raises:
        ValueError: 如果 rule_key 已被注册或处理器类无效
    """
    # 创建临时实例获取 rule_key
    try:
        temp_instance = handler_class()
        key = temp_instance.rule_key
    except Exception as e:
        raise ValueError(f"Invalid handler class {handler_class.__name__}: {e}")

    if key in HANDLER_REGISTRY:
        logger.warning(f"Handler key '{key}' already registered, overwriting")

    HANDLER_REGISTRY[key] = handler_class
    logger.info(f"Registered rule handler: {key} -> {handler_class.__name__}")

    return handler_class


def get_handler(rule_key: str) -> Optional[BaseRuleHandler]:
    """获取规则处理器实例

    Args:
        rule_key: 规则识别码

    Returns:
        处理器实例，如果未找到返回 None
    """
    handler_class = HANDLER_REGISTRY.get(rule_key)
    if handler_class is None:
        logger.warning(f"Handler '{rule_key}' not found in registry")
        return None
    return handler_class()


def list_handlers() -> Dict[str, str]:
    """列出所有已注册的处理器

    Returns:
        Dict[str, str]: rule_key -> description 的映射
    """
    result = {}
    for key, handler_class in HANDLER_REGISTRY.items():
        try:
            instance = handler_class()
            result[key] = instance.description or instance.rule_key
        except Exception:
            result[key] = key
    return result