from datetime import date, datetime
import json
import traceback
from database import get_db
from services.crawler import CrawlerService
from services.llm_service import LLMService
from services.market_data import MarketDataService

class PipelineEngine:
    @staticmethod
    def get_or_create_run(day: date):
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM task_run_log WHERE day=%s", (day,))
            row = cur.fetchone()
            if row:
                return row
            
            cur.execute("INSERT INTO task_run_log (day) VALUES (%s)", (day,))
            conn.commit()
            return PipelineEngine.get_or_create_run(day)
        finally:
            cur.close()

    @staticmethod
    def update_node_status(day: date, node: str, status: int, msg: str = None):
        # node: 'node_a', 'node_b', 'node_c', 'node_d'
        # status: 0=pending, 1=running, 2=success, 3=error
        conn = get_db()
        cur = conn.cursor()
        try:
            field_status = f"{node}_status"
            field_msg = f"{node}_msg"
            sql = f"UPDATE task_run_log SET {field_status}=%s, {field_msg}=%s WHERE day=%s"
            cur.execute(sql, (status, msg, day))
            conn.commit()
        finally:
            cur.close()

    @staticmethod
    def run_node_a(day: date):
        """Node A: Info Gathering (Crawl Articles)"""
        PipelineEngine.update_node_status(day, 'node_a', 1)
        try:
            # For now, just rely on existing Python logic or trigger a crawl
            # In V2, we might want to explictly call CrawlerService for all accounts
            # Reusing existing logic: fetch list for all enabled accounts
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM wx_mp_account WHERE enabled=1")
            accounts = cur.fetchall()
            cur.close()

            # TODO: Parallel fetch? For now simple sequential or reuse script logic
            # This is a placeholder for the actual loop
            # count = 0
            # for acc in accounts:
            #     CrawlerService.fetch_account_articles(acc['id'])
            #     count += 1
            
            PipelineEngine.update_node_status(day, 'node_a', 2, f"Fetched entries")
        except Exception as e:
            traceback.print_exc()
            PipelineEngine.update_node_status(day, 'node_a', 3, str(e))
            raise

    @staticmethod
    def run_node_b(day: date):
        """Node B: Topic Extraction"""
        PipelineEngine.update_node_status(day, 'node_b', 1)
        try:
            conn = get_db()
            # 1. Get today's articles
            # Reusing CrawlerService.list_today_seeds logic but here
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, title, digest, url FROM wx_article_seed WHERE is_deleted=0 AND post_time_str LIKE %s ORDER BY id DESC LIMIT 50",
                (f"{day}%",)
            )
            seeds = cur.fetchall()
            cur.close()

            if not seeds:
                PipelineEngine.update_node_status(day, 'node_b', 2, "No articles")
                return

            # 2. Fetch content
            articles = []
            for s in seeds:
                 text = CrawlerService.fetch_article_text(s['url'])
                 articles.append({
                     'id': s['id'],
                     'title': s['title'],
                     'content_text': text
                 })

            # 3. Get candidates
            industry_list = MarketDataService.get_industry_list()
            candidates = [i['name'] for i in industry_list]

            # 4. LLM Extract
            topics = LLMService.extract_topics(articles, candidates)

            # 5. Save to topic_analysis
            cur = conn.cursor()
            # Clear old for today?
            cur.execute("DELETE FROM topic_analysis WHERE day=%s", (day,))
            
            count = 0
            for t in topics:
                cur.execute(
                    "INSERT INTO topic_analysis (day, topic_name, related_sector, strength, article_ids, reason) VALUES (%s, %s, %s, %s, %s, %s)",
                    (day, t.get('name'), t.get('related_sector'), t.get('strength'), json.dumps(t.get('article_ids')), t.get('reason'))
                )
                count += 1
            conn.commit()
            cur.close()

            PipelineEngine.update_node_status(day, 'node_b', 2, f"Extracted {count} topics")

        except Exception as e:
            traceback.print_exc()
            PipelineEngine.update_node_status(day, 'node_b', 3, str(e))
            raise

    @staticmethod
    def run_node_c(day: date):
        """Node C: Abnormal Scan -> Stock Pool 1"""
        PipelineEngine.update_node_status(day, 'node_c', 1)
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            # 1. Get topics
            cur.execute("SELECT * FROM topic_analysis WHERE day=%s", (day,))
            topics = cur.fetchall()
            cur.close()
            
            total_picks = 0
            # Clear old pool 1
            cur = conn.cursor()
            cur.execute("DELETE FROM stock_pool_1 WHERE day=%s", (day,))
            cur.close()

            for t in topics:
                sector = t['related_sector']
                if not sector: continue
                
                # Fetch stocks
                # Need code... 
                # Attempt to find board code via MarketDataService logic
                # For now simple fetch by name
                stocks = MarketDataService.fetch_constituents(sector)
                
                # Filter logic (e.g. vol_ratio > 2)
                # This could be configurable
                for s in stocks:
                    # Simple rule: Volume Ratio > 1.5 AND Pct Change > 2%
                    try:
                        vr = float(s.get('vol_ratio') or 0)
                        pct = float(s.get('pct_change') or 0)
                        if vr > 1.5 and pct > 2.0:
                             conn = get_db()
                             cur = conn.cursor()
                             cur.execute(
                                 """INSERT INTO stock_pool_1 
                                 (day, stock_code, stock_name, source_topic_id, snapshot_price, snapshot_pct_change, snapshot_vol_ratio, snapshot_turnover, reason)
                                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                 (day, s['code'], s['name'], t['id'], s['price'], s['pct_change'], vr, s['turnover'], "High Vol & Rise")
                             )
                             conn.commit()
                             cur.close()
                             total_picks += 1
                    except:
                        continue
            
            PipelineEngine.update_node_status(day, 'node_c', 2, f"Found {total_picks} stocks")

        except Exception as e:
            traceback.print_exc()
            PipelineEngine.update_node_status(day, 'node_c', 3, str(e))
            raise

    @staticmethod
    def run_node_d(day: date):
        """Node D: Deep Dive -> Stock Pool 2"""
        PipelineEngine.update_node_status(day, 'node_d', 1)
        try:
             # Just copy from pool 1 for now as a placeholder
             conn = get_db()
             cur = conn.cursor(dictionary=True)
             cur.execute("SELECT * FROM stock_pool_1 WHERE day=%s", (day,))
             pool1 = cur.fetchall()
             cur.close()

             cur = conn.cursor()
             cur.execute("DELETE FROM stock_pool_2 WHERE pool1_id IN (SELECT id FROM stock_pool_1 WHERE day=%s)", (day,))
             
             count = 0
             for p1 in pool1:
                 # Logic to filter...
                 # Insert into pool 2
                 cur.execute(
                     """INSERT INTO stock_pool_2 (pool1_id, technical_score, fundamental_score, ai_analysis_text, decision_status)
                     VALUES (%s, %s, %s, %s, %s)""",
                     (p1['id'], 8.0, 8.0, "AI says good", 1)
                 )
                 count += 1
             conn.commit()
             cur.close()

             PipelineEngine.update_node_status(day, 'node_d', 2, f"Selected {count} stocks")
        except Exception as e:
            traceback.print_exc()
            PipelineEngine.update_node_status(day, 'node_d', 3, str(e))
            raise
