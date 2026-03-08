# -*- coding: utf-8 -*-
"""LLM service for DeepSeek API."""

import json
import logging
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from config import get_settings

logger = logging.getLogger(__name__)

# Cache the OpenAI client
_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Get or create the OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


class LLMServiceError(Exception):
    """Exception raised for LLM service errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


TOPIC_EXTRACTION_PROMPT = """你是一个专业的A股题材挖掘分析师。请分析以下公众号文章内容，提炼出其中提到的热点板块/题材。

要求：
1. 识别文章中提到的所有行业板块、概念题材
2. 对于每个热点，给出简短的逻辑描述
3. 尝试匹配东方财富网的板块名称（如"人工智能"、"新能源汽车"、"低空经济"、"机器人"、"半导体"等）

请以JSON格式返回，格式如下：
{{
  "topics": [
    {{
      "topic_name": "板块名称",
      "related_boards": ["东财板块名1", "东财板块名2"],
      "logic_summary": "逻辑摘要，简短说明为什么这个题材是热点"
    }}
  ]
}}

文章内容：
{content}
"""


TOPIC_BOARD_MATCHING_PROMPT = """你是一个专业的A股题材与板块匹配分析师。现在有一批公众号文章，以及一份已经保存到数据库中的东方财富板块名称清单。

你的任务是：针对每一篇文章，从候选板块清单中选出最匹配的板块。

严格要求：
1. `matched_boards` 只能从候选板块清单中选择，禁止自造、改写、扩写板块名称。
2. 单篇文章最多匹配 3 个板块，宁缺毋滥，不是越多越好。
3. 如果文章和候选板块没有足够强的关联，可以返回空数组。
4. `topic_name` 用一句简洁短语概括文章的核心题材。
5. `logic_summary` 简要说明文章为什么匹配这些板块。
6. 需要覆盖输入中的每一篇文章，并原样返回 `article_id`。
7. 输出必须是纯 JSON，不要使用 markdown 代码块。

请按以下 JSON 格式返回：
{{
    "article_matches": [
        {{
            "article_id": 123,
            "topic_name": "文章核心题材",
            "matched_boards": ["板块1", "板块2"],
            "logic_summary": "匹配逻辑摘要"
        }}
    ]
}}

候选板块清单：
{sector_names}

文章列表：
{articles}
"""


STOCK_ANALYSIS_PROMPT = """你是一个专业的A股选股分析师。请分析以下股票列表，找出其中最具独特性和稀缺性的标的。

股票信息：
{stocks}

要求：
1. 分析每只股票的基本面和技术面特征
2. 找出每只股票的独特亮点和稀缺性（如：技术壁垒、市场份额、政策受益等）
3. 重点关注在同板块中具有差异化优势的公司

请以JSON格式返回，格式如下：
{{
  "analysis": [
    {{
      "stock_code": "股票代码",
      "stock_name": "股票名称",
      "unique_points": ["独特点1", "独特点2"],
      "scarcity_reason": "稀缺性分析，说明为什么这家公司具有稀缺价值",
      "reason_score": 0.8
    }}
  ]
}}
"""


async def extract_topics_from_articles(
    articles: List[Dict[str, Any]],
    sector_names: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Extract hot topics from articles using LLM.

    Args:
        articles: List of article dictionaries with title, content, etc.
        sector_names: Candidate sector names from sectors table

    Returns:
        List of topics with related boards and logic summary
    """
    if not articles:
        return []

    try:
        client = get_client()
        settings = get_settings()

        valid_sector_names = []
        if sector_names:
            deduped_sector_names = []
            seen_sector_names = set()
            for sector_name in sector_names:
                if not sector_name or sector_name in seen_sector_names:
                    continue
                seen_sector_names.add(sector_name)
                deduped_sector_names.append(sector_name)
            valid_sector_names = deduped_sector_names

        if valid_sector_names:
            article_payload = []
            for article in articles:
                article_payload.append(
                    {
                        "article_id": article.get("id"),
                        "title": article.get("title", ""),
                        "content": (article.get("content", "") or "")[:3000],
                    }
                )

            prompt = TOPIC_BOARD_MATCHING_PROMPT.format(
                sector_names=json.dumps(valid_sector_names, ensure_ascii=False),
                articles=json.dumps(article_payload, ensure_ascii=False),
            )

            response = await client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的A股题材与板块匹配分析师。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=3000,
            )

            content = response.choices[0].message.content

            if content.strip().startswith("```"):
                lines = content.strip().split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)

            result = json.loads(content)
            article_matches = result.get("article_matches", [])

            article_map = {article.get("id"): article for article in articles if article.get("id") is not None}
            sector_name_set = set(valid_sector_names)
            topics = []

            for match in article_matches:
                article_id = match.get("article_id")
                if article_id not in article_map:
                    continue

                matched_boards = []
                for board_name in match.get("matched_boards", []) or []:
                    if board_name in sector_name_set and board_name not in matched_boards:
                        matched_boards.append(board_name)

                matched_boards = matched_boards[:3]
                if not matched_boards:
                    continue

                article = article_map[article_id]
                topic_name = (match.get("topic_name") or article.get("title") or matched_boards[0]).strip()
                logic_summary = (match.get("logic_summary") or "").strip()
                if not logic_summary:
                    logic_summary = f"文章《{article.get('title', '')}》与板块 {', '.join(matched_boards)} 相关。"

                topics.append(
                    {
                        "topic_name": topic_name,
                        "related_boards": matched_boards,
                        "logic_summary": logic_summary,
                        "source_article_ids": [article_id],
                    }
                )

            return topics

        # Combine article content for analysis
        combined_content = ""
        for article in articles[:5]:  # Limit to 5 articles to avoid token limit
            title = article.get("title", "")
            content = article.get("content", "")
            combined_content += f"【{title}】\n{content[:2000]}\n\n"  # Truncate long content

        prompt = TOPIC_EXTRACTION_PROMPT.format(content=combined_content)

        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": "你是一个专业的A股题材挖掘分析师。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content

        # Strip markdown code block formatting if present
        if content.strip().startswith("```"):
            lines = content.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        result = json.loads(content)

        return result.get("topics", [])

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {content if 'content' in locals() else 'N/A'}")
        raise LLMServiceError(f"解析LLM响应失败: {e}")
    except Exception as e:
        logger.error(f"Failed to extract topics from articles: {e}")
        raise LLMServiceError(f"提取热点话题失败: {e}")


async def analyze_stock_uniqueness(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze stock uniqueness and scarcity using LLM.

    Args:
        stocks: List of stock dictionaries with code, name, and other info

    Returns:
        List of analysis results for each stock
    """
    if not stocks:
        return []

    try:
        client = get_client()

        # Format stock info for LLM
        stocks_text = ""
        for stock in stocks[:10]:  # Limit to 10 stocks
            code = stock.get("code", "")
            name = stock.get("name", "")
            topic = stock.get("topic_name", "")
            stocks_text += f"- {code} {name} ({topic})\n"

        prompt = STOCK_ANALYSIS_PROMPT.format(stocks=stocks_text)
        settings = get_settings()

        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": "你是一个专业的A股选股分析师。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        content = response.choices[0].message.content

        # Strip markdown code block formatting if present
        if content.strip().startswith("```"):
            lines = content.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        result = json.loads(content)

        return result.get("analysis", [])

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {content if 'content' in locals() else 'N/A'}")
        raise LLMServiceError(f"解析LLM响应失败: {e}")
    except Exception as e:
        logger.error(f"Failed to analyze stock uniqueness: {e}")
        raise LLMServiceError(f"分析股票独特性失败: {e}")
