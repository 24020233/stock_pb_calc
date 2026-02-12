import requests
import pandas as pd
import akshare as ak
import os
import contextlib
import time
from typing import List, Dict, Any, Optional

class MarketDataService:
    @staticmethod
    @contextlib.contextmanager
    def _akshare_no_proxy():
        # ... Reuse no proxy logic ...
        old_http = os.environ.get("HTTP_PROXY")
        old_https = os.environ.get("HTTPS_PROXY")
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        try:
            yield
        finally:
            if old_http: os.environ["HTTP_PROXY"] = old_http
            if old_https: os.environ["HTTPS_PROXY"] = old_https

    @staticmethod
    def get_industry_list():
        # Wrapper for AkShare stock_board_industry_name_em
        with MarketDataService._akshare_no_proxy():
            try:
                df = ak.stock_board_industry_name_em()
                # df columns: 序号, 板块名称, 板块代码, ...
                return [{"name": r["板块名称"], "code": r["板块代码"]} for _, r in df.iterrows()]
            except Exception as e:
                print(f"AkShare industry list failed: {e}")
                return []

    @staticmethod
    def get_concept_list():
        # Wrapper for AkShare stock_board_concept_name_em
        with MarketDataService._akshare_no_proxy():
            try:
                df = ak.stock_board_concept_name_em()
                return [{"name": r["板块名称"], "code": r["板块代码"]} for _, r in df.iterrows()]
            except Exception as e:
                print(f"AkShare concept list failed: {e}")
                return []
    
    @staticmethod
    def fetch_constituents(board_name: str, board_code: str = None, is_industry=True):
        # Fetch stocks in a sector
        # Logic adapted from script.py _fetch_board_constituents_by_code or _fetch_concept_constituents
        with MarketDataService._akshare_no_proxy():
            try:
                if is_industry and board_code:
                     df = ak.stock_board_industry_cons_em(symbol=board_code)
                else:
                     df = ak.stock_board_concept_cons_em(symbol=board_name) # AkShare concept sometimes uses name
                
                # Normalize result
                # df columns usually: 序号, 代码, 名称, 最新价, 涨跌幅, ...
                result = []
                for _, r in df.iterrows():
                    result.append({
                        "code": str(r.get("代码", "")),
                        "name": str(r.get("名称", "")),
                        "price": r.get("最新价"),
                        "pct_change": r.get("涨跌幅"),
                        "vol_ratio": r.get("量比"),
                        "turnover": r.get("换手率"),
                        "turnover_rate": r.get("换手率"), # alias
                        "amount": r.get("成交额"),
                        "pe": r.get("市盈率-动态"),
                        "pb": r.get("市净率"),
                        "open": r.get("今开"),
                        "prev_close": r.get("昨收")
                    })
                return result
            except Exception as e:
                 print(f"Fetch constituents failed for {board_name}: {e}")
                 return []
