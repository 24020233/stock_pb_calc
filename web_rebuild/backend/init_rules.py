#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize default strategy rules in database."""

import json
import os
import sys
from pathlib import Path

import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def get_mysql_config() -> dict:
    """Get MySQL configuration from environment."""
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "wechat_crawler"),
        "charset": "utf8mb4",
        "autocommit": False,
    }


def init_default_rules(conn):
    """Initialize default strategy rules."""
    cursor = conn.cursor()

    default_rules = [
        {
            "rule_key": "market_cap",
            "rule_name": "市值筛选",
            "rule_value": {"min_market_cap": 50, "max_market_cap": 500},
            "description": "筛选市值在 50-500 亿之间的股票",
            "is_enabled": True,
            "sort_order": 1,
        },
        {
            "rule_key": "volume_ratio",
            "rule_name": "量比筛选",
            "rule_value": {"min_volume_ratio": 1.5},
            "description": "筛选量比大于等于 1.5 的股票",
            "is_enabled": True,
            "sort_order": 2,
        },
        {
            "rule_key": "price_change",
            "rule_name": "涨跌幅筛选",
            "rule_value": {"min_change_pct": -10, "max_change_pct": 10},
            "description": "筛选涨跌幅在 -10% 到 10% 范围内的股票",
            "is_enabled": True,
            "sort_order": 3,
        },
        {
            "rule_key": "turnover_rate",
            "rule_name": "换手率筛选",
            "rule_value": {"min_turnover": 2.0, "max_turnover": 20.0},
            "description": "筛选换手率在 2%-20% 范围内的股票",
            "is_enabled": True,
            "sort_order": 4,
        },
        {
            "rule_key": "pe_ratio",
            "rule_name": "市盈率筛选",
            "rule_value": {"min_pe": 0, "max_pe": 50},
            "description": "筛选市盈率在 0-50 范围内的股票",
            "is_enabled": True,
            "sort_order": 5,
        },
        {
            "rule_key": "pb_ratio",
            "rule_name": "市净率筛选",
            "rule_value": {"min_pb": 0, "max_pb": 10},
            "description": "筛选市净率在 0-10 范围内的股票",
            "is_enabled": True,
            "sort_order": 6,
        },
        {
            "rule_key": "roe",
            "rule_name": "ROE筛选",
            "rule_value": {"min_roe": 0},
            "description": "筛选ROE大于等于 0% 的股票",
            "is_enabled": True,
            "sort_order": 7,
        },
    ]

    try:
        for rule in default_rules:
            # Check if rule already exists
            cursor.execute(
                "SELECT id FROM strategy_config WHERE rule_key = %s",
                (rule["rule_key"],),
            )
            existing = cursor.fetchone()

            if existing:
                print(f"  Rule {rule['rule_key']} already exists, skipping.")
                continue

            cursor.execute(
                """INSERT INTO strategy_config (rule_key, rule_name, rule_value, description, is_enabled, sort_order)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    rule["rule_key"],
                    rule["rule_name"],
                    json.dumps(rule["rule_value"]),
                    rule["description"],
                    rule["is_enabled"],
                    rule["sort_order"],
                ),
            )
            print(f"  Added rule: {rule['rule_name']} ({rule['rule_key']})")

        conn.commit()
        print("Default rules initialized successfully!")

    except MySQLError as e:
        print(f"Error initializing rules: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def main():
    """Main entry point."""
    print("Initializing default strategy rules...")
    print("=" * 50)

    try:
        config = get_mysql_config()
        conn = mysql.connector.connect(**config)
        print(f"Connected to database: {config['database']}@{config['host']}\n")

        init_default_rules(conn)

        conn.close()
        print("\nInitialization completed successfully!")

    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
