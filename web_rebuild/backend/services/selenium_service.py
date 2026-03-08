# -*- coding: utf-8 -*-
"""Selenium service for fetching board stock data from Eastmoney."""

import json
import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional
#from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

# 东财板块成分股接口 URL 模板
EASTMONEY_BOARD_URL = "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&fs=b:{sector_id}+f:!50&fields=f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23&fid=f3&pn=1&pz=50&po=1&dect=1&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=7025305900436274|0|1|0|web"


def create_webdriver() -> webdriver.Chrome:
    """创建并返回配置好的 Chrome WebDriver"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--log-level=3")
    # 禁用图片加载以加快速度
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    #driver = webdriver.Chrome(options=options)
    driver = webdriver.Chrome()
    # 设置页面加载超时
    driver.set_page_load_timeout(30)
    return driver


def _safe_divide(value: Optional[float], divisor: float) -> Optional[float]:
    """安全除法"""
    if value is None:
        return None
    try:
        return float(value) / divisor
    except (TypeError, ValueError):
        return None


def fetch_board_stocks(driver: webdriver.Chrome, sector_id: str, sector_name: str) -> List[Dict[str, Any]]:
    """
    获取单个板块的成分股数据

    Args:
        driver: WebDriver 实例
        sector_id: 板块代码
        sector_name: 板块名称

    Returns:
        成分股列表
    """
    url = EASTMONEY_BOARD_URL.format(sector_id=sector_id)

    try:
        driver.get(url)

        # 等待页面加载完成
        time.sleep(0.5)

        text_content = driver.execute_script("return document.body.innerText;")

        # 调试：打印返回内容的前200个字符
        if not text_content or not text_content.strip():
            logger.warning(f"Empty response for sector: {sector_name} ({sector_id})")
            return []

        # 检查是否是有效 JSON 格式
        text_content = text_content.strip()
        if not text_content.startswith('{'):
            logger.warning(f"Invalid JSON response for sector {sector_name}, starts with: {text_content[:100]}")
            return []

        # 解析 JSON
        data = json.loads(text_content)

        if not data or not data.get("data") or not data["data"].get("diff"):
            logger.warning(f"No stocks found for sector: {sector_name} ({sector_id})")
            return []

        stocks = []
        for item in data["data"]["diff"]:
            stock_code = item.get("f12", "")
            if not stock_code:
                continue

            stocks.append({
                "stock_code": stock_code,
                "stock_name": item.get("f14", ""),
                "latest_price": _safe_divide(item.get("f15"), 100),
                "change_pct": _safe_divide(item.get("f3"), 100),
                "change_amount": _safe_divide(item.get("f4"), 100),
                "high_price": _safe_divide(item.get("f2"), 100),
                "low_price": _safe_divide(item.get("f16"), 100),
                "open_price": _safe_divide(item.get("f17"), 100),
                "prev_close": _safe_divide(item.get("f18"), 100),
                "volume": item.get("f5"),
                "turnover": item.get("f6"),
                "amplitude": _safe_divide(item.get("f7"), 100),
                "turnover_rate": _safe_divide(item.get("f8"), 100),
                "pe_ratio": _safe_divide(item.get("f9"), 100),
                "pb_ratio": _safe_divide(item.get("f23"), 100),
            })

        logger.info(f"Successfully fetched {len(stocks)} stocks for sector: {sector_name}")
        return stocks

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON for sector {sector_name}: {e}")
        # 尝试获取页面源码以调试
        try:
            page_source = driver.page_source[:500]
            logger.debug(f"Page source preview: {page_source}")
        except:
            pass
        return []
    except Exception as e:
        logger.error(f"Failed to fetch stocks for sector {sector_name}: {e}")
        return []


def fetch_all_board_stocks(
    sector_list: List[Dict[str, str]],
    top_n: int = 10
) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取所有板块的成分股数据

    注意：此函数是同步函数，不能直接调用异步代码。
    进度更新需要在调用方处理。

    Args:
        sector_list: 板块列表，每项包含 sector_id 和 sector_name
        top_n: 每个板块取涨跌幅前 N 名

    Returns:
        Dict[sector_name, List[stock_data]]
    """
    driver = None
    results = {}
    today = date.today()
    total = len(sector_list)

    try:
        driver = create_webdriver()
        logger.info(f"WebDriver created, processing {total} sectors...")

        for idx, sector in enumerate(sector_list):
            sector_id = sector.get("sector_id")
            sector_name = sector.get("sector_name")

            if not sector_id or not sector_name:
                logger.warning(f"Skipping invalid sector: {sector}")
                continue

            logger.info(f"[{idx + 1}/{total}] Fetching stocks for sector: {sector_name}")

            stocks = fetch_board_stocks(driver, sector_id, sector_name)

            if stocks:
                # 按涨跌幅降序排序
                stocks_sorted = sorted(
                    stocks,
                    key=lambda x: x.get("change_pct") or 0,
                    reverse=True
                )
                # 取前 N 名
                top_stocks = stocks_sorted[:top_n]

                # 添加板块信息和日期
                for stock in top_stocks:
                    stock["sector_id"] = sector_id
                    stock["sector_name"] = sector_name
                    stock["data_date"] = today

                results[sector_name] = top_stocks

            # 每次轮询后等待10秒，避免请求过于频繁
            if idx < total - 1:
                logger.info(f"Waiting 10 seconds before next request...")
                time.sleep(10)

    except Exception as e:
        logger.exception(f"Error fetching board stocks: {e}")
    finally:
        # 确保关闭 webdriver
        if driver:
            try:
                driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")

    return results