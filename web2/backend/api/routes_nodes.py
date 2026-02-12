from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db
import json

bp = Blueprint('nodes', __name__, url_prefix='/api')

@bp.route('/node_a/articles', methods=['GET'])
def get_articles():
    # Similar to list_today_seeds in script.py
    day_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        # Reuse existing logic to query wx_article_seed
        cur.execute(
            """SELECT id, title, digest, url, post_time_str, mp_nickname 
            FROM wx_article_seed 
            WHERE is_deleted=0 AND post_time_str LIKE %s
            ORDER BY post_time DESC, id DESC LIMIT 200""",
            (f"{day_str}%",)
        )
        rows = cur.fetchall()
        cur.close()
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/node_b/topics', methods=['GET'])
def get_topics():
    day_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM topic_analysis WHERE day=%s", (day_str,))
        rows = cur.fetchall()
        cur.close()
        for r in rows:
            if isinstance(r.get('article_ids'), str):
                try: r['article_ids'] = json.loads(r['article_ids'])
                except: pass
            if r.get('created_at'): r['created_at'] = str(r['created_at'])
            if r.get('updated_at'): r['updated_at'] = str(r['updated_at'])
            if r.get('day'): r['day'] = str(r['day'])
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/node_c/stocks', methods=['GET'])
def get_pool1():
    day_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT p.*, t.topic_name, t.related_sector 
            FROM stock_pool_1 p 
            LEFT JOIN topic_analysis t ON p.source_topic_id = t.id
            WHERE p.day=%s
        """, (day_str,))
        rows = cur.fetchall()
        cur.close()
        # Serialize decimals
        for r in rows:
            for k, v in r.items():
                if hasattr(v, 'quantize'): # Decimal
                    r[k] = float(v)
            if r.get('created_at'): r['created_at'] = str(r['created_at'])
            if r.get('day'): r['day'] = str(r['day'])
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/node_d/stocks', methods=['GET'])
def get_pool2():
    day_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT p2.*, p1.stock_code, p1.stock_name, p1.snapshot_price, p1.snapshot_pct_change
            FROM stock_pool_2 p2
            JOIN stock_pool_1 p1 ON p2.pool1_id = p1.id
            WHERE p1.day=%s
        """, (day_str,))
        rows = cur.fetchall()
        cur.close()
        for r in rows:
            for k, v in r.items():
                if hasattr(v, 'quantize'): # Decimal
                    r[k] = float(v)
            if r.get('created_at'): r['created_at'] = str(r['created_at'])
            if r.get('updated_at'): r['updated_at'] = str(r['updated_at'])
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
