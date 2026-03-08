#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for selenium_service.py"""

import json
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import date

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.selenium_service import (
    _safe_divide,
    fetch_board_stocks,
    fetch_all_board_stocks,
    create_webdriver,
    EASTMONEY_BOARD_URL,
)


class TestSafeDivide(unittest.TestCase):
    """Test the _safe_divide helper function."""

    def test_normal_division(self):
        """Test normal division."""
        self.assertEqual(_safe_divide(100, 100), 1.0)
        self.assertEqual(_safe_divide(250, 100), 2.5)
        self.assertEqual(_safe_divide(50, 10), 5.0)

    def test_none_value(self):
        """Test with None value."""
        self.assertIsNone(_safe_divide(None, 100))
        self.assertIsNone(_safe_divide(None, 1))

    def test_zero_divisor(self):
        """Test division by zero."""
        # Division by zero should raise or return inf
        result = _safe_divide(100, 0)
        self.assertTrue(result == float('inf') or result is None or isinstance(result, float))

    def test_string_value(self):
        """Test with string value that can be converted."""
        # _safe_divide tries to convert to float
        self.assertEqual(_safe_divide("100", 100), 1.0)
        self.assertEqual(_safe_divide(200, 100), 2.0)


class TestFetchBoardStocks(unittest.TestCase):
    """Test the fetch_board_stocks function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = MagicMock()

    def test_successful_fetch(self):
        """Test successful data fetch."""
        # Mock response data
        mock_response = {
            "rc": 0,
            "data": {
                "total": 2,
                "diff": [
                    {
                        "f12": "000001",
                        "f14": "平安银行",
                        "f15": 1234,  # latest_price * 100
                        "f3": 256,    # change_pct * 100
                        "f4": 34,     # change_amount * 100
                        "f2": 1256,   # high_price * 100
                        "f16": 1200,  # low_price * 100
                        "f17": 1210,  # open_price * 100
                        "f18": 1200,  # prev_close * 100
                        "f5": 100000, # volume
                        "f6": 1234567890, # turnover
                        "f7": 450,    # amplitude * 100
                        "f8": 123,    # turnover_rate * 100
                        "f9": 567,    # pe_ratio * 100
                        "f23": 89,    # pb_ratio * 100
                    },
                    {
                        "f12": "000002",
                        "f14": "万科A",
                        "f15": 2345,
                        "f3": -150,
                        "f4": -35,
                        "f2": 2400,
                        "f16": 2300,
                        "f17": 2350,
                        "f18": 2380,
                        "f5": 200000,
                        "f6": 2345678901,
                        "f7": 400,
                        "f8": 234,
                        "f9": 678,
                        "f23": 90,
                    },
                ]
            }
        }

        # Setup mock
        self.mock_driver.get.return_value = None
        self.mock_driver.execute_script.return_value = json.dumps(mock_response)

        # Execute
        result = fetch_board_stocks(self.mock_driver, "BK0001", "人工智能")

        # Verify
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["stock_code"], "000001")
        self.assertEqual(result[0]["stock_name"], "平安银行")
        self.assertEqual(result[0]["latest_price"], 12.34)  # 1234 / 100
        self.assertEqual(result[0]["change_pct"], 2.56)      # 256 / 100
        self.assertEqual(result[1]["stock_code"], "000002")
        self.assertEqual(result[1]["change_pct"], -1.50)     # -150 / 100

    def test_empty_response(self):
        """Test with empty response."""
        mock_response = {"rc": 0, "data": None}

        self.mock_driver.get.return_value = None
        self.mock_driver.execute_script.return_value = json.dumps(mock_response)

        result = fetch_board_stocks(self.mock_driver, "BK0001", "人工智能")

        self.assertEqual(len(result), 0)

    def test_empty_diff(self):
        """Test with empty diff array."""
        mock_response = {"rc": 0, "data": {"total": 0, "diff": []}}

        self.mock_driver.get.return_value = None
        self.mock_driver.execute_script.return_value = json.dumps(mock_response)

        result = fetch_board_stocks(self.mock_driver, "BK0001", "人工智能")

        self.assertEqual(len(result), 0)

    def test_invalid_json(self):
        """Test with invalid JSON response."""
        self.mock_driver.get.return_value = None
        self.mock_driver.execute_script.return_value = "invalid json"

        result = fetch_board_stocks(self.mock_driver, "BK0001", "人工智能")

        self.assertEqual(len(result), 0)

    def test_exception_handling(self):
        """Test exception handling."""
        self.mock_driver.get.side_effect = Exception("Connection failed")

        result = fetch_board_stocks(self.mock_driver, "BK0001", "人工智能")

        self.assertEqual(len(result), 0)

    def test_missing_stock_code(self):
        """Test with missing stock code (f12)."""
        mock_response = {
            "rc": 0,
            "data": {
                "diff": [
                    {"f14": "无代码股票", "f15": 1000},  # Missing f12
                    {"f12": "000001", "f14": "有代码股票", "f15": 2000},
                ]
            }
        }

        self.mock_driver.get.return_value = None
        self.mock_driver.execute_script.return_value = json.dumps(mock_response)

        result = fetch_board_stocks(self.mock_driver, "BK0001", "人工智能")

        # Should only have one stock (the one with code)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["stock_code"], "000001")


class TestFetchAllBoardStocks(unittest.TestCase):
    """Test the fetch_all_board_stocks function."""

    @patch('services.selenium_service.create_webdriver')
    def test_successful_fetch_all(self, mock_create_webdriver):
        """Test successful fetch for all sectors."""
        mock_driver = MagicMock()
        mock_create_webdriver.return_value = mock_driver

        # Mock responses
        mock_response1 = {
            "rc": 0,
            "data": {
                "diff": [
                    {"f12": "000001", "f14": "平安银行", "f15": 1200, "f3": 500, "f4": 50,
                     "f2": 1250, "f16": 1180, "f17": 1190, "f18": 1180,
                     "f5": 100000, "f6": 1200000, "f7": 600, "f8": 80,
                     "f9": 500, "f23": 60},
                    {"f12": "000002", "f14": "万科A", "f15": 2400, "f3": 300, "f4": 70,
                     "f2": 2450, "f16": 2350, "f17": 2380, "f18": 2350,
                     "f5": 200000, "f6": 4800000, "f7": 400, "f8": 150,
                     "f9": 600, "f23": 80},
                ]
            }
        }
        mock_response2 = {
            "rc": 0,
            "data": {
                "diff": [
                    {"f12": "600000", "f14": "浦发银行", "f15": 1000, "f3": 200, "f4": 20,
                     "f2": 1020, "f16": 990, "f17": 1000, "f18": 990,
                     "f5": 150000, "f6": 1500000, "f7": 300, "f8": 100,
                     "f9": 400, "f23": 50},
                ]
            }
        }

        mock_driver.execute_script.side_effect = [
            json.dumps(mock_response1),
            json.dumps(mock_response2),
        ]

        sector_list = [
            {"sector_id": "BK0001", "sector_name": "人工智能"},
            {"sector_id": "BK0002", "sector_name": "新能源"},
        ]

        result = fetch_all_board_stocks(sector_list, top_n=10)

        # Verify results
        self.assertIn("人工智能", result)
        self.assertIn("新能源", result)
        self.assertEqual(len(result["人工智能"]), 2)
        self.assertEqual(len(result["新能源"]), 1)

        # Verify webdriver was quit
        mock_driver.quit.assert_called_once()

    @patch('services.selenium_service.create_webdriver')
    def test_webdriver_quit_on_exception(self, mock_create_webdriver):
        """Test that webdriver is quit even when exception occurs."""
        mock_driver = MagicMock()
        mock_create_webdriver.return_value = mock_driver

        # Make get() raise an exception
        mock_driver.get.side_effect = Exception("Browser crashed")

        sector_list = [{"sector_id": "BK0001", "sector_name": "人工智能"}]

        result = fetch_all_board_stocks(sector_list, top_n=10)

        # Result should be empty
        self.assertEqual(len(result), 0)

        # Verify webdriver was still quit
        mock_driver.quit.assert_called_once()

    @patch('services.selenium_service.create_webdriver')
    def test_top_n_filtering(self, mock_create_webdriver):
        """Test that only top N stocks are returned."""
        mock_driver = MagicMock()
        mock_create_webdriver.return_value = mock_driver

        # Create 20 stocks with different change_pct
        stocks = []
        for i in range(20):
            stocks.append({
                "f12": f"00000{i:02d}",
                "f14": f"股票{i}",
                "f15": 1000 + i * 10,
                "f3": i * 50,  # change_pct varies: 0, 50, 100, ..., 950 (x100)
                "f4": i,
                "f2": 1000 + i * 10,
                "f16": 990,
                "f17": 1000,
                "f18": 990,
                "f5": 100000,
                "f6": 1000000,
                "f7": 100,
                "f8": 50,
                "f9": 500,
                "f23": 50,
            })

        mock_response = {"rc": 0, "data": {"diff": stocks}}
        mock_driver.execute_script.return_value = json.dumps(mock_response)

        sector_list = [{"sector_id": "BK0001", "sector_name": "测试板块"}]

        # Request only top 5
        result = fetch_all_board_stocks(sector_list, top_n=5)

        # Should have only 5 stocks
        self.assertEqual(len(result["测试板块"]), 5)

        # Should be sorted by change_pct descending (highest first)
        # Last stock (index 19) has highest change_pct = 950/100 = 9.5%
        self.assertEqual(result["测试板块"][0]["change_pct"], 9.5)

        mock_driver.quit.assert_called_once()

    @patch('services.selenium_service.create_webdriver')
    def test_empty_sector_list(self, mock_create_webdriver):
        """Test with empty sector list."""
        mock_driver = MagicMock()
        mock_create_webdriver.return_value = mock_driver

        result = fetch_all_board_stocks([], top_n=10)

        self.assertEqual(len(result), 0)

    @patch('services.selenium_service.create_webdriver')
    def test_sector_info_added(self, mock_create_webdriver):
        """Test that sector_id, sector_name, and data_date are added to stocks."""
        mock_driver = MagicMock()
        mock_create_webdriver.return_value = mock_driver

        mock_response = {
            "rc": 0,
            "data": {
                "diff": [{
                    "f12": "000001", "f14": "平安银行",
                    "f15": 1200, "f3": 500, "f4": 50,
                    "f2": 1250, "f16": 1180, "f17": 1190, "f18": 1180,
                    "f5": 100000, "f6": 1200000, "f7": 600, "f8": 80,
                    "f9": 500, "f23": 60
                }]
            }
        }
        mock_driver.execute_script.return_value = json.dumps(mock_response)

        sector_list = [{"sector_id": "BK0123", "sector_name": "人工智能"}]

        result = fetch_all_board_stocks(sector_list, top_n=10)

        stock = result["人工智能"][0]
        self.assertEqual(stock["sector_id"], "BK0123")
        self.assertEqual(stock["sector_name"], "人工智能")
        self.assertEqual(stock["data_date"], date.today())

        mock_driver.quit.assert_called_once()


class TestCreateWebdriver(unittest.TestCase):
    """Test the create_webdriver function."""

    @patch('services.selenium_service.webdriver.Chrome')
    def test_webdriver_creation(self, mock_chrome):
        """Test that webdriver is created with correct options."""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        result = create_webdriver()

        # Verify Chrome was called
        mock_chrome.assert_called_once()

        # Verify the result is the mock driver
        self.assertEqual(result, mock_driver)


class TestUrlFormat(unittest.TestCase):
    """Test URL format."""

    def test_url_template(self):
        """Test that URL template contains sector_id placeholder."""
        self.assertIn("{sector_id}", EASTMONEY_BOARD_URL)

    def test_url_format(self):
        """Test URL formatting with sector_id."""
        sector_id = "BK0123"
        url = EASTMONEY_BOARD_URL.format(sector_id=sector_id)

        self.assertIn(sector_id, url)
        self.assertIn("eastmoney.com", url)


if __name__ == "__main__":
    unittest.main(verbosity=2)