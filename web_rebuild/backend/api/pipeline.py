# -*- coding: utf-8 -*-
"""Pipeline API routes."""

import logging
from typing import Any, List, Optional

from aiomysql import Connection
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from database import get_db, Database
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


@router.post("/{report_id}/rerun/{step_number}", response_model=ApiResponse)
async def rerun_step(
    report_id: int,
    step_number: int,
    background_tasks: BackgroundTasks,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Rerun a specific pipeline step.

    Args:
        report_id: Report ID
        step_number: Step number (2, 3, or 4)
    """
    if step_number < 2 or step_number > 4:
        raise HTTPException(status_code=400, detail="Step number must be 2, 3, or 4")

    try:
        # Check if report exists
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM reports WHERE id = %s", (report_id,))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Report not found")

        # Clear data for this step and subsequent steps
        deleted = await pipeline_service.clear_step_data(conn, report_id, step_number)

        # Start rerun in background
        background_tasks.add_task(run_step_task, report_id, step_number)

        return ApiResponse(
            code=0,
            msg=f"Step {step_number} rerun started",
            data={"cleared": deleted, "step": step_number},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to rerun step {step_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_step_task(report_id: int, step_number: int):
    """Background task to run a single step."""
    try:
        logger.info(f"Starting background step {step_number} for report {report_id}")

        async with Database.get_connection() as conn:
            if step_number == 2:
                result = await pipeline_service.step2_extract_topics(conn, report_id)
                logger.info(f"Step 2 completed: {len(result)} topics extracted")

            elif step_number == 3:
                count = await pipeline_service.step3_get_board_stocks(conn, report_id)
                logger.info(f"Step 3 completed: {count} stocks added to pool 1")

            elif step_number == 4:
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
                count = await pipeline_service.step4_apply_rules(conn, report_id, rules_config)
                logger.info(f"Step 4 completed: {count} stocks selected")

    except Exception as e:
        logger.exception(f"Step {step_number} failed for report {report_id}: {e}")
