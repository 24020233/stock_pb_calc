# -*- coding: utf-8 -*-
"""Stock data API routes."""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import services.stock_service as stock_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    code: int = Field(default=0)
    msg: str = Field(default="success")
    data: Optional[Any] = Field(default=None)


@router.get("/boards", response_model=ApiResponse)
async def list_boards() -> ApiResponse:
    """Get all stock sector/industry boards."""
    try:
        boards = stock_service.get_stock_boards()

        return ApiResponse(
            code=0,
            msg="success",
            data={"boards": boards},
        )

    except stock_service.StockServiceError as e:
        logger.error(f"Stock service error: {e}")
        return ApiResponse(
            code=1,
            msg=str(e),
            data=None,
        )
    except Exception as e:
        logger.exception(f"Failed to list boards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boards/{board_name}/stocks", response_model=ApiResponse)
async def get_board_stocks(board_name: str) -> ApiResponse:
    """Get stocks in a specific board."""
    try:
        stocks = stock_service.get_stocks_by_board(board_name)

        return ApiResponse(
            code=0,
            msg="success",
            data={"stocks": stocks, "count": len(stocks)},
        )

    except stock_service.StockServiceError as e:
        logger.error(f"Stock service error: {e}")
        return ApiResponse(
            code=1,
            msg=str(e),
            data=None,
        )
    except Exception as e:
        logger.exception(f"Failed to get board stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stock_code}/snapshot", response_model=ApiResponse)
async def get_stock_snapshot(stock_code: str) -> ApiResponse:
    """Get stock real-time snapshot data."""
    try:
        snapshot = stock_service.get_stock_snapshot(stock_code)

        return ApiResponse(
            code=0,
            msg="success",
            data=snapshot,
        )

    except stock_service.StockServiceError as e:
        logger.error(f"Stock service error: {e}")
        return ApiResponse(
            code=1,
            msg=str(e),
            data=None,
        )
    except Exception as e:
        logger.exception(f"Failed to get stock snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/{keyword}", response_model=ApiResponse)
async def search_stocks(keyword: str) -> ApiResponse:
    """Search stocks by keyword."""
    try:
        stocks = stock_service.search_stock(keyword)

        return ApiResponse(
            code=0,
            msg="success",
            data={"stocks": stocks, "count": len(stocks)},
        )

    except stock_service.StockServiceError as e:
        logger.error(f"Stock service error: {e}")
        return ApiResponse(
            code=1,
            msg=str(e),
            data=None,
        )
    except Exception as e:
        logger.exception(f"Failed to search stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
