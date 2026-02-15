# -*- coding: utf-8 -*-
"""Rule registry for stock selection engine."""

from typing import Dict, Type

from rules.base import BaseRule

# Global registry mapping rule_key to rule class
RULE_REGISTRY: Dict[str, Type[BaseRule]] = {}


def register_rule(rule_class: Type[BaseRule]) -> Type[BaseRule]:
    """Decorator to register a rule class in the global registry.

    Args:
        rule_class: The rule class to register

    Returns:
        The rule class unchanged

    Raises:
        ValueError: If rule_key is already registered
    """
    if not hasattr(rule_class, "rule_key"):
        raise ValueError(f"Rule class {rule_class.__name__} has no rule_key")

    # Create a temp instance to get the rule_key
    temp_instance = rule_class({})
    key = temp_instance.rule_key

    if key in RULE_REGISTRY:
        raise ValueError(f"Rule key '{key}' already registered")

    RULE_REGISTRY[key] = rule_class
    return rule_class


def get_rule_class(rule_key: str) -> Type[BaseRule]:
    """Get rule class by rule_key.

    Args:
        rule_key: The unique rule identifier

    Returns:
        The rule class

    Raises:
        KeyError: If rule_key not found in registry
    """
    if rule_key not in RULE_REGISTRY:
        raise KeyError(f"Rule '{rule_key}' not found in registry")
    return RULE_REGISTRY[rule_key]


def list_registered_rules() -> Dict[str, str]:
    """List all registered rules with their names.

    Returns:
        Dictionary mapping rule_key to rule_name
    """
    result = {}
    for key, rule_class in RULE_REGISTRY.items():
        temp_instance = rule_class({})
        result[key] = temp_instance.rule_name
    return result


# Import and register all rule implementations
# This ensures all rules are available in the registry
from rules.technical import *  # noqa: F401, F403
from rules.fundamental import *  # noqa: F401, F403
