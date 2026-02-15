# -*- coding: utf-8 -*-
"""Reports API routes."""

import logging
from typing import Any, List, Optional

from aiomysql import Connection
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import get_db
import services.pipeline_service as pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


class CreateReportRequest(BaseModel):
    """Request model for creating a report."""

    report_date: str  # YYYY-MM-DD format


class ArticleInput(BaseModel):
    """Model for manual article input."""

    title: str
    content: str
    source_account: Optional[str] = None
    publish_time: Optional[int] = None
    url: Optional[str] = None
    article_detail_id: Optional[int] = None


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    code: int = Field(default=0)
    msg: str = Field(default="success")
    data: Optional[Any] = Field(default=None)


@router.get("/", response_model=ApiResponse)
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Get reports list with pagination."""
    try:
        query = "SELECT id, report_date, status, created_at, updated_at FROM reports"
        params = []

        if status:
            query += " WHERE status = %s"
            params.append(status)

        query += " ORDER BY report_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        async with conn.cursor() as cur:
            await cur.execute(query, params)
            rows = await cur.fetchall()

            # Get counts
            count_query = "SELECT COUNT(*) FROM reports"
            if status:
                count_query += " WHERE status = %s"
                await cur.execute(count_query, [status])
            else:
                await cur.execute(count_query)

            total = (await cur.fetchone())[0]

        reports = []
        for row in rows:
            reports.append({
                "id": row[0],
                "report_date": row[1].strftime("%Y-%m-%d") if row[1] else None,
                "status": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            })

        return ApiResponse(
            code=0,
            msg="success",
            data={
                "reports": reports,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    except Exception as e:
        logger.exception(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}", response_model=ApiResponse)
async def get_report(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Get single report by ID."""
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, report_date, status, created_at, updated_at FROM reports WHERE id = %s",
                (report_id,),
            )
            row = await cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Report not found")

            return ApiResponse(
                code=0,
                msg="success",
                data={
                    "id": row[0],
                    "report_date": row[1].strftime("%Y-%m-%d") if row[1] else None,
                    "status": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ApiResponse)
async def create_report(
    request: CreateReportRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Create a new report."""
    try:
        report_id = await pipeline_service.create_report(conn, request.report_date)

        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, report_date, status, created_at FROM reports WHERE id = %s",
                (report_id,),
            )
            row = await cur.fetchone()

            return ApiResponse(
                code=0,
                msg="success",
                data={
                    "id": row[0],
                    "report_date": row[1].strftime("%Y-%m-%d") if row[1] else None,
                    "status": row[2],
                    "created_at": row[3],
                },
            )

    except Exception as e:
        logger.exception(f"Failed to create report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{report_id}", response_model=ApiResponse)
async def delete_report(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Delete a report."""
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))

        return ApiResponse(
            code=0,
            msg="success",
            data={"deleted": report_id},
        )

    except Exception as e:
        logger.exception(f"Failed to delete report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{report_id}/generate", response_model=ApiResponse)
async def generate_report(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Run full pipeline to generate report."""
    try:
        # Get report date first
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT report_date FROM reports WHERE id = %s",
                (report_id,),
            )
            row = await cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Report not found")

            report_date = row[0].strftime("%Y-%m-%d") if row[0] else None

        # Run pipeline
        result = await pipeline_service.run_full_pipeline(conn, report_date)

        return ApiResponse(
            code=0,
            msg="success",
            data=result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}/check", response_model=ApiResponse)
async def check_report_data(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Check if report has data for each node."""
    try:
        # Get report date
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT report_date, status FROM reports WHERE id = %s",
                (report_id,),
            )
            row = await cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Report not found")

            report_date = row[0].strftime("%Y-%m-%d") if row[0] else None
            status = row[1]

        # Get article data from wx_article_detail for this date
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT COUNT(*) FROM wx_article_detail
                   WHERE DATE(FROM_UNIXTIME(pubtime)) = %s""",
                (report_date,),
            )
            article_count = (await cur.fetchone())[0]

        return ApiResponse(
            code=0,
            msg="success",
            data={
                "report_id": report_id,
                "report_date": report_date,
                "status": status,
                "has_article_data": article_count > 0,
                "article_count": article_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to check report data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}/summary", response_model=ApiResponse)
async def get_report_summary(
    report_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Get report summary with pool counts."""
    try:
        async with conn.cursor() as cur:
            # Get basic info
            await cur.execute(
                "SELECT report_date, status FROM reports WHERE id = %s",
                (report_id,),
            )
            row = await cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Report not found")

            # Get counts
            await cur.execute(
                "SELECT COUNT(*) FROM raw_articles WHERE report_id = %s",
                (report_id,),
            )
            article_count = (await cur.fetchone())[0]

            await cur.execute(
                "SELECT COUNT(*) FROM hot_topics WHERE report_id = %s",
                (report_id,),
            )
            topic_count = (await cur.fetchone())[0]

            await cur.execute(
                "SELECT COUNT(*) FROM stock_pool_1 WHERE report_id = %s",
                (report_id,),
            )
            pool1_count = (await cur.fetchone())[0]

            await cur.execute(
                "SELECT COUNT(*) FROM stock_pool_2 WHERE report_id = %s AND is_selected = TRUE",
                (report_id,),
            )
            pool2_count = (await cur.fetchone())[0]

        return ApiResponse(
            code=0,
            msg="success",
            data={
                "id": report_id,
                "report_date": row[0].strftime("%Y-%m-%d") if row[0] else None,
                "status": row[1],
                "article_count": article_count,
                "topic_count": topic_count,
                "pool1_count": pool1_count,
                "pool2_count": pool2_count,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get report summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
