#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import contextlib
import concurrent.futures
import hmac
import json
import os
import sys
import time
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

import requests

try:
    import akshare as ak
except Exception:  # pragma: no cover
    ak = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv

    _dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=_dotenv_path)
except Exception:  # pragma: no cover
    pass

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment]

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except Exception:  # pragma: no cover
    mysql = None  # type: ignore[assignment]

    class MySQLError(Exception):
        pass


API_URL = "https://www.dajiala.com/fbmain/monitor/v3/post_condition"


if TYPE_CHECKING:  # pragma: no cover
    from mysql.connector.connection import MySQLConnection
else:  # pragma: no cover
    MySQLConnection = Any  # type: ignore[misc,assignment]


def mysql_config_from_env() -> Dict[str, Any]:
    """MySQL config from environment.

    Keep keys compatible with mysql-connector-python.
    """
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "test"),
        "autocommit": True,
        # Remote MySQL TLS handshakes can occasionally take >5s; keep a safer default.
        "connection_timeout": int(os.getenv("MYSQL_TIMEOUT", "20")),
        "read_timeout": int(os.getenv("MYSQL_READ_TIMEOUT", os.getenv("MYSQL_TIMEOUT", "20"))),
        "write_timeout": int(os.getenv("MYSQL_WRITE_TIMEOUT", os.getenv("MYSQL_TIMEOUT", "20"))),
    }


def get_default_mysql_config() -> Dict[str, Any]:
    """Default MySQL config (no secrets hardcoded).

    Password must be provided via env `MYSQL_PASSWORD` or CLI `--mysql-password`.
    """
    return {
        **mysql_config_from_env(),
    }


