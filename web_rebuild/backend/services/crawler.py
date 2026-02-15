# -*- coding: utf-8 -*-
"""WeChat MP article crawler service using Dajiala API."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

# Dajiala API endpoints
DAJIALA_POST_CONDITION_URL = "https://www.dajiala.com/fbmain/monitor/v3/post_condition"
DAJIALA_ARTICLE_HTML_URL = "https://www.dajiala.com/fbmain/monitor/v3/article_html"


class DajialaAPIError(Exception):
    """Exception raised for Dajiala API errors."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API Error {code}: {message}")


async def fetch_article_list_by_name(name: str) -> Dict[str, Any]:
    """
    Fetch article list for a WeChat MP account by name.

    Args:
        name: WeChat MP account name

    Returns:
        API response containing article list

    Raises:
        DajialaAPIError: If API returns an error
        httpx.HTTPError: If HTTP request fails
    """
    settings = get_settings()

    payload = {
        "biz": "",
        "url": "",
        "name": name,
        "key": settings.dajiala_key,
        "verifycode": settings.dajiala_verifycode or "",
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            DAJIALA_POST_CONDITION_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    code = data.get("code")
    if code != 0:
        raise DajialaAPIError(code, data.get("msg", "Unknown error"))

    return data


async def fetch_article_html(url: str) -> Dict[str, Any]:
    """
    Fetch article HTML content by URL.

    Args:
        url: WeChat article URL

    Returns:
        API response containing article HTML and metadata

    Raises:
        DajialaAPIError: If API returns an error
        httpx.HTTPError: If HTTP request fails
    """
    settings = get_settings()

    payload = {
        "url": url,
        "key": settings.dajiala_key,
        "verifycode": settings.dajiala_verifycode or "",
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            DAJIALA_ARTICLE_HTML_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    code = data.get("code")
    if code != 0:
        raise DajialaAPIError(code, data.get("msg", "Unknown error"))

    return data


def parse_article_list(api_response: Dict[str, Any], mp_name_fallback: str = "") -> List[Dict[str, Any]]:
    """
    Parse article list from API response.

    Args:
        api_response: Raw API response
        mp_name_fallback: Fallback MP name if not in response

    Returns:
        List of parsed article records
    """
    mp_nickname = api_response.get("mp_nickname") or mp_name_fallback
    mp_wxid = api_response.get("mp_wxid")
    mp_ghid = api_response.get("mp_ghid")

    articles = api_response.get("data", [])
    records = []

    for item in articles:
        record = {
            "mp_nickname": mp_nickname,
            "mp_wxid": mp_wxid,
            "mp_ghid": mp_ghid,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "post_time": item.get("post_time"),
            "post_time_str": item.get("post_time_str"),
            "position": item.get("position"),
            "cover_url": item.get("cover_url"),
            "original": item.get("original"),
            "digest": item.get("digest"),
        }
        records.append(record)

    return records


def parse_article_detail(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse article detail from API response.

    Args:
        api_response: Raw API response

    Returns:
        Parsed article detail record
    """
    data = api_response.get("data", {})

    return {
        "title": data.get("title", ""),
        "article_url": data.get("article_url", ""),
        "post_time": data.get("post_time"),
        "wxid": data.get("wxid", ""),
        "author": data.get("author", ""),
        "html": data.get("html", ""),
        "mp_head_img": data.get("mp_head_img"),
        "cover_url": data.get("cover_url"),
        "nickname": data.get("nickname"),
        "gh_id": data.get("gh_id"),
        "signature": data.get("signature"),
        "copyright": data.get("copyright"),
        "ip_wording": data.get("ip_wording"),
    }
