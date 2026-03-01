# -*- coding: utf-8 -*-
"""Settings API routes."""

import json
import logging
from typing import Any, List, Optional

from aiomysql import Connection
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    code: int = Field(default=0)
    msg: str = Field(default="success")
    data: Optional[Any] = Field(default=None)


class CreateAccountRequest(BaseModel):
    """Request model for creating target account."""

    account_name: str
    wx_id: Optional[str] = None
    status: str = "active"
    sort_order: int = 0


class UpdateAccountRequest(BaseModel):
    """Request model for updating target account."""

    account_name: Optional[str] = None
    wx_id: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class UpdateRuleRequest(BaseModel):
    """Request model for updating rule config."""

    rule_name: Optional[str] = None
    rule_value: Optional[Any] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("/accounts", response_model=ApiResponse)
async def list_accounts(
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Get target accounts list."""
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, account_name, wx_id, status, sort_order, created_at, updated_at FROM target_accounts ORDER BY sort_order, id"
            )
            rows = await cur.fetchall()

        accounts = []
        for row in rows:
            accounts.append({
                "id": row[0],
                "account_name": row[1],
                "wx_id": row[2],
                "status": row[3],
                "sort_order": row[4],
                "created_at": row[5],
                "updated_at": row[6],
            })

        return ApiResponse(
            code=0,
            msg="success",
            data={"accounts": accounts},
        )

    except Exception as e:
        logger.exception(f"Failed to list accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts", response_model=ApiResponse)
async def create_account(
    request: CreateAccountRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Create a new target account."""
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO target_accounts (account_name, wx_id, status, sort_order)
                   VALUES (%s, %s, %s, %s)""",
                (request.account_name, request.wx_id, request.status, request.sort_order),
            )
            account_id = cur.lastrowid

        return ApiResponse(
            code=0,
            msg="success",
            data={"id": account_id},
        )

    except Exception as e:
        logger.exception(f"Failed to create account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/accounts/{account_id}", response_model=ApiResponse)
async def update_account(
    account_id: int,
    request: UpdateAccountRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Update target account."""
    try:
        updates = []
        params = []

        if request.account_name is not None:
            updates.append("account_name = %s")
            params.append(request.account_name)

        if request.wx_id is not None:
            updates.append("wx_id = %s")
            params.append(request.wx_id)

        if request.status is not None:
            updates.append("status = %s")
            params.append(request.status)

        if request.sort_order is not None:
            updates.append("sort_order = %s")
            params.append(request.sort_order)

        if updates:
            updates.append("updated_at = NOW()")

        query = f"UPDATE target_accounts SET {', '.join(updates)} WHERE id = %s"
        params.append(account_id)

        async with conn.cursor() as cur:
            await cur.execute(query, params)

        return ApiResponse(
            code=0,
            msg="success",
            data={"updated": account_id},
        )

    except Exception as e:
        logger.exception(f"Failed to update account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_id}", response_model=ApiResponse)
async def delete_account(
    account_id: int,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Delete target account."""
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM target_accounts WHERE id = %s", (account_id,))

        return ApiResponse(
            code=0,
            msg="success",
            data={"deleted": account_id},
        )

    except Exception as e:
        logger.exception(f"Failed to delete account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=ApiResponse)
async def list_rules(
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Get strategy rules list."""
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, rule_key, rule_name, rule_value, description, is_enabled, sort_order FROM strategy_config ORDER BY sort_order, id"
            )
            rows = await cur.fetchall()

        rules = []
        for row in rows:
            rules.append({
                "id": row[0],
                "rule_key": row[1],
                "rule_name": row[2],
                "rule_value": row[3] if isinstance(row[3], dict) else {},
                "description": row[4],
                "is_enabled": row[5],
                "sort_order": row[6],
            })

        return ApiResponse(
            code=0,
            msg="success",
            data={"rules": rules},
        )

    except Exception as e:
        logger.exception(f"Failed to list rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/rules/{rule_key}", response_model=ApiResponse)
async def update_rule(
    rule_key: str,
    request: UpdateRuleRequest,
    conn: Connection = Depends(get_db),
) -> ApiResponse:
    """Update rule configuration."""
    try:
        updates = []
        params = []

        if request.rule_name is not None:
            updates.append("rule_name = %s")
            params.append(request.rule_name)

        if request.rule_value is not None:
            updates.append("rule_value = %s")
            params.append(json.dumps(request.rule_value, ensure_ascii=False))

        if request.description is not None:
            updates.append("description = %s")
            params.append(request.description)

        if request.is_enabled is not None:
            updates.append("is_enabled = %s")
            params.append(request.is_enabled)

        if request.sort_order is not None:
            updates.append("sort_order = %s")
            params.append(request.sort_order)

        if updates:
            updates.append("updated_at = NOW()")

        query = f"UPDATE strategy_config SET {', '.join(updates)} WHERE rule_key = %s"
        params.append(rule_key)

        async with conn.cursor() as cur:
            await cur.execute(query, params)

        return ApiResponse(
            code=0,
            msg="success",
            data={"updated": rule_key},
        )

    except Exception as e:
        logger.exception(f"Failed to update rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))
