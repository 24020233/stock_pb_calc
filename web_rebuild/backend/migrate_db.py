#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migration script to update table structure."""

import asyncio
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


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s",
            (table_name,),
        )
        return cursor.fetchone()[0] > 0
    finally:
        cursor.close()


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND column_name = %s
            """,
            (table_name, column_name),
        )
        return cursor.fetchone()[0] > 0
    finally:
        cursor.close()


def backup_table(conn, table_name: str, backup_suffix: str = "_old") -> None:
    """Create a backup of a table if it exists."""
    cursor = conn.cursor()
    backup_name = f"{table_name}{backup_suffix}"

    if table_exists(conn, backup_name):
        print(f"Backup table {backup_name} already exists, skipping backup.")
        return

    try:
        print(f"Creating backup of {table_name} as {backup_name}...")
        cursor.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}")
        conn.commit()
        print("Backup created successfully.")
    except MySQLError as e:
        print(f"Error creating backup table: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def migrate_article_detail_table(conn) -> None:
    """Migrate wx_article_detail table structure."""
    cursor = conn.cursor()

    try:
        print("Checking if table migration is needed...")

        # Check if the table has old structure
        has_old_columns = False
        old_columns = ["article_url", "post_time", "wxid", "html"]
        for col in old_columns:
            if column_exists(conn, "wx_article_detail", col):
                has_old_columns = True
                break

        if not has_old_columns:
            print("Table structure is already up to date.")
            return

        # Step 1: Backup table
        backup_table(conn, "wx_article_detail")

        # Step 2: Modify table structure
        print("Modifying table structure...")

        # Rename columns
        if column_exists(conn, "wx_article_detail", "article_url"):
            cursor.execute(
                "ALTER TABLE wx_article_detail CHANGE COLUMN article_url url VARCHAR(2048) NOT NULL COMMENT '文章链接'"
            )
            print("Renamed column: article_url -> url")

        if column_exists(conn, "wx_article_detail", "post_time"):
            cursor.execute(
                "ALTER TABLE wx_article_detail CHANGE COLUMN post_time pubtime BIGINT NULL COMMENT '发文时间戳'"
            )
            print("Renamed column: post_time -> pubtime")

        if column_exists(conn, "wx_article_detail", "wxid"):
            cursor.execute(
                "ALTER TABLE wx_article_detail CHANGE COLUMN wxid hashid VARCHAR(64) NULL COMMENT '文章唯一hashid'"
            )
            print("Renamed column: wxid -> hashid")

        if column_exists(conn, "wx_article_detail", "html"):
            cursor.execute(
                "ALTER TABLE wx_article_detail CHANGE COLUMN html content MEDIUMTEXT NULL COMMENT '文章正文内容'"
            )
            print("Renamed column: html -> content")

        # Add new columns
        if not column_exists(conn, "wx_article_detail", "nick_name"):
            cursor.execute(
                "ALTER TABLE wx_article_detail ADD COLUMN nick_name VARCHAR(128) NULL COMMENT '公众号名字' AFTER hashid"
            )
            print("Added column: nick_name")

        # Update url_hash generated column
        if column_exists(conn, "wx_article_detail", "url_hash"):
            cursor.execute("ALTER TABLE wx_article_detail DROP COLUMN url_hash")

        cursor.execute(
            "ALTER TABLE wx_article_detail ADD COLUMN url_hash BINARY(16) GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED COMMENT 'URL哈希' AFTER url"
        )
        print("Updated generated column: url_hash")

        # Update indexes
        print("Updating indexes...")
        cursor.execute("DROP INDEX IF EXISTS uk_article_url ON wx_article_detail")
        cursor.execute("DROP INDEX IF EXISTS idx_wxid ON wx_article_detail")
        cursor.execute("CREATE UNIQUE INDEX uk_url ON wx_article_detail (url_hash)")
        cursor.execute("CREATE INDEX idx_hashid ON wx_article_detail (hashid)")
        cursor.execute("CREATE INDEX idx_nick_name ON wx_article_detail (nick_name)")

        # Step 3: Update data
        print("Updating existing data...")
        cursor.execute(
            """
            UPDATE wx_article_detail d
            JOIN wx_article_list l ON d.article_list_id = l.id
            JOIN wx_mp_account a ON l.account_id = a.id
            SET d.nick_name = a.mp_nickname
            WHERE d.nick_name IS NULL
            """
        )
        affected_rows = cursor.rowcount
        print(f"Updated {affected_rows} records with nick_name.")

        conn.commit()
        print("Table migration completed successfully.")

    except MySQLError as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def main():
    """Main entry point for migration."""
    print("Starting database migration...")
    try:
        config = get_mysql_config()
        conn = mysql.connector.connect(**config)
        print(f"Connected to database: {config['database']}@{config['host']}")

        if not table_exists(conn, "wx_article_detail"):
            print("Table wx_article_detail does not exist. Please run init_db.py first.")
            conn.close()
            return

        migrate_article_detail_table(conn)

        conn.close()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
