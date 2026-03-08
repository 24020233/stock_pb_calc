#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch Eastmoney sector list and persist it to MySQL."""

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlencode

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error as MySQLError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings

API_URL = "https://push2.eastmoney.com/api/qt/clist/get"
PAGE_RANGE = range(1, 6)
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
PROXY_ENV_KEYS = [
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
]
CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sectors (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sector_id VARCHAR(32) NOT NULL COMMENT '板块ID',
  sector_name VARCHAR(128) NOT NULL COMMENT '板块名称',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_sector_id (sector_id),
  KEY idx_sector_name (sector_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='板块信息表'
"""

INSERT_SQL = """
INSERT INTO sectors (sector_id, sector_name)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE
  sector_name = VALUES(sector_name),
  updated_at = CURRENT_TIMESTAMP
"""

COUNT_SQL = "SELECT COUNT(*) FROM sectors"


@contextmanager
def proxy_guard():
    """Temporarily disable proxy for Eastmoney requests."""
    disable_proxy = os.getenv("EASTMONEY_DISABLE_PROXY", "1").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not disable_proxy:
        yield
        return

    backup: Dict[str, str] = {}
    for key in PROXY_ENV_KEYS:
        value = os.environ.pop(key, None)
        if value is not None:
            backup[key] = value

    try:
        yield
    finally:
        os.environ.update(backup)


def load_env() -> None:
    """Load environment variables from web_rebuild/.env if present."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(env_path, override=True)


def get_mysql_config() -> Dict[str, object]:
    """Build MySQL config from application settings."""
    settings = get_settings()
    disable_ssl = os.getenv("MYSQL_DISABLE_SSL", "1").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    config = {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "database": settings.mysql_database,
        "charset": "utf8mb4",
    }
    if disable_ssl:
        config["ssl_disabled"] = True
    return config


def build_params(page_number: int) -> Dict[str, object]:
    """Build request params for Eastmoney API."""
    return {
        "np": "1",
        "fltt": "1",
        "invt": "2",
        "cb": "jQuery37106721039112435286_1772894267509",
        "fs": "m:90+t:3+f:!50",
        "fields": "f12,f13,f14,f1,f2,f4,f3,f152,f20,f8,f104,f105,f128,f140,f141,f207,f208,f209,f136,f222",
        "fid": "f3",
        "pn": page_number,
        "pz": "100",
        "po": "1",
        "dect": "1",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "wbp2u": "|0|0|0|web",
        "_": "1772894267513",
    }


def parse_jsonp(response_text: str) -> Dict:
    """Extract JSON payload from JSONP response."""
    start = response_text.find("(")
    end = response_text.rfind(")")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("接口返回不是合法的 JSONP 数据")

    json_text = response_text[start + 1 : end]
    return json.loads(json_text)


def parse_payload_text(payload_text: str) -> Dict:
    """Parse either raw JSON or JSONP response text."""
    text = payload_text.strip()
    if not text:
        raise ValueError("响应内容为空")

    if text.startswith("{"):
        return json.loads(text)
    return parse_jsonp(text)


def extract_sectors(payload: Dict) -> List[Dict[str, str]]:
    """Extract sector records from Eastmoney payload."""
    diff = ((payload.get("data") or {}).get("diff")) or []

    sectors: List[Dict[str, str]] = []
    for item in diff:
        sector_id = str(item.get("f12") or "").strip()
        sector_name = str(item.get("f14") or "").strip()
        if not sector_id or not sector_name:
            continue
        sectors.append({"sector_id": sector_id, "sector_name": sector_name})

    return sectors


def fetch_sector_page(page_number: int) -> List[Dict[str, str]]:
    """Fetch and parse a single sector page."""
    request_url = f"{API_URL}?{urlencode(build_params(page_number))}"

    for attempt in range(1, MAX_RETRIES + 1):
        driver = None
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1280,900")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            if os.path.exists(CHROME_BINARY):
                options.binary_location = CHROME_BINARY

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(int(REQUEST_TIMEOUT))
            driver.get(request_url)
            time.sleep(1)
            response_text = driver.execute_script(
                "return document.body ? document.body.innerText : document.documentElement.innerText;"
            )
            if not response_text or "ERR_" in response_text or "无法访问此网站" in response_text:
                raise RuntimeError("浏览器未返回有效接口内容")
            break
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"第 {page_number} 页请求失败: {exc}") from exc
            time.sleep(attempt)
        finally:
            if driver is not None:
                driver.quit()

    payload = parse_payload_text(response_text)
    return extract_sectors(payload)


def fetch_all_sectors() -> List[Dict[str, str]]:
    """Fetch sectors from configured pages and deduplicate by sector_id."""
    sector_map: Dict[str, str] = {}

    with proxy_guard():
        for page_number in PAGE_RANGE:
            sectors = fetch_sector_page(page_number)
            print(f"第 {page_number} 页抓取到 {len(sectors)} 条板块数据")
            for sector in sectors:
                sector_map[sector["sector_id"]] = sector["sector_name"]

    return [
        {"sector_id": sector_id, "sector_name": sector_name}
        for sector_id, sector_name in sector_map.items()
    ]


def load_sectors_from_sources(file_paths: List[str], use_stdin: bool) -> List[Dict[str, str]]:
    """Load sector payloads from files or stdin and merge them."""
    sector_map: Dict[str, str] = {}

    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as file:
            payload = parse_payload_text(file.read())
        sectors = extract_sectors(payload)
        print(f"文件 {file_path} 解析出 {len(sectors)} 条板块数据")
        for sector in sectors:
            sector_map[sector["sector_id"]] = sector["sector_name"]

    if use_stdin:
        payload = parse_payload_text(sys.stdin.read())
        sectors = extract_sectors(payload)
        print(f"标准输入解析出 {len(sectors)} 条板块数据")
        for sector in sectors:
            sector_map[sector["sector_id"]] = sector["sector_name"]

    return [
        {"sector_id": sector_id, "sector_name": sector_name}
        for sector_id, sector_name in sector_map.items()
    ]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="抓取或导入东方财富板块列表并保存到数据库")
    parser.add_argument(
        "--input-file",
        nargs="+",
        default=[],
        help="从本地文件导入原始 JSON/JSONP 响应，支持传入多个文件",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="从标准输入读取原始 JSON/JSONP 响应",
    )
    return parser.parse_args()


def save_sectors(sectors: List[Dict[str, str]]) -> int:
    """Create table if needed, upsert sectors, and return total row count."""
    config = get_mysql_config()

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute(CREATE_TABLE_SQL)
        cursor.executemany(
            INSERT_SQL,
            [(item["sector_id"], item["sector_name"]) for item in sectors],
        )
        conn.commit()

        cursor.execute(COUNT_SQL)
        total_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return int(total_count)
    except MySQLError as exc:
        raise RuntimeError(f"保存板块数据失败: {exc}") from exc


def main() -> None:
    """Script entry point."""
    load_env()
    args = parse_args()

    if args.input_file or args.stdin:
        sectors = load_sectors_from_sources(args.input_file, args.stdin)
    else:
        sectors = fetch_all_sectors()

    if not sectors:
        raise RuntimeError("没有解析到任何板块数据")

    total_count = save_sectors(sectors)
    print(f"本次处理 {len(sectors)} 条唯一板块数据")
    print(f"数据库当前共保存 {total_count} 条板块记录")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"执行失败: {exc}")
        raise SystemExit(1) from exc
