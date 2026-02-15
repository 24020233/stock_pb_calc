# -*- coding: utf-8 -*-
"""Pipeline API routes."""

import logging
from typing import Any, List, Optional

from aiomysql import Connection
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import get_db
import services.pipeline_service as pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    code: int = Field(default=0)
    msg: str = Field(default="success")
    data: Optional[Any] = Field(default=None)


class AddArticlesRequest(BaseModel):
    """Request model for adding articles."""

    report_id: int
    articles: List[dict]


@router.post("/step1-articles", response_model=ApiResponse)
async def step1_add_articles(
    request: AddArticlesRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Step 1: Add articles to report."""
    try:
        article_ids = await pipeline_service.step1_add_articles(conn, request.report_id, request.articles)

        return ApiResponse(
            code=0,
            msg="success",
            data={"added_count": len(article_ids), "article_ids": article_ids},
        )

    except Exception as e:
        logger.exception(f"Failed to add articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{report_id}/step2-topics", response_model=ApiResponse)
async def step2_extract_topics(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Step 2: Extract topics from articles using LLM."""
    try:
        topics = await pipeline_service.step2_extract_topics(conn, report_id)

        return ApiResponse(
            code=0,
            msg="success",
            data={"topics": topics, "count": len(topics)},
        )

    except Exception as e:
        logger.exception(f"Failed to extract topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{report_id}/step3-pool1", response_model=ApiResponse)
async def step3_get_board_stocks(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Step 3: Get stocks from board names."""
    try:
        stock_count = await pipeline_service.step3_get_board_stocks(conn, report_id)

        return ApiResponse(
            code=0,
            msg="success",
            data={"stock_count": stock_count},
        )

    except Exception as e:
        logger.exception(f"Failed to get board stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{report_id}/step4-pool2", response_model=ApiResponse)
async def step4_apply_rules(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Step 4: Apply rules to stock pool 1."""
    try:
        # Get rule configurations
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT rule_key, rule_value, is_enabled FROM strategy_config WHERE is_enabled = TRUE ORDER BY sort_order",
            )
            rows = await cur.fetchall()
            rules_config = [
                {"rule_key": row[0], "rule_value": row[1], "is_enabled": row[2]}
                for row in rows
            ]

        selected_count = await pipeline_service.step4_apply_rules(conn, report_id, rules_config)

        return ApiResponse(
            code=0,
            msg="success",
            data={"selected_count": selected_count, "rules_applied": len(rules_config)},
        )

    except Exception as e:
        logger.exception(f"Failed to apply rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}/nodes", response_model=ApiResponse)
async def get_pipeline_nodes(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Get all pipeline node data for a report."""
    try:
        nodes = await pipeline_service.get_pipeline_nodes(conn, report_id)

        return ApiResponse(
            code=0,
            msg="success",
            data=nodes,
        )

    except Exception as e:
        logger.exception(f"Failed to get pipeline nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
