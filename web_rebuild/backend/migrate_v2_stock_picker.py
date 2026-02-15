#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migration script V2 - Add stock picker tables."""

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


def run_migration(conn):
    """Run the migration to add stock picker tables."""
    cursor = conn.cursor()

    # Migration SQL
    migrations = [
        # 1. reports table
        """
        CREATE TABLE IF NOT EXISTS reports (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          report_date DATE NOT NULL COMMENT '报告日期',
          status VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT '状态: pending, processing, completed, error',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_report_date (report_date),
          KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日报告主表'
        """,
        # 2. raw_articles table
        """
        CREATE TABLE IF NOT EXISTS raw_articles (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
          title VARCHAR(512) NULL COMMENT '文章标题',
          content MEDIUMTEXT NULL COMMENT '全文内容',
          source_account VARCHAR(128) NULL COMMENT '公众号名称',
          publish_time BIGINT NULL COMMENT '发布时间戳',
          url VARCHAR(2048) NULL COMMENT '原文链接',
          article_detail_id BIGINT UNSIGNED NULL COMMENT '关联 wx_article_detail.id',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_report_id (report_id),
          KEY idx_article_detail_id (article_detail_id),
          CONSTRAINT fk_raw_articles_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情报源表'
        """,
        # 3. hot_topics table
        """
        CREATE TABLE IF NOT EXISTS hot_topics (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
          topic_name VARCHAR(256) NOT NULL COMMENT 'AI提炼的热点名称',
          related_boards JSON NULL COMMENT '关联的东财板块名数组',
          logic_summary TEXT NULL COMMENT 'AI总结的逻辑摘要',
          source_article_ids JSON NULL COMMENT '关联 raw_articles.id 的数组',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_report_id (report_id),
          CONSTRAINT fk_hot_topics_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='热点风口表'
        """,
        # 4. stock_pool_1 table
        """
        CREATE TABLE IF NOT EXISTS stock_pool_1 (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
          stock_code VARCHAR(32) NOT NULL COMMENT '股票代码',
          stock_name VARCHAR(128) NOT NULL COMMENT '股票名称',
          related_topic_id BIGINT UNSIGNED NULL COMMENT '关联 hot_topics.id',
          snapshot_data JSON NULL COMMENT '行情快照: price, change_pct, volume_ratio等',
          match_reason VARCHAR(512) NULL COMMENT '入选理由',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_report_id (report_id),
          KEY idx_topic_id (related_topic_id),
          KEY idx_stock_code (stock_code),
          CONSTRAINT fk_pool1_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
          CONSTRAINT fk_pool1_topic FOREIGN KEY (related_topic_id) REFERENCES hot_topics(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='异动初筛表'
        """,
        # 5. stock_pool_2 table
        """
        CREATE TABLE IF NOT EXISTS stock_pool_2 (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          report_id BIGINT UNSIGNED NOT NULL COMMENT '关联 reports.id',
          pool_1_id BIGINT UNSIGNED NOT NULL COMMENT '关联 stock_pool_1.id',
          stock_code VARCHAR(32) NOT NULL COMMENT '股票代码',
          stock_name VARCHAR(128) NOT NULL COMMENT '股票名称',
          tech_score DECIMAL(5,2) NULL COMMENT '技术面评分',
          fund_score DECIMAL(5,2) NULL COMMENT '基本面评分',
          total_score DECIMAL(5,2) NULL COMMENT '总分',
          ai_analysis TEXT NULL COMMENT 'AI分析文本',
          rule_results JSON NULL COMMENT '各规则检查结果',
          is_selected BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否最终入选',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_report_id (report_id),
          KEY idx_pool1_id (pool_1_id),
          KEY idx_is_selected (is_selected),
          CONSTRAINT fk_pool2_report FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
          CONSTRAINT fk_pool2_pool1 FOREIGN KEY (pool_1_id) REFERENCES stock_pool_1(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='深度精选表'
        """,
        # 6. target_accounts table
        """
        CREATE TABLE IF NOT EXISTS target_accounts (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          account_name VARCHAR(128) NOT NULL COMMENT '公众号名称',
          wx_id VARCHAR(64) NULL COMMENT '微信号',
          status VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '状态: active, inactive',
          sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='目标公众号列表'
        """,
        # 7. strategy_config table
        """
        CREATE TABLE IF NOT EXISTS strategy_config (
          id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
          rule_key VARCHAR(128) NOT NULL COMMENT '规则标识',
          rule_name VARCHAR(128) NOT NULL COMMENT '规则名称',
          rule_value JSON NOT NULL COMMENT '规则参数值',
          description TEXT NULL COMMENT '描述',
          is_enabled BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
          sort_order INT NOT NULL DEFAULT 0 COMMENT '执行顺序',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uk_rule_key (rule_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略参数配置表'
        """,
    ]

    try:
        print("Starting database migration V2 (stock picker tables)...")

        for idx, sql in enumerate(migrations, 1):
            table_name = sql.split("IF NOT EXISTS ")[1].split("(")[0].strip()
            if table_exists(conn, table_name):
                print(f"  Table {table_name} already exists, skipping.")
                continue

            print(f"  Creating table {idx}/{len(migrations)}: {table_name}...")
            cursor.execute(sql)

        conn.commit()
        print("Migration V2 completed successfully!")

    except MySQLError as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def main():
    """Main entry point for migration."""
    print("Stock Picker Database Migration V2")
    print("=" * 50)

    try:
        config = get_mysql_config()
        conn = mysql.connector.connect(**config)
        print(f"Connected to database: {config['database']}@{config['host']}\n")

        run_migration(conn)

        conn.close()
        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
