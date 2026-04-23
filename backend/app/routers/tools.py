"""工具调用 API（M20）。

Agent 工具调用支持：搜索/记忆/提醒/天气。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolCall(BaseModel):
    name: str
    args: dict = {}
    result: str = ""


class ToolListResponse(BaseModel):
    tools: list[dict]


AVAILABLE_TOOLS = [
    {"name": "search", "description": "搜索网络信息"},
    {"name": "memory", "description": "查询长期记忆"},
    {"name": "reminder", "description": "设置提醒"},
    {"name": "weather", "description": "查询天气"},
]


@router.get("", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    return ToolListResponse(tools=AVAILABLE_TOOLS)


@router.post("/call", response_model=ToolCall)
async def call_tool(body: ToolCall, request: Request) -> ToolCall:
    """模拟工具调用（实际集成 Ling Agent 时会替换）。"""
    name = body.name

    if name == "weather":
        body.result = "今天晴天，气温 25°C，适合出门。"
    elif name == "search":
        body.result = f"搜索结果：关于「{body.args.get('query', '')}」的最新信息。"
    elif name == "memory":
        body.result = "你之前问过关于 Live2D 的问题。"
    elif name == "reminder":
        body.result = f"已设置提醒：{body.args.get('message', '')}"
    else:
        raise HTTPException(status_code=400, detail=f"未知工具: {name}")

    return body
