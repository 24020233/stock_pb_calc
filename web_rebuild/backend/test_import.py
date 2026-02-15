#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test rule registry import."""

import traceback

try:
    from rules.registry import list_registered_rules
    rules = list_registered_rules()
    print("Import successful!")
    print("Registered rules:")
    for key, name in rules.items():
        print(f"  - {key}: {name}")
except Exception as e:
    print(f"Import failed: {e}")
    traceback.print_exc()
