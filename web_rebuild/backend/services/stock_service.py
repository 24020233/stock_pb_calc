# -*- coding: utf-8 -*-
"""Stock data service using akshare."""

import logging
from typing import Any, Dict, List, Optional

import akshare as ak

logger = logging.getLogger(__name__)


class StockServiceError(Exception):
    """Exception raised for stock service errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def get_stock_boards() -> List[Dict[str, Any]]:
    """Get all stock sector/industry boards from Eastmoney.

    Returns:
        List of board dictionaries with name and code
    """
    try:
        # Get industry boards
        industry_df = ak.stock_board_industry_name_em()

        boards = []
        for _, row in industry_df.iterrows():
            boards.append({
                "name": row.get("板块名称", ""),
                "code": row.get("板块代码", ""),
                "type": "industry",
            })

        # Get concept boards
        concept_df = ak.stock_board_concept_name_em()
        for _, row in concept_df.iterrows():
            boards.append({
                "name": row.get("板块名称", ""),
                "code": row.get("板块代码", ""),
                "type": "concept",
            })

        return boards

    except Exception as e:
        logger.error(f"Failed to get stock boards: {e}")
        raise StockServiceError(f"获取板块列表失败: {e}")


def get_stocks_by_board(board_name: str) -> List[Dict[str, Any]]:
    """Get stocks in a specific board/sector.

    Args:
        board_name: Name of the board/sector (e.g., "人工智能", "新能源汽车")

    Returns:
        List of stock dictionaries with code, name, and basic info
    """
    try:
        # Try to get stocks by board name
        df = ak.stock_board_industry_cons_em(symbol=board_name)

        if df.empty:
            # Try concept boards if industry fails
            df = ak.stock_board_concept_cons_em(symbol=board_name)

        if df.empty:
            logger.warning(f"No stocks found for board: {board_name}")
            return []

        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                "code": row.get("代码", ""),
                "name": row.get("名称", ""),
                "latest_price": row.get("最新价", 0),
                "change_pct": row.get("涨跌幅", 0),
                "volume": row.get("成交量", 0),
                "turnover": row.get("成交额", 0),
            })

        return stocks

    except Exception as e:
        logger.error(f"Failed to get stocks for board {board_name}: {e}")
        # Return empty list instead of raising for resilience
        return []


def get_stock_snapshot(stock_code: str) -> Dict[str, Any]:
    """Get stock real-time snapshot data.

    Args:
        stock_code: Stock code (e.g., "000001", "600000")

    Returns:
        Dictionary with stock snapshot data
    """
    try:
        df = ak.stock_zh_a_spot_em()
        stock_data = df[df["代码"] == stock_code]

        if stock_data.empty:
            logger.warning(f"No data found for stock: {stock_code}")
            return {}

        row = stock_data.iloc[0]

        return {
            "code": row.get("代码", ""),
            "name": row.get("名称", ""),
            "price": row.get("最新价", 0),
            "open": row.get("今开", 0),
            "high": row.get("最高", 0),
            "low": row.get("最低", 0),
            "prev_close": row.get("昨收", 0),
            "volume": row.get("成交量", 0),
            "turnover": row.get("成交额", 0),
            "change_pct": row.get("涨跌幅", 0),
            "change_amount": row.get("涨跌额", 0),
            "turnover_rate": row.get("换手率", 0),
            "pe_ratio": row.get("市盈率-动态", 0),
            "pb_ratio": row.get("市净率", 0),
            "market_cap": row.get("总市值", 0),
            "circulating_cap": row.get("流通市值", 0),
            "high_52w": row.get("52周最高", 0),
            "low_52w": row.get("52周最低", 0),
            "amplitude": row.get("振幅", 0),
        }

    except Exception as e:
        logger.error(f"Failed to get snapshot for stock {stock_code}: {e}")
        raise StockServiceError(f"获取股票快照失败: {e}")


def search_stock(keyword: str) -> List[Dict[str, Any]]:
    """Search stocks by keyword (name or code).

    Args:
        keyword: Search keyword

    Returns:
        List of matching stocks
    """
    try:
        df = ak.stock_zh_a_spot_em()

        # Filter by code or name
        mask = df["代码"].str.contains(keyword, na=False) | df["名称"].str.contains(keyword, na=False)
        filtered = df[mask]

        if filtered.empty:
            return []

        stocks = []
        for _, row in filtered.head(10).iterrows():  # Limit to 10 results
            stocks.append({
                "code": row.get("代码", ""),
                "name": row.get("名称", ""),
                "price": row.get("最新价", 0),
                "change_pct": row.get("涨跌幅", 0),
            })

        return stocks

    except Exception as e:
        logger.error(f"Failed to search stocks: {e}")
        raise StockServiceError(f"搜索股票失败: {e}")


def get_stock_history(stock_code: str, period: str = "daily") -> List[Dict[str, Any]]:
    """Get stock historical data.

    Args:
        stock_code: Stock code
        period: Time period ("daily", "weekly", "monthly")

    Returns:
        List of historical data points
    """
    try:
        # Determine symbol format for akshare
        if stock_code.startswith("6"):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"

        # Get daily data
        df = ak.stock_zh_a_hist(symbol=symbol, adjust="qfq")

        if df.empty:
            return []

        history = []
        for _, row in df.iterrows():
            history.append({
                "date": row.get("日期"),
                "open": row.get("开盘", 0),
                "high": row.get("最高", 0),
                "low": row.get("最低", 0),
                "close": row.get("收盘", 0),
                "volume": row.get("成交量", 0),
                "turnover": row.get("成交额", 0),
                "change_pct": row.get("涨跌幅", 0),
                "turnover_rate": row.get("换手率", 0),
            })

        return history

    except Exception as e:
        logger.error(f"Failed to get history for stock {stock_code}: {e}")
        raise StockServiceError(f"获取股票历史数据失败: {e}")
