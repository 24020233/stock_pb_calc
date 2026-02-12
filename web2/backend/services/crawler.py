import requests
import json
import time
import hashlib
from datetime import datetime
from database import get_db
from config import Config
from bs4 import BeautifulSoup

# Reusing constants from script.py
API_URL = "https://www.dajiala.com/fbmain/monitor/v3/post_condition"

class CrawlerService:
    @staticmethod
    def upsert_account(mp_nickname, mp_wxid=None, mp_ghid=None):
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        try:
            # Try find by wxid
            if mp_wxid:
                cur.execute("SELECT id FROM wx_mp_account WHERE mp_wxid=%s", (mp_wxid,))
                row = cur.fetchone()
                if row:
                    return row['id']
            # Try find by ghid
            if mp_ghid:
                cur.execute("SELECT id FROM wx_mp_account WHERE mp_ghid=%s", (mp_ghid,))
                row = cur.fetchone()
                if row:
                    return row['id']
            # Try find by nickname
            cur.execute("SELECT id FROM wx_mp_account WHERE mp_nickname=%s", (mp_nickname,))
            row = cur.fetchone()
            if row:
                # Update wxid/ghid if missing
                updates = []
                params = []
                if mp_wxid:
                    updates.append("mp_wxid=%s")
                    params.append(mp_wxid)
                if mp_ghid:
                    updates.append("mp_ghid=%s")
                    params.append(mp_ghid)
                if updates:
                    params.append(row['id'])
                    cur.execute(f"UPDATE wx_mp_account SET {', '.join(updates)} WHERE id=%s", tuple(params))
                    conn.commit()
                return row['id']

            # Insert new
            cur.execute(
                "INSERT INTO wx_mp_account (mp_nickname, mp_wxid, mp_ghid) VALUES (%s, %s, %s)",
                (mp_nickname, mp_wxid, mp_ghid)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            cur.close()

    @staticmethod
    def fetch_article_text(url: str, timeout_s: float = 12.0) -> str:
        # Simple extraction logic from script.py
        try:
            resp = requests.get(url, timeout=timeout_s)
            resp.encoding = 'utf-8' # or detect
            html = resp.text
            # Very basic extraction - in a real scenario we might use readability or boilerpipe
            # For now, let's just return the whole HTML or a simplified version
            # The original script using BeautifulSoup if available, or just raw.
            # Let's try to strip tags if possible, or just return raw for LLM to handle.
            # ... refactoring the logic from script.py ...
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract() 

            text = soup.get_text()
            # break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    @staticmethod
    def post_condition_by_name(name, key, verifycode="", timeout_s=30.0, retries=3, sleep_s=1.0):
        # Ported from script.py
        url = "https://www.dajiala.com/fbmain/monitor/v3/post_condition"
        headers = {"Content-Type": "application/json"}
        payload = {
            "name": name,
            "key": key,
            "verifycode": verifycode
        }
        
        for i in range(retries):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout_s)
                # Dajiala sometimes returns 502/504
                if resp.status_code >= 500:
                    time.sleep(sleep_s)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"Dajiala API error (try {i+1}/{retries}): {e}")
                time.sleep(sleep_s)
        return None

    @staticmethod
    def to_jsonl_records(api_resp, mp_name_fallback):
        # Ported from script.py
        data = api_resp.get("data")
        if not data:
            return []
        
        records = []
        for i, item in enumerate(data):
            # item structure from Dajiala
            rec = {
                "mp_nickname": item.get("mp_nickname") or mp_name_fallback,
                "mp_wxid": item.get("mp_wxid"),
                "mp_ghid": item.get("mp_ghid"),
                "title": item.get("title"),
                "digest": item.get("digest"),
                "url": item.get("url"),
                "position": item.get("position"),
                "post_time": item.get("post_time"), # timestamp
                "post_time_str": item.get("post_time_str"),
                "cover_url": item.get("cover"),
                "original": 1 if item.get("original") else 0,
                "item_show_type": item.get("item_show_type"),
                "types": item.get("types"),
                "is_deleted": 1 if item.get("is_deleted") else 0,
                "msg_status": item.get("msg_status"),
                "msg_fail_reason": item.get("msg_fail_reason"),
            }
            records.append(rec)
        return records

    @staticmethod
    def fetch_account_articles(account_id):
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM wx_mp_account WHERE id=%s", (account_id,))
        account = cur.fetchone()
        cur.close()
        
        if not account:
            raise ValueError("Account not found")

        name = account['mp_nickname']
        key = Config.DAJIALA_KEY
        if not key:
            raise ValueError("Missing DAJIALA_KEY")

        resp = CrawlerService.post_condition_by_name(name, key)
        if not resp:
            raise RuntimeError("API request failed")
        
        if resp.get('code') != 0:
             raise RuntimeError(f"API Error: {resp.get('msg')}")

        records = CrawlerService.to_jsonl_records(resp, name)
        
        # Store in DB
        # Reuse logic: insert_fetch_log, upsert_seed...
        # For brevity, let's implement simplified storage here or we'd need to copy those helpers too.
        # Let's copy the essential SQL calls.
        
        # 1. Update account info from resp
        mp_wxid = resp.get('mp_wxid')
        mp_ghid = resp.get('mp_ghid')
        CrawlerService.upsert_account(name, mp_wxid, mp_ghid) # Updates if exists
        
        # 2. Log fetch (Simplified - skipping detailed fetch log for now or implement if needed)
        # 3. Insert seeds
        count = 0
        cur = conn.cursor()
        try:
             for r in records:
                 types_json = json.dumps(r.get("types"), ensure_ascii=False) if r.get("types") else None
                 # Upsert Seed
                 sql = """
                 INSERT INTO wx_article_seed (
                   account_id, mp_nickname, mp_wxid, mp_ghid,
                   title, digest, url,
                   position, post_time, post_time_str,
                   cover_url, original, item_show_type, types,
                   is_deleted, first_seen_at, last_seen_at
                 ) VALUES (
                   %s, %s, %s, %s,
                   %s, %s, %s,
                   %s, %s, %s,
                   %s, %s, %s, %s,
                   %s, NOW(), NOW()
                 ) ON DUPLICATE KEY UPDATE
                   mp_nickname=VALUES(mp_nickname), mp_wxid=VALUES(mp_wxid), mp_ghid=VALUES(mp_ghid),
                   title=VALUES(title), digest=VALUES(digest),
                   position=VALUES(position), post_time=VALUES(post_time), post_time_str=VALUES(post_time_str),
                   cover_url=VALUES(cover_url), original=VALUES(original),
                   item_show_type=VALUES(item_show_type), types=VALUES(types),
                   is_deleted=VALUES(is_deleted), last_seen_at=NOW()
                 """
                 cur.execute(sql, (
                     account_id, r['mp_nickname'], r['mp_wxid'], r['mp_ghid'],
                     r['title'], r['digest'], r['url'],
                     r['position'], r['post_time'], r['post_time_str'],
                     r['cover_url'], r['original'], r['item_show_type'], types_json,
                     r['is_deleted']
                 ))
                 count += 1
             conn.commit()
        finally:
             cur.close()
        
        return count
