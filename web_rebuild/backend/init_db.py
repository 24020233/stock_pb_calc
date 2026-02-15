#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database initialization script."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def get_mysql_config(without_db: bool = False) -> dict:
    """Get MySQL configuration from environment."""
    config = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "charset": "utf8mb4",
    }
    if not without_db:
        config["database"] = os.getenv("MYSQL_DATABASE", "wechat_crawler")
    return config


def create_database_if_not_exists() -> None:
    """Create database if it doesn't exist."""
    config = get_mysql_config(without_db=True)
    database = os.getenv("MYSQL_DATABASE", "wechat_crawler")

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{database}' created or already exists.")
        cursor.close()
        conn.close()
    except MySQLError as e:
        print(f"Error creating database: {e}")
        sys.exit(1)


def init_tables() -> None:
    """Initialize database tables from schema.sql."""
    config = get_mysql_config()
    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        print(f"Schema file not found: {schema_path}")
        sys.exit(1)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Split SQL by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

        for stmt in statements:
            if stmt:
                cursor.execute(stmt)

        conn.commit()
        print("Database tables initialized successfully.")

        # Show created tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")

        cursor.close()
        conn.close()
    except MySQLError as e:
        print(f"Error initializing tables: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    print("Initializing database...")
    create_database_if_not_exists()
    init_tables()
    print("Database initialization completed.")


if __name__ == "__main__":
    main()
