import requests
import json
import os
from config import Config

class LLMService:
    @staticmethod
    def extract_topics(articles, candidate_sectors=None):
        """
        Node B: Extract topics/sectors from articles.
        Returns a list of dicts: {"name": str, "related_sector": str, "strength": float, "article_ids": [], "reason": str}
        """
        api_key = Config.DEEPSEEK_API_KEY
        if not api_key:
            raise RuntimeError("missing-env:DEEPSEEK_API_KEY")

        base_url = Config.DEEPSEEK_BASE_URL.rstrip("/")
        model = Config.DEEPSEEK_MODEL

        # Prepare context from articles
        max_chars = int(os.environ.get("SECTOR_ARTICLE_MAX_CHARS", "2000"))
        parts = []
        # articles is expected to be a list of dicts with 'id', 'title', 'content_text'
        for i, a in enumerate(articles, start=1):
            title = (a.get("title") or "").strip()
            body = (a.get("content_text") or "").strip()
            if max_chars > 0 and len(body) > max_chars:
                body = body[:max_chars] + "\n..."
            parts.append(f"[Article {a['id']}]\nTitle: {title}\nContent: {body}\n")

        joined_text = "\n---\n".join(parts)

        # Build candidate block if any
        candidate_block = ""
        if candidate_sectors:
            lines = [f"{i+1}. {name}" for i, name in enumerate(sorted(set(candidate_sectors)))]
            candidate_block = "\nCandidate Industries (Select from here if applicable):\n" + "\n".join(lines) + "\n"

        system_prompt = (
            "You are a financial analyst. Task: Extract 'Hot Topics' or 'Sectors' from the provided news articles.\n"
            "Output JSON only. Structure: \n"
            "{\"topics\": [{\"name\": \"Topic Name\", \"related_sector\": \"Standard Sector Name\", \"strength\": 0.0-10.0, \"article_ids\": [id1, id2...], \"reason\": \"Why this is hot\"}] }\n"
            "Rules:\n"
            "1. 'name' should be the specific concept (e.g., 'Low-Altitude Economy').\n"
            "2. 'related_sector' should be the broader industry (e.g., 'Aviation'). Use candidate list if provided.\n"
            "3. 'strength' is your assessment of market hype (0-10).\n"
            "4. 'article_ids' must map back to the input article IDs.\n"
        )

        user_prompt = f"Here are the articles:\n{candidate_block}\n\n{joined_text}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"} 
        }

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            return json.loads(content).get('topics', [])
        except Exception as e:
            print(f"LLM Error: {e}")
            raise

    @staticmethod
    def analyze_stock(stock_info, market_data):
        """
        Node D: Deep dive analysis for a single stock.
        Returns dict with scores and analysis text.
        """
        # TODO: Implement Node D logic
        pass