def upsert_account(
    conn: MySQLConnection,
    mp_nickname: str,
    mp_wxid: Optional[str],
    mp_ghid: Optional[str],
) -> int:
    """Return wx_mp_account.id."""
    cur = conn.cursor()
    try:
        if mp_ghid:
            cur.execute("SELECT id FROM wx_mp_account WHERE mp_ghid=%s LIMIT 1", (mp_ghid,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE wx_mp_account SET mp_nickname=%s, mp_wxid=%s WHERE id=%s",
                    (mp_nickname, mp_wxid, int(row[0])),
                )
                return int(row[0])

        if mp_wxid:
            cur.execute("SELECT id FROM wx_mp_account WHERE mp_wxid=%s LIMIT 1", (mp_wxid,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE wx_mp_account SET mp_nickname=%s, mp_ghid=%s WHERE id=%s",
                    (mp_nickname, mp_ghid, int(row[0])),
                )
                return int(row[0])

        # Fallback: best-effort match by nickname (not unique).
        cur.execute("SELECT id FROM wx_mp_account WHERE mp_nickname=%s ORDER BY id ASC LIMIT 1", (mp_nickname,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE wx_mp_account SET mp_wxid=%s, mp_ghid=%s WHERE id=%s",
                (mp_wxid, mp_ghid, int(row[0])),
            )
            return int(row[0])

        cur.execute(
            "INSERT INTO wx_mp_account (mp_nickname, mp_wxid, mp_ghid) VALUES (%s,%s,%s)",
            (mp_nickname, mp_wxid, mp_ghid),
        )
        return int(cur.lastrowid)
    finally:
        cur.close()


def insert_fetch_log(
    conn: MySQLConnection,
    account_id: Optional[int],
    query_name: str,
    api_url: str,
    request_json: Dict[str, Any],
    response_json: Dict[str, Any],
) -> int:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO wx_article_list_fetch (
              account_id, query_name, api_url,
              request_json, response_code, response_msg,
              mp_nickname, mp_wxid, mp_ghid,
              item_count, response_json
            ) VALUES (
              %s,%s,%s,
              %s,%s,%s,
              %s,%s,%s,
              %s,%s
            )
            """,
            (
                account_id,
                query_name,
                api_url,
                json.dumps(request_json, ensure_ascii=False),
                response_json.get("code"),
                response_json.get("msg"),
                response_json.get("mp_nickname"),
                response_json.get("mp_wxid"),
                response_json.get("mp_ghid"),
                len(response_json.get("data") or []),
                json.dumps(response_json, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)
    finally:
        cur.close()


def upsert_seed(
    conn: MySQLConnection,
    account_id: int,
    fetch_id: Optional[int],
    record: Dict[str, Any],
) -> None:
    cur = conn.cursor()
    try:
        types_val = record.get("types")
        types_json = json.dumps(types_val, ensure_ascii=False) if types_val is not None else None

        cur.execute(
            """
            INSERT INTO wx_article_seed (
              account_id, fetch_id,
              mp_nickname, mp_wxid, mp_ghid,
              title, digest, url,
              position, post_time, post_time_str,
              cover_url,
              original, item_show_type, types,
              is_deleted, msg_status, msg_fail_reason,
              first_seen_at, last_seen_at
            ) VALUES (
              %s,%s,
              %s,%s,%s,
              %s,%s,%s,
              %s,%s,%s,
              %s,
              %s,%s,%s,
              %s,%s,%s,
              NOW(), NOW()
            ) AS new
            ON DUPLICATE KEY UPDATE
              fetch_id = new.fetch_id,
              mp_nickname = new.mp_nickname,
              mp_wxid = new.mp_wxid,
              mp_ghid = new.mp_ghid,
              title = new.title,
              digest = new.digest,
              position = new.position,
              post_time = new.post_time,
              post_time_str = new.post_time_str,
              cover_url = new.cover_url,
              original = new.original,
              item_show_type = new.item_show_type,
              types = new.types,
              is_deleted = new.is_deleted,
              msg_status = new.msg_status,
              msg_fail_reason = new.msg_fail_reason,
              last_seen_at = NOW();
            """,
            (
                account_id,
                fetch_id,
                record.get("mp_nickname"),
                record.get("mp_wxid"),
                record.get("mp_ghid"),
                record.get("title"),
                record.get("digest"),
                record.get("url"),
                record.get("position"),
                record.get("post_time"),
                record.get("post_time_str"),
                record.get("cover_url"),
                record.get("original"),
                record.get("item_show_type"),
                types_json,
                record.get("is_deleted"),
                record.get("msg_status"),
                record.get("msg_fail_reason"),
            ),
        )
    finally:
        cur.close()


def store_list_to_mysql(
    api_resp: Dict[str, Any],
    records: List[Dict[str, Any]],
    *,
    query_name: str,
    api_url: str,
    mysql_cfg: Dict[str, Any],
    verifycode: str,
) -> Dict[str, Any]:
    mp_name = api_resp.get("mp_nickname") or query_name
    mp_wxid = api_resp.get("mp_wxid")
    mp_ghid = api_resp.get("mp_ghid")

    # Do not persist API key.
    request_json = {"biz": "", "url": "", "name": query_name, "verifycode": verifycode or ""}

    conn = mysql.connector.connect(**mysql_cfg)
    try:
        conn.autocommit = False

        account_id = upsert_account(conn, mp_nickname=mp_name, mp_wxid=mp_wxid, mp_ghid=mp_ghid)
        fetch_id = insert_fetch_log(
            conn,
            account_id=account_id,
            query_name=query_name,
            api_url=api_url,
            request_json=request_json,
            response_json=api_resp,
        )

        for r in records:
            upsert_seed(conn, account_id=account_id, fetch_id=fetch_id, record=r)

        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE wx_mp_account SET last_list_fetch_at=NOW() WHERE id=%s",
                (account_id,),
            )
        finally:
            cur.close()

        conn.commit()
        return {
            "account_id": account_id,
            "fetch_id": fetch_id,
            "fetched": len(records),
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _parse_paging_from_flask_request(req) -> Tuple[int, int]:
    try:
        limit = int(req.args.get("limit", 50))
    except Exception:
        limit = 50
    try:
        offset = int(req.args.get("offset", 0))
    except Exception:
        offset = 0
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    return limit, offset


def create_app(mysql_cfg: Dict[str, Any]):
    """Flask CRUD app.

    This keeps the API logic co-located with the crawler so there's a single entrypoint.
    """

    try:
        from flask import Flask, jsonify, request
        from flask_cors import CORS
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Missing dependencies for API server. Install: python3 -m pip install flask flask-cors"
        ) from e

    app = Flask(__name__)

    def _parse_cors_origins() -> List[str] | str:
        """Return origins list or '*' based on env.

        - CORS_ALLOW_ORIGINS="*" -> allow all
        - CORS_ALLOW_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
        """

        raw = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
        if raw == "*":
            return "*"
        if raw:
            return [o.strip() for o in raw.split(",") if o.strip()]
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://www.chatgptanswer.cn",
            "https://www.chatgptanswer.cn",
        ]

    cors_origins = _parse_cors_origins()
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        max_age=600,
    )

    def ok(data: Any = None, **extra):
        out = {"success": True, "data": data}
        out.update(extra)
        return jsonify(out)

    def err(message: str, status: int = 400, **extra):
        out = {"success": False, "error": message}
        out.update(extra)
        return jsonify(out), status

    def get_db():
        if mysql is None:
            raise RuntimeError(
                "Missing dependency: mysql-connector-python (install: python3 -m pip install mysql-connector-python)"
            )
        if not mysql_cfg.get("password"):
            raise RuntimeError("Missing MySQL password (set MYSQL_PASSWORD or pass --mysql-password)")
        return mysql.connector.connect(**mysql_cfg)

    @app.post("/api/login")
    def login_api():
        """Validate UI login password.

        This is intentionally minimal auth (single shared password).
        Reads env `PASSWORD`.
        """

        expected = (os.getenv("PASSWORD") or "").strip()
        if not expected:
            return err("missing-env:PASSWORD", status=500)

        body = request.get_json(silent=True) or {}
        password = str(body.get("password") or "")
        if not password:
            return err("password required", status=400)

        if not hmac.compare_digest(password, expected):
            return err("invalid password", status=401)

        return ok({"ok": True})

    def _fmt_dt(v: Any) -> Any:
        # mysql-connector returns datetime objects; Flask would serialize them to RFC1123.
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        return v

    @app.get("/api/health")
    def health():
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            row = cur.fetchone()
            cur.close()
            conn.close()
            return ok({"db": True, "select": row[0] if row else None})
        except Exception as e:
            return err(f"health-failed:{e}", status=500)

    # ----------------------------- wx_sector_daily ----------------------------

    def _today_ymd() -> str:
        # Server-local date (sufficient for this admin tool).
        return datetime.now().strftime("%Y-%m-%d")

    def _parse_ymd(v: str) -> Optional[str]:
        s = (v or "").strip()
        if not s:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        return None

    def ensure_sector_tables(conn: MySQLConnection) -> None:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS wx_sector_daily (
                  day DATE NOT NULL,
                  sector VARCHAR(128) NOT NULL,
                  mention_count INT NOT NULL DEFAULT 0,
                  articles JSON NULL,
                  raw_json JSON NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (day, sector),
                  KEY idx_day (day)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        finally:
            cur.close()

    def ensure_pick_tables(conn: MySQLConnection) -> None:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS wx_sector_stock_pick (
                  day DATE NOT NULL,
                  sector VARCHAR(128) NOT NULL,
                  stock_code VARCHAR(16) NOT NULL,
                  stock_name VARCHAR(64) NOT NULL,
                  latest_price DECIMAL(18, 4) NULL,
                  pct_change DECIMAL(10, 4) NULL,
                  open_price DECIMAL(18, 4) NULL,
                  prev_close DECIMAL(18, 4) NULL,
                  turnover_rate DECIMAL(10, 4) NULL,
                  pe_dynamic DECIMAL(18, 4) NULL,
                  pb DECIMAL(18, 4) NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (day, sector, stock_code),
                  KEY idx_day (day),
                  KEY idx_day_sector (day, sector),
                  KEY idx_stock_code (stock_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        finally:
            cur.close()

    def _to_float(v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s or s in ("-", "--", "None", "nan"):
            return None
        s = s.replace("%", "")
        try:
            return float(s)
        except Exception:
            return None

    def list_today_seeds(conn: MySQLConnection, ymd: str) -> List[Dict[str, Any]]:
        # Best-effort date filter: `post_time_str` usually like 'YYYY-MM-DD ...'
        # Also filter non-deleted.
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                """
                SELECT id, account_id, title, digest, url, post_time_str
                FROM wx_article_seed
                WHERE is_deleted = 0
                  AND post_time_str LIKE %s
                ORDER BY post_time DESC, id DESC
                """,
                (f"{ymd}%",),
            )
            return list(cur.fetchall() or [])
        finally:
            cur.close()

    def fetch_article_text(url: str, timeout_s: float = 12.0) -> str:
        # WeChat articles typically render content in #js_content.
        # This is best-effort; if blocked, we fall back to title/digest only.
        if not url:
            return ""
        if BeautifulSoup is None:
            raise RuntimeError("missing-dependency:beautifulsoup4")

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=timeout_s)
        resp.raise_for_status()

        html = resp.text or ""
        soup = BeautifulSoup(html, "lxml")

        # Primary: WeChat
        node = soup.select_one("#js_content")
        if node:
            text = node.get_text("\n", strip=True)
        else:
            # Fallback: main/article
            node = soup.select_one("article") or soup.select_one("main")
            text = node.get_text("\n", strip=True) if node else soup.get_text("\n", strip=True)

        # Normalize whitespace and cap size
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def deepseek_extract_sectors(articles: List[Dict[str, Any]], candidate_sectors: Optional[List[str]] = None) -> Dict[str, Any]:
        api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("missing-env:DEEPSEEK_API_KEY")

        base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
        model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()

        # Build compact input: title + url + extracted text snippet.
        max_chars = int(os.getenv("SECTOR_ARTICLE_MAX_CHARS", "2000"))
        parts: List[str] = []
        for i, a in enumerate(articles, start=1):
            title = (a.get("title") or "").strip()
            url = (a.get("url") or "").strip()
            body = (a.get("content_text") or "").strip()
            if max_chars > 0 and len(body) > max_chars:
                body = body[:max_chars] + "\n..."
            parts.append(f"[文章{i}]\n标题: {title}\n链接: {url}\n正文: {body}\n")

        joined = "\n---\n".join(parts)

        cand = [str(x).strip() for x in (candidate_sectors or []) if str(x).strip()]
        # Keep prompt size predictable.
        cand = sorted(set(cand))
        cand_cap = int(os.getenv("SECTOR_CANDIDATE_MAX", "300"))
        if cand_cap > 0:
            cand = cand[:cand_cap]

        candidate_block = ""
        if cand:
            lines = [f"{i+1}. {name}" for i, name in enumerate(cand)]
            candidate_block = (
                "\n候选行业板块清单（只能从此清单中选择，名称必须完全一致；无法匹配则忽略，不要自造板块名）：\n"
                + "\n".join(lines)
                + "\n"
            )

        system = (
            "你是金融资讯分析助手。任务：从给定文章内容中抽取‘股票板块/行业/概念’名称。\n"
            "要求：\n"
            "1) 只输出 JSON（不要 markdown）。\n"
            "2) 结果结构：{\"sectors\":[{\"name\":string,\"articleIndexes\":[int,...]}...]}\n"
            "3) 如果提供了‘候选行业板块清单’，name 必须严格从清单里选，且必须完全一致；同义词/别名请归并到最贴近的候选板块。\n"
            "4) 如果没有清单，则 name 使用中文常见叫法（如：‘半导体’‘AI算力’‘军工’‘新能源车’），去重并合并同义词。\n"
            "5) articleIndexes 为提到该板块的文章编号（从 1 开始）。\n"
        )
        user = f"下面是文章列表，请抽取板块：\n{candidate_block}\n{joined}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }

        url = f"{base_url}/chat/completions"
        r = requests.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        content = (((data.get("choices") or [None])[0] or {}).get("message") or {}).get("content")
        if not content:
            raise RuntimeError("deepseek-empty-response")

        try:
            return json.loads(content)
        except Exception as e:
            raise RuntimeError(f"deepseek-invalid-json:{e}")

    @app.get("/api/sectors")
    def list_sectors_api():
        # Query param: date=YYYY-MM-DD (default today)
        ymd = _parse_ymd(request.args.get("date") or "") or _today_ymd()
        try:
            conn = get_db()
        except Exception as e:
            return err(f"db-connect-error:{e}", status=500)
        try:
            ensure_sector_tables(conn)
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT day, sector, mention_count, articles, updated_at FROM wx_sector_daily WHERE day=%s ORDER BY mention_count DESC, sector ASC",
                (ymd,),
            )
            rows = list(cur.fetchall() or [])
            cur.close()
            for r in rows:
                for k in ("articles",):
                    v = r.get(k)
                    if isinstance(v, str) and v:
                        try:
                            r[k] = json.loads(v)
                        except Exception:
                            pass
            return ok({"date": ymd, "rows": rows})
        finally:
            conn.close()

    @app.post("/api/sectors/generate")
    def generate_sectors_api():
        # Optional JSON body:
        # {"date": "YYYY-MM-DD", "force": 0|1, "maxArticles": int, "fetchConcurrency": int}
        body = request.get_json(silent=True) or {}
        ymd = _parse_ymd(body.get("date") or "") or _today_ymd()
        force = bool(int(body.get("force") or 0))
        try:
            max_articles = int(body.get("maxArticles") or os.getenv("SECTOR_MAX_ARTICLES", "30"))
        except Exception:
            max_articles = 30
        max_articles = max(1, min(max_articles, 200))
        try:
            fetch_conc = int(body.get("fetchConcurrency") or os.getenv("SECTOR_FETCH_CONCURRENCY", "8"))
        except Exception:
            fetch_conc = 8
        fetch_conc = max(1, min(fetch_conc, 32))

        try:
            conn = get_db()
        except Exception as e:
            return err(f"db-connect-error:{e}", status=500)
        try:
            ensure_sector_tables(conn)

            # Fast path: if already generated and not forced, return stored rows.
            if not force:
                industry_candidates = None
                try:
                    industry_candidates = len(_get_industry_list() or [])
                except Exception:
                    industry_candidates = None
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT day, sector, mention_count, articles, updated_at FROM wx_sector_daily WHERE day=%s ORDER BY mention_count DESC, sector ASC",
                    (ymd,),
                )
                existing = list(cur.fetchall() or [])
                cur.close()
                if existing:
                    for r in existing:
                        v = r.get("articles")
                        if isinstance(v, str) and v:
                            try:
                                r["articles"] = json.loads(v)
                            except Exception:
                                pass
                    return ok({"date": ymd, "generated": 0, "cached": True, "rows": existing, "industry_candidates": industry_candidates})

            seeds = list_today_seeds(conn, ymd)
        finally:
            conn.close()

        if not seeds:
            return ok({"date": ymd, "generated": 0, "rows": []})

        # Limit number of articles to control latency and LLM token usage.
        seeds = list(seeds[:max_articles])

        # Fetch article texts (best-effort) in parallel. Keep going even if some fail.
        failures = 0
        url_to_text: Dict[str, str] = {}

        def _fetch_one(u: str) -> Tuple[str, str, Optional[str]]:
            if not u:
                return (u, "", None)
            try:
                txt = fetch_article_text(u)
                return (u, txt, None)
            except Exception as e:
                return (u, "", str(e))

        unique_urls = sorted({(s.get("url") or "").strip() for s in seeds if (s.get("url") or "").strip()})
        if unique_urls:
            with concurrent.futures.ThreadPoolExecutor(max_workers=fetch_conc) as ex:
                futs = [ex.submit(_fetch_one, u) for u in unique_urls]
                for fut in concurrent.futures.as_completed(futs):
                    u, txt, err_s = fut.result()
                    if err_s:
                        failures += 1
                    url_to_text[u] = txt

        articles: List[Dict[str, Any]] = []
        for s in seeds:
            url = (s.get("url") or "").strip()
            content_text = url_to_text.get(url, "")
            articles.append(
                {
                    "id": int(s.get("id")),
                    "title": s.get("title") or "",
                    "url": url,
                    "digest": s.get("digest") or "",
                    "content_text": content_text or (s.get("digest") or ""),
                }
            )

        # Fetch industry board list first, then constrain DeepSeek to select from it.
        industry_names: List[str] = []
        try:
            industry_names = [it.get("name") or "" for it in (_get_industry_list() or [])]
            industry_names = [x.strip() for x in industry_names if x and x.strip()]
        except Exception:
            industry_names = []

        try:
            llm_json = deepseek_extract_sectors(articles, candidate_sectors=industry_names)
        except Exception as e:
            return err(f"deepseek-failed:{e}", status=502)

        sectors = (llm_json or {}).get("sectors") or []
        if not isinstance(sectors, list):
            return err("deepseek-bad-format:sectors", status=502)

        # Build rows: mention_count = number of distinct articles referencing the sector.
        out_rows: List[Dict[str, Any]] = []
        for item in sectors:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            idxs = item.get("articleIndexes") or []
            if not isinstance(idxs, list):
                idxs = []
            # Convert 1-based indexes -> article objects
            used: List[Dict[str, Any]] = []
            seen_ids: set[int] = set()
            for i in idxs:
                try:
                    ii = int(i)
                except Exception:
                    continue
                if ii < 1 or ii > len(articles):
                    continue
                a = articles[ii - 1]
                aid = int(a.get("id"))
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)
                used.append({"id": aid, "title": a.get("title") or "", "url": a.get("url") or ""})
            out_rows.append({
                "day": ymd,
                "sector": name,
                "mention_count": len(used) if used else 0,
                "articles": used,
            })

        # Persist (replace day set).
        try:
            conn = get_db()
        except Exception as e:
            return err(f"db-connect-error:{e}", status=500)
        try:
            ensure_sector_tables(conn)
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute("DELETE FROM wx_sector_daily WHERE day=%s", (ymd,))
            ins = "INSERT INTO wx_sector_daily (day, sector, mention_count, articles, raw_json) VALUES (%s,%s,%s,%s,%s)"
            for r0 in out_rows:
                cur.execute(
                    ins,
                    (
                        ymd,
                        r0["sector"],
                        int(r0["mention_count"]),
                        json.dumps(r0.get("articles") or [], ensure_ascii=False),
                        json.dumps(llm_json, ensure_ascii=False),
                    ),
                )
            conn.commit()
            cur.close()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

        return ok({"date": ymd, "generated": len(out_rows), "fetch_failures": failures, "rows": out_rows, "cached": False, "max_articles": max_articles, "industry_candidates": len(industry_names)})

    # -------------------------- wx_sector_stock_pick --------------------------

    def _env_bool(name: str, default: bool = False) -> bool:
        v = (os.getenv(name) or "").strip().lower()
        if not v:
            return default
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off"):
            return False
        return default

    @contextlib.contextmanager
    def _akshare_no_proxy():
        """Disable HTTP(S) proxy env vars for AkShare/EastMoney calls.

        AkShare relies on requests, which honors proxy env vars by default.
        If the environment has a broken proxy configured, requests will raise ProxyError.
        """
        # Default: respect user's proxy settings (many networks require it).
        # Set AKSHARE_DISABLE_PROXY=1 to force direct connections.
        if os.getenv("AKSHARE_DISABLE_PROXY", "0") != "1":
            yield
            return

        proxy_keys = [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ]
        prev = {k: os.environ.get(k) for k in proxy_keys}
        prev_no_proxy = os.environ.get("NO_PROXY")
        prev_no_proxy_lc = os.environ.get("no_proxy")

        extra_hosts = [
            "eastmoney.com",
            "push2.eastmoney.com",
            "79.push2.eastmoney.com",
            "push2.eastmoney.com.cn",
            "localhost",
            "127.0.0.1",
        ]

        def merge_no_proxy(existing: Optional[str]) -> str:
            parts = [p.strip() for p in (existing or "").split(",") if p.strip()]
            for host in extra_hosts:
                if host not in parts:
                    parts.append(host)
            return ",".join(parts)

        try:
            for k in proxy_keys:
                os.environ.pop(k, None)
            os.environ["NO_PROXY"] = merge_no_proxy(prev_no_proxy)
            os.environ["no_proxy"] = merge_no_proxy(prev_no_proxy_lc)
            yield
        finally:
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            if prev_no_proxy is None:
                os.environ.pop("NO_PROXY", None)
            else:
                os.environ["NO_PROXY"] = prev_no_proxy
            if prev_no_proxy_lc is None:
                os.environ.pop("no_proxy", None)
            else:
                os.environ["no_proxy"] = prev_no_proxy_lc

    def _get_concept_name_df() -> Any:
        """Get EastMoney concept board name list via AkShare.

        Returns a pandas.DataFrame.
        """
        if ak is None:
            raise RuntimeError("missing-dependency:akshare")
        # NOTE: This call can be slow; caller should cache if needed.
        with _akshare_no_proxy():
            return ak.stock_board_concept_name_em()

    def _em_clist_get(fs: str, fields: str, pn: int = 1, pz: int = 200, fid: str = "f12") -> Dict[str, Any]:
        # EastMoney clist: push2 host may redirect and sometimes yields empty replies.
        # Use the redirect target host directly (observed stable in this environment).
        url = "https://push2delay.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": pn,
            "pz": pz,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": fid,
            "fs": fs,
            "fields": fields,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        }
        def do_request(trust_env: bool) -> Dict[str, Any]:
            sess = requests.Session()
            sess.trust_env = trust_env
            with _akshare_no_proxy():
                resp = sess.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

        prefer_proxy = os.getenv("AKSHARE_DISABLE_PROXY", "0") != "1"
        try:
            return do_request(trust_env=prefer_proxy)
        except Exception as e1:
            # If proxy path fails, retry direct (ignoring env/system proxies) for better resilience.
            if prefer_proxy:
                try:
                    return do_request(trust_env=False)
                except Exception as e2:
                    raise RuntimeError(f"proxy_failed:{e1}; direct_failed:{e2}")
            raise

    def _get_concept_list() -> List[Dict[str, str]]:
        """Return concept boards list as [{'name':..., 'code':...}, ...].

        Prefer AkShare, but fallback to EastMoney HTTP when AkShare network path fails.
        """
        # Try AkShare first (optional).
        # Default off: AkShare can occasionally return different field formats/units,
        # causing the downstream filters (pct/turnover thresholds) to behave inconsistently.
        if ak is not None and _env_bool("PICKS_USE_AKSHARE", default=False):
            try:
                df = _get_concept_name_df()
                # Expect columns: 板块名称, 板块代码
                records = df[["板块名称", "板块代码"]].to_dict("records")  # type: ignore[index]
                out: List[Dict[str, str]] = []
                for r in records or []:
                    name = str(r.get("板块名称") or "").strip()
                    code = str(r.get("板块代码") or "").strip()
                    if name and code:
                        out.append({"name": name, "code": code})
                if out:
                    return out
            except Exception:
                pass

        # Fallback: EastMoney concept board list (m:90 t:3)
        out: List[Dict[str, str]] = []
        pn = 1
        while True:
            j = _em_clist_get(
                fs="m:90+t:3+f:!50",
                fields="f12,f14",
                pn=pn,
                pz=200,
                fid="f12",
            )
            diff = (((j or {}).get("data") or {}).get("diff") or [])
            if not diff:
                break
            for it in diff:
                code = str(it.get("f12") or "").strip()
                name = str(it.get("f14") or "").strip()
                if code and name:
                    out.append({"name": name, "code": code})
            if len(diff) < 200:
                break
            pn += 1
            if pn > 20:
                break
        return out

    _industry_list_cache: Dict[str, Any] = {"ts": 0.0, "items": []}

    def _get_industry_list() -> List[Dict[str, str]]:
        """Return industry boards list as [{'name':..., 'code':...}, ...].

        Data source: EastMoney 行业板块 (沪深京板块-行业板块)
        Equivalent to AkShare: stock_board_industry_name_em
        """
        ttl_s = int(os.getenv("SECTOR_INDUSTRY_CACHE_TTL", "21600"))  # 6h
        now = time.time()
        cached_items = _industry_list_cache.get("items") or []
        cached_ts = float(_industry_list_cache.get("ts") or 0.0)
        if cached_items and ttl_s > 0 and (now - cached_ts) < ttl_s:
            return list(cached_items)

        out: List[Dict[str, str]] = []
        pn = 1
        while True:
            j = _em_clist_get(
                fs="m:90+t:2+f:!50",
                fields="f12,f14",
                pn=pn,
                pz=200,
                fid="f12",
            )
            diff = (((j or {}).get("data") or {}).get("diff") or [])
            if not diff:
                break
            for it in diff:
                code = str(it.get("f12") or "").strip()
                name = str(it.get("f14") or "").strip()
                if code and name:
                    out.append({"name": name, "code": code})
            if len(diff) < 200:
                break
            pn += 1
            if pn > 20:
                break

        if out:
            _industry_list_cache["ts"] = now
            _industry_list_cache["items"] = list(out)
        return out

    def _match_concept_name(sector: str, concept_names: List[str]) -> Optional[str]:
        s = (sector or "").strip()
        if not s:
            return None

        concept_set = set(concept_names)
        if s in concept_set:
            return s

        # Built-in common mapping: article sectors are often broader than EastMoney concept names.
        # Keep the list short and practical; callers can still rely on the fallback heuristics below.
        COMMON_SECTOR_ALIASES: Dict[str, List[str]] = {
            "人工智能": [
                "AI应用",
                "AI算力",
                "AI服务器",
                "AI芯片",
                "AI语料",
                "AI手机",
                "AI PC",
                "ChatGPT概念",
                "AIGC概念",
            ],
            "黄金": [
                "黄金概念",
                "黄金",
            ],
            "光伏": [
                "光伏概念",
                "光伏设备",
                "TOPCon电池",
                "HJT电池",
                "HIT电池",
                "钙钛矿电池",
                "BC电池",
            ],
            "芯片": [
                "芯片",
                "国产芯片",
                "先进封装",
                "存储芯片",
                "MCU芯片",
                "光刻机",
            ],
            "军工": [
                "军工",
                "军民融合",
                "国防军工",
            ],
            "机器人": [
                "机器人概念",
                "人形机器人",
                "工业母机",
            ],
            "算力": [
                "AI算力",
                "算力租赁",
                "数据中心",
            ],
            "新能源车": [
                "新能源汽车",
                "新能源车",
                "锂电池概念",
                "固态电池",
            ],
        }

        preferred = COMMON_SECTOR_ALIASES.get(s)
        if preferred:
            for name in preferred:
                if name in concept_set:
                    return name
            # If no exact preferred match, try contains match using preferred keywords.
            for name in preferred:
                contains = [n for n in concept_names if name and name in n]
                if contains:
                    contains.sort(key=lambda n: (len(n), n))
                    return contains[0]

        # Heuristic: prefer concept names that contain the sector keyword.
        contains = [n for n in concept_names if s in n]
        if contains:
            contains.sort(key=lambda n: (len(n), n))
            return contains[0]
        # Fallback: sector might be longer than concept.
        contained = [n for n in concept_names if n in s]
        if contained:
            contained.sort(key=lambda n: (-len(n), n))
            return contained[0]
        return None

    def _fetch_concept_constituents(concept_name: str) -> List[Dict[str, Any]]:
        if ak is None:
            # We can still use EastMoney HTTP fallback without AkShare.
            pass

        # Try AkShare first (optional). See `PICKS_USE_AKSHARE` note above.
        if ak is not None and _env_bool("PICKS_USE_AKSHARE", default=False):
            try:
                with _akshare_no_proxy():
                    df = ak.stock_board_concept_cons_em(symbol=concept_name)
                try:
                    records = df.to_dict("records")
                except Exception:
                    records = []
                return list(records or [])
            except Exception:
                pass

        # Fallback: need board code by name.
        concept_list = _get_concept_list()
        code_by_name = {r["name"]: r["code"] for r in concept_list if r.get("name") and r.get("code")}
        board_code = code_by_name.get(concept_name)
        if not board_code:
            return []
        return _fetch_board_constituents_by_code(board_code)

    def _fetch_board_constituents_by_code(board_code: str) -> List[Dict[str, Any]]:
        """Fetch constituents by EastMoney board code (BKxxxx).

        Works for both concept boards (t:3) and industry boards (t:2).
        Returns AkShare-like keys so downstream logic stays unchanged.
        """
        code = str(board_code or "").strip()
        if not code:
            return []

        # Some boards can exceed a single page; paginate to keep results stable.
        try:
            page_size = int(os.getenv("PICKS_BOARD_PAGE_SIZE", "200"))
        except Exception:
            page_size = 200
        page_size = max(50, min(page_size, 500))
        try:
            max_pages = int(os.getenv("PICKS_BOARD_MAX_PAGES", "10"))
        except Exception:
            max_pages = 10
        max_pages = max(1, min(max_pages, 50))

        out: List[Dict[str, Any]] = []
        seen_codes: set[str] = set()
        for pn in range(1, max_pages + 1):
            j = _em_clist_get(
                fs=f"b:{code}+f:!50",
                fields="f12,f14,f2,f3,f17,f18,f8,f9,f23",
                pn=pn,
                pz=page_size,
                fid="f3",
            )
            diff = (((j or {}).get("data") or {}).get("diff") or [])
            if not diff:
                break
            for it in diff:
                c0 = str(it.get("f12") or "").strip()
                if not c0 or c0 in seen_codes:
                    continue
                seen_codes.add(c0)
                out.append(
                    {
                        "代码": c0,
                        "名称": it.get("f14"),
                        "最新价": it.get("f2"),
                        "涨跌幅": it.get("f3"),
                        "今开": it.get("f17"),
                        "昨收": it.get("f18"),
                        "换手率": it.get("f8"),
                        "市盈率-动态": it.get("f9"),
                        "市净率": it.get("f23"),
                    }
                )
            if len(diff) < page_size:
                break

        return out

    @app.get("/api/picks")
    def list_picks_api():
        ymd = _parse_ymd(request.args.get("date") or "") or _today_ymd()
        sector = (request.args.get("sector") or "").strip()
        limit, offset = _parse_paging_from_flask_request(request)

        try:
            conn = get_db()
        except Exception as e:
            return err(f"db-connect-error:{e}", status=500)
        try:
            ensure_pick_tables(conn)
            cur = conn.cursor(dictionary=True)
            where = "day=%s"
            params: List[Any] = [ymd]
            if sector:
                where += " AND sector=%s"
                params.append(sector)
            sql = (
                "SELECT day, sector, stock_code, stock_name, latest_price, pct_change, open_price, prev_close, "
                "turnover_rate, pe_dynamic, pb, updated_at "
                "FROM wx_sector_stock_pick WHERE "
                + where
                + " ORDER BY pct_change DESC, turnover_rate DESC LIMIT %s OFFSET %s"
            )
            params.extend([limit, offset])
            cur.execute(sql, tuple(params))
            rows = list(cur.fetchall() or [])
            cur.close()
            return ok({"date": ymd, "rows": rows}, limit=limit, offset=offset)
        finally:
            conn.close()

    @app.post("/api/picks/generate")
    def generate_picks_api():
        body = request.get_json(silent=True) or {}
        ymd = _parse_ymd(body.get("date") or "") or _today_ymd()

        try:
            min_mention = int(body.get("minMention") or 4)
        except Exception:
            min_mention = 4
        try:
            min_change = float(body.get("minChange") or 5)
        except Exception:
            min_change = 5.0
        try:
            min_turnover = float(body.get("minTurnover") or 5)
        except Exception:
            min_turnover = 5.0
        try:
            max_sectors = int(body.get("maxSectors") or 30)
        except Exception:
            max_sectors = 30
        max_sectors = max(1, min(max_sectors, 200))

        # Load sectors (mention_count >= min_mention)
        try:
            conn = get_db()
        except Exception as e:
            return err(f"db-connect-error:{e}", status=500)
        try:
            ensure_sector_tables(conn)
            ensure_pick_tables(conn)
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT sector, mention_count FROM wx_sector_daily WHERE day=%s AND mention_count >= %s ORDER BY mention_count DESC, sector ASC LIMIT %s",
                (ymd, int(min_mention), int(max_sectors)),
            )
            sectors = list(cur.fetchall() or [])
            cur.close()
        finally:
            conn.close()

        if not sectors:
            return ok({"date": ymd, "generated": 0, "rows": [], "sectors": []})

        # Fetch board lists once.
        try:
            concept_list = _get_concept_list()
        except Exception:
            concept_list = []
        concept_names = [r.get("name") for r in concept_list if r.get("name")]
        concept_names = [str(x).strip() for x in concept_names if x and str(x).strip()]
        concept_code_by_name = {r["name"]: r["code"] for r in concept_list if r.get("name") and r.get("code")}

        try:
            industry_list = _get_industry_list()
        except Exception:
            industry_list = []
        industry_names = [r.get("name") for r in industry_list if r.get("name")]
        industry_names = [str(x).strip() for x in industry_names if x and str(x).strip()]
        industry_code_by_name = {r["name"]: r["code"] for r in industry_list if r.get("name") and r.get("code")}

        picks: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        matched_sectors = 0

        for srow in sectors:
            sector_name = str(srow.get("sector") or "").strip()
            if not sector_name:
                continue
            board_kind = "concept"
            matched_name = _match_concept_name(sector_name, concept_names)
            board_code: Optional[str] = None

            if matched_name:
                board_code = concept_code_by_name.get(matched_name)
            else:
                # If sector summaries come from industry-board candidates, prefer industry match.
                if sector_name in industry_code_by_name:
                    board_kind = "industry"
                    matched_name = sector_name
                    board_code = industry_code_by_name.get(sector_name)
                else:
                    # Simple contains heuristics.
                    contains = [n for n in industry_names if sector_name and sector_name in n]
                    contained = [n for n in industry_names if n and n in sector_name]
                    pick = None
                    if contains:
                        contains.sort(key=lambda n: (len(n), n))
                        pick = contains[0]
                    elif contained:
                        contained.sort(key=lambda n: (-len(n), n))
                        pick = contained[0]
                    if pick and pick in industry_code_by_name:
                        board_kind = "industry"
                        matched_name = pick
                        board_code = industry_code_by_name.get(pick)

            if not board_code:
                skipped.append({"sector": sector_name, "reason": "no-board-match"})
                continue

            try:
                if board_kind == "industry":
                    cons = _fetch_board_constituents_by_code(board_code)
                else:
                    # concept (keep AkShare-first behavior inside)
                    cons = _fetch_concept_constituents(matched_name or sector_name)
            except Exception as e:
                skipped.append(
                    {
                        "sector": sector_name,
                        "matched": matched_name,
                        "board_kind": board_kind,
                        "board_code": board_code,
                        "reason": f"fetch-failed:{e}",
                    }
                )
                continue

            matched_sectors += 1
            for r in cons:
                code = str(r.get("代码") or "").strip()
                name = str(r.get("名称") or "").strip()
                if not code or not name:
                    continue

                pct = _to_float(r.get("涨跌幅"))
                turn = _to_float(r.get("换手率"))
                if pct is None or turn is None:
                    continue
                if pct < float(min_change) or turn < float(min_turnover):
                    continue

                picks.append(
                    {
                        "day": ymd,
                        "sector": sector_name,
                        "stock_code": code,
                        "stock_name": name,
                        "latest_price": _to_float(r.get("最新价")),
                        "pct_change": pct,
                        "open_price": _to_float(r.get("今开")),
                        "prev_close": _to_float(r.get("昨收")),
                        "turnover_rate": turn,
                        "pe_dynamic": _to_float(r.get("市盈率-动态")),
                        "pb": _to_float(r.get("市净率")),
                    }
                )

        # Persist (replace day set).
        try:
            conn = get_db()
        except Exception as e:
            return err(f"db-connect-error:{e}", status=500)
        try:
            ensure_pick_tables(conn)
            conn.autocommit = False
            cur = conn.cursor()
            cur.execute("DELETE FROM wx_sector_stock_pick WHERE day=%s", (ymd,))
            ins = (
                "INSERT INTO wx_sector_stock_pick (day, sector, stock_code, stock_name, latest_price, pct_change, open_price, prev_close, "
                "turnover_rate, pe_dynamic, pb) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            for p in picks:
                cur.execute(
                    ins,
                    (
                        ymd,
                        p["sector"],
                        p["stock_code"],
                        p["stock_name"],
                        p.get("latest_price"),
                        p.get("pct_change"),
                        p.get("open_price"),
                        p.get("prev_close"),
                        p.get("turnover_rate"),
                        p.get("pe_dynamic"),
                        p.get("pb"),
                    ),
                )
            conn.commit()
            cur.close()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

        return ok(
            {
                "date": ymd,
                "generated": len(picks),
                "sectors_total": len(sectors),
                "sectors_matched": matched_sectors,
                "skipped": skipped,
                "rows": picks,
                "params": {"minMention": min_mention, "minChange": min_change, "minTurnover": min_turnover, "maxSectors": max_sectors},
                "boards": {"concept": len(concept_names), "industry": len(industry_names)},
            }
        )

    # ----------------------------- wx_mp_account -----------------------------

    @app.get("/api/accounts")
    def list_accounts():
        limit, offset = _parse_paging_from_flask_request(request)
        enabled = request.args.get("enabled")
        name_like = (request.args.get("name_like") or "").strip()

        where = []
        params: List[Any] = []
        if enabled is not None and str(enabled).strip() != "":
            where.append("enabled = %s")
            params.append(int(bool(int(enabled))))
        if name_like:
            where.append("mp_nickname LIKE %s")
            params.append(f"%{name_like}%")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        sql = (
            "SELECT id, mp_nickname, mp_wxid, mp_ghid, enabled, last_list_fetch_at, created_at, updated_at "
            "FROM wx_mp_account" + where_sql + " ORDER BY id DESC LIMIT %s OFFSET %s"
        )
        params.extend([limit, offset])

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            cur.close()
            for r in rows:
                for k in ("last_list_fetch_at", "created_at", "updated_at"):
                    if k in r:
                        r[k] = _fmt_dt(r.get(k))
            return ok(rows, limit=limit, offset=offset)
        finally:
            conn.close()

    @app.get("/api/accounts/<int:account_id>")
    def get_account(account_id: int):
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, mp_nickname, mp_wxid, mp_ghid, enabled, last_list_fetch_at, created_at, updated_at "
                "FROM wx_mp_account WHERE id=%s",
                (account_id,),
            )
            row = cur.fetchone()
            cur.close()
            if not row:
                return err("not-found", status=404)
            for k in ("last_list_fetch_at", "created_at", "updated_at"):
                if k in row:
                    row[k] = _fmt_dt(row.get(k))
            return ok(row)
        finally:
            conn.close()

    @app.post("/api/accounts")
    def create_account_api():
        body = request.get_json(silent=True) or {}
        mp_nickname = (body.get("mp_nickname") or "").strip()
        if not mp_nickname:
            return err("mp_nickname required")
        mp_wxid = (body.get("mp_wxid") or None) or None
        mp_ghid = (body.get("mp_ghid") or None) or None
        enabled = int(bool(body.get("enabled", 1)))

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO wx_mp_account (mp_nickname, mp_wxid, mp_ghid, enabled) VALUES (%s,%s,%s,%s)",
                (mp_nickname, mp_wxid, mp_ghid, enabled),
            )
            new_id = int(cur.lastrowid)
            cur.close()
            return ok({"id": new_id})
        except MySQLError as e:
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

    @app.patch("/api/accounts/<int:account_id>")
    def update_account_api(account_id: int):
        body = request.get_json(silent=True) or {}
        fields = []
        params: List[Any] = []

        for k in ("mp_nickname", "mp_wxid", "mp_ghid"):
            if k in body:
                fields.append(f"{k}=%s")
                params.append(body.get(k))
        if "enabled" in body:
            fields.append("enabled=%s")
            params.append(int(bool(body.get("enabled"))))

        if not fields:
            return err("no fields")

        params.append(account_id)
        sql = "UPDATE wx_mp_account SET " + ",".join(fields) + " WHERE id=%s"
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            affected = cur.rowcount
            cur.close()
            if affected <= 0:
                return err("not-found", status=404)
            return ok({"updated": affected})
        except MySQLError as e:
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

    @app.delete("/api/accounts/<int:account_id>")
    def delete_account_api(account_id: int):
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM wx_mp_account WHERE id=%s", (account_id,))
            affected = cur.rowcount
            cur.close()
            if affected <= 0:
                return err("not-found", status=404)
            return ok({"deleted": affected})
        except MySQLError as e:
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

    @app.post("/api/accounts/<int:account_id>/fetch")
    def fetch_account_articles_api(account_id: int):
        """Fetch latest article list for the account and store into MySQL.

        Uses env `DAJIALA_KEY`. Optional JSON body: {"verifycode": "..."}
        """

        body = request.get_json(silent=True) or {}
        verifycode = (body.get("verifycode") or "").strip()

        # Key can come from env, or be supplied per-request (useful for local dev).
        # Priority: header > json body > query > env
        key = (
            (request.headers.get("X-Dajiala-Key") or "").strip()
            or (body.get("key") or "").strip()
            or (request.args.get("key") or "").strip()
            or (os.getenv("DAJIALA_KEY") or "").strip()
        )
        if not key:
            return err(
                "missing-env:DAJIALA_KEY",
                status=500,
                hint="Set env DAJIALA_KEY, or pass X-Dajiala-Key header / {key} in JSON body.",
            )

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, mp_nickname, enabled FROM wx_mp_account WHERE id=%s", (account_id,))
            row = cur.fetchone()
            cur.close()
            if not row:
                return err("not-found", status=404)

            name = (row.get("mp_nickname") or "").strip()
            if not name:
                return err("mp_nickname missing", status=400)
        finally:
            conn.close()

        try:
            api_resp = post_condition_by_name(name=name, key=key, verifycode=verifycode)
        except Exception as e:
            return err(f"fetch-failed:{e}", status=502)

        code = api_resp.get("code")
        if code != 0:
            return err(
                f"upstream-failed:code={code},msg={api_resp.get('msg')}",
                status=502,
                code=code,
                msg=api_resp.get("msg"),
            )

        records = to_jsonl_records(api_resp, mp_name_fallback=name)
        try:
            store_ret = store_list_to_mysql(
                api_resp,
                records,
                query_name=name,
                api_url=API_URL,
                mysql_cfg=mysql_cfg,
                verifycode=verifycode,
            )
        except Exception as e:
            return err(f"store-failed:{e}", status=500)

        return ok(
            {
                "account_id": account_id,
                "fetched": len(records),
                "stored_account_id": store_ret.get("account_id"),
                "fetch_id": store_ret.get("fetch_id"),
            }
        )

    # ----------------------------- wx_article_seed ----------------------------

    @app.get("/api/seeds")
    def list_seeds_api():
        limit, offset = _parse_paging_from_flask_request(request)
        account_id = request.args.get("account_id")
        q = (request.args.get("q") or "").strip()
        is_deleted = request.args.get("is_deleted")

        where = []
        params: List[Any] = []
        if account_id is not None and str(account_id).strip() != "":
            where.append("account_id=%s")
            params.append(int(account_id))
        if is_deleted is not None and str(is_deleted).strip() != "":
            where.append("is_deleted=%s")
            params.append(int(bool(int(is_deleted))))
        if q:
            where.append("(title LIKE %s OR digest LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        sql = (
            "SELECT id, account_id, fetch_id, title, digest, url, position, post_time, post_time_str, cover_url, "
            "original, item_show_type, types, is_deleted, msg_status, msg_fail_reason, first_seen_at, last_seen_at, created_at, updated_at "
            "FROM wx_article_seed" + where_sql + " ORDER BY post_time DESC, id DESC LIMIT %s OFFSET %s"
        )
        params.extend([limit, offset])

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            cur.close()
            for r in rows:
                tv = r.get("types")
                if isinstance(tv, str) and tv:
                    try:
                        r["types"] = json.loads(tv)
                    except Exception:
                        pass
            return ok(rows, limit=limit, offset=offset)
        finally:
            conn.close()

    @app.get("/api/seeds/<int:seed_id>")
    def get_seed_api(seed_id: int):
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM wx_article_seed WHERE id=%s", (seed_id,))
            row = cur.fetchone()
            cur.close()
            if not row:
                return err("not-found", status=404)
            tv = row.get("types")
            if isinstance(tv, str) and tv:
                try:
                    row["types"] = json.loads(tv)
                except Exception:
                    pass
            return ok(row)
        finally:
            conn.close()

    @app.patch("/api/seeds/<int:seed_id>")
    def update_seed_api(seed_id: int):
        body = request.get_json(silent=True) or {}
        allow = {
            "title",
            "digest",
            "position",
            "post_time",
            "post_time_str",
            "cover_url",
            "original",
            "item_show_type",
            "types",
            "is_deleted",
            "msg_status",
            "msg_fail_reason",
        }
        fields = []
        params: List[Any] = []
        for k, v in body.items():
            if k not in allow:
                continue
            if k == "types" and v is not None:
                v = json.dumps(v, ensure_ascii=False)
            fields.append(f"{k}=%s")
            params.append(v)
        if not fields:
            return err("no fields")
        params.append(seed_id)

        sql = "UPDATE wx_article_seed SET " + ",".join(fields) + ", last_seen_at=NOW() WHERE id=%s"
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            affected = cur.rowcount
            cur.close()
            if affected <= 0:
                return err("not-found", status=404)
            return ok({"updated": affected})
        except MySQLError as e:
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

    @app.delete("/api/seeds/<int:seed_id>")
    def delete_seed_api(seed_id: int):
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM wx_article_seed WHERE id=%s", (seed_id,))
            affected = cur.rowcount
            cur.close()
            if affected <= 0:
                return err("not-found", status=404)
            return ok({"deleted": affected})
        except MySQLError as e:
            return err(f"db-error:{e}", status=500)
        finally:
            conn.close()

    # -------------------------- wx_article_list_fetch -------------------------

    @app.get("/api/fetches")
    def list_fetches_api():
        limit, offset = _parse_paging_from_flask_request(request)
        account_id = request.args.get("account_id")
        query_name = (request.args.get("query_name") or "").strip()

        where = []
        params: List[Any] = []
        if account_id is not None and str(account_id).strip() != "":
            where.append("account_id=%s")
            params.append(int(account_id))
        if query_name:
            where.append("query_name LIKE %s")
            params.append(f"%{query_name}%")
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        sql = (
            "SELECT id, account_id, query_name, api_url, response_code, response_msg, item_count, fetched_at "
            "FROM wx_article_list_fetch" + where_sql + " ORDER BY id DESC LIMIT %s OFFSET %s"
        )
        params.extend([limit, offset])

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            cur.close()
            return ok(rows, limit=limit, offset=offset)
        finally:
            conn.close()

    @app.get("/api/fetches/<int:fetch_id>")
    def get_fetch_api(fetch_id: int):
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM wx_article_list_fetch WHERE id=%s", (fetch_id,))
            row = cur.fetchone()
            cur.close()
            if not row:
                return err("not-found", status=404)
            for k in ("request_json", "response_json"):
                v = row.get(k)
                if isinstance(v, str) and v:
                    try:
                        row[k] = json.loads(v)
                    except Exception:
                        pass
            return ok(row)
        finally:
            conn.close()

    return app


def post_condition_by_name(
    name: str,
    key: str,
    verifycode: str = "",
    timeout_s: float = 30.0,
    retries: int = 3,
    sleep_s: float = 1.0,
) -> Dict[str, Any]:
    payload = {
        "biz": "",
        "url": "",
        "name": name,
        "key": key,
        "verifycode": verifycode or "",
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=timeout_s)
            resp.raise_for_status()
            data = resp.json()

            # 轻度重试：QPS/频繁/网络抖动等
            code = data.get("code", None)
            if code in (-1, 111, 112) and attempt < retries - 1:
                time.sleep(sleep_s * (attempt + 1))
                continue

            return data
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(sleep_s * (attempt + 1))
                continue
            raise last_exc


def to_jsonl_records(api_resp: Dict[str, Any], mp_name_fallback: str) -> List[Dict[str, Any]]:
    articles = api_resp.get("data") or []
    mp_name = api_resp.get("mp_nickname") or mp_name_fallback
    mp_wxid = api_resp.get("mp_wxid")
    mp_ghid = api_resp.get("mp_ghid")

    records: List[Dict[str, Any]] = []
    for a in articles:
        records.append(
            {
                "mp_nickname": mp_name,
                "mp_wxid": mp_wxid,
                "mp_ghid": mp_ghid,
                "title": a.get("title"),
                "digest": a.get("digest"),
                "url": a.get("url"),
                "position": a.get("position"),
                "post_time": a.get("post_time"),
                "post_time_str": a.get("post_time_str"),
                "cover_url": a.get("cover_url"),
                "original": a.get("original"),
                "item_show_type": a.get("item_show_type"),
                "types": a.get("types"),
                "is_deleted": a.get("is_deleted"),
                "msg_status": a.get("msg_status"),
                "msg_fail_reason": a.get("msg_fail_reason"),
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="WeChat MP crawler + CRUD API (dajiala + MySQL)")
    sub = parser.add_subparsers(dest="cmd")

    def add_mysql_args(p: argparse.ArgumentParser) -> None:
        defaults = get_default_mysql_config()
        p.add_argument("--mysql-host", default=defaults["host"], help="MySQL host")
        p.add_argument("--mysql-port", type=int, default=int(defaults["port"]), help="MySQL port")
        p.add_argument("--mysql-user", default=defaults["user"], help="MySQL user")
        p.add_argument(
            "--mysql-password",
            default=defaults["password"],
            help="MySQL password（建议用环境变量 MYSQL_PASSWORD）",
        )
        p.add_argument("--mysql-database", default=defaults["database"], help="MySQL database")
        p.add_argument(
            "--mysql-timeout",
            type=int,
            default=int(defaults["connection_timeout"]),
            help="MySQL 连接超时（秒），避免卡住",
        )

    crawl = sub.add_parser("crawl", help="抓取公众号文章列表")
    crawl.add_argument("--name", required=True, help="公众号名称，如：人民日报")
    crawl.add_argument("--key", default=os.getenv("DAJIALA_KEY", ""), help="接口 key（也可用环境变量 DAJIALA_KEY）")
    crawl.add_argument("--verifycode", default="", help="验证码（如接口要求时再填）")
    crawl.add_argument("--out-json", default="", help="保存完整响应 JSON 到文件路径")
    crawl.add_argument("--out-jsonl", default="", help="保存文章列表 JSONL 到文件路径（每行一篇）")
    crawl.add_argument("--to-mysql", action="store_true", help="将抓取结果写入 MySQL（要求表已建好）")
    add_mysql_args(crawl)

    serve = sub.add_parser("serve", help="启动 CRUD API 服务")
    serve.add_argument("--api-host", default=os.getenv("API_HOST", "0.0.0.0"), help="API host")
    serve.add_argument("--api-port", type=int, default=int(os.getenv("API_PORT", "8001")), help="API port")
    serve.add_argument("--api-debug", default=os.getenv("API_DEBUG", "1"), help="API debug (0/1)")
    add_mysql_args(serve)

    argv = sys.argv[1:]
    if not argv:
        # Default behavior: start API server.
        argv = ["serve"]
    elif argv[0].startswith("-"):
        # Keep standard argparse behavior for flags like --help.
        pass
    elif argv[0] not in ("crawl", "serve"):
        # Convenience: allow `python3 script.py --name xxx ...` style.
        argv = ["crawl", *argv]
    args = parser.parse_args(argv)

    if args.cmd == "serve":
        mysql_cfg = {
            "host": args.mysql_host,
            "port": int(args.mysql_port),
            "user": args.mysql_user,
            "password": args.mysql_password,
            "database": args.mysql_database,
            "connection_timeout": int(args.mysql_timeout),
            "read_timeout": int(args.mysql_timeout),
            "write_timeout": int(args.mysql_timeout),
            "autocommit": True,
        }
        app = create_app(mysql_cfg)
        debug = bool(int(str(args.api_debug)))
        app.run(host=args.api_host, port=int(args.api_port), debug=debug, use_reloader=False)
        return

    if args.cmd != "crawl":
        parser.print_help()
        raise SystemExit(2)

    if not args.key:
        raise SystemExit("缺少 --key 或环境变量 DAJIALA_KEY")

    resp = post_condition_by_name(name=args.name, key=args.key, verifycode=args.verifycode)

    code = resp.get("code")
    if code != 0:
        raise SystemExit(f"接口返回失败：code={code}, msg={resp.get('msg')}, raw={resp}")

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(resp, f, ensure_ascii=False, indent=2)

    records = to_jsonl_records(resp, mp_name_fallback=args.name)

    if args.out_jsonl:
        with open(args.out_jsonl, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if args.to_mysql:
        if mysql is None:
            raise SystemExit("缺少依赖：请先安装 mysql-connector-python（例如：python3 -m pip install mysql-connector-python）")
        if not args.mysql_password:
            raise SystemExit("缺少 MySQL 密码：请设置环境变量 MYSQL_PASSWORD 或传 --mysql-password（不建议写死在代码里）")

        mysql_cfg = {
            "host": args.mysql_host,
            "port": int(args.mysql_port),
            "user": args.mysql_user,
            "password": args.mysql_password,
            "database": args.mysql_database,
            "connection_timeout": int(args.mysql_timeout),
            "read_timeout": int(args.mysql_timeout),
            "write_timeout": int(args.mysql_timeout),
            "autocommit": True,
        }

        try:
            store_list_to_mysql(
                resp,
                records,
                query_name=args.name,
                api_url=API_URL,
                mysql_cfg=mysql_cfg,
                verifycode=args.verifycode,
            )
            print(
                f"mysql ok: db={args.mysql_database}, mp={records[0]['mp_nickname'] if records else args.name}, articles={len(records)}"
            )
        except MySQLError as e:
            raise SystemExit(f"写入 MySQL 失败：{e}")

    print(f"mp={records[0]['mp_nickname'] if records else args.name}, articles={len(records)}")
    for r in records[:5]:
        print(f"- {r.get('post_time_str')} | {r.get('title')} | {r.get('url')}")


if __name__ == "__main__":
    main()