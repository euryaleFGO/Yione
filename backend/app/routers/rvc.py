"""RVC 声线转换 API（M26）。

提供声线转换接口（需要 RVC 微服务部署）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rvc", tags=["rvc"])


class RVCConvertRequest(BaseModel):
    audio_url: str
    model: str = "default"


class RVCConvertResponse(BaseModel):
    output_url: str
    model: str


@router.post("/convert", response_model=RVCConvertResponse)
async def convert_voice(body: RVCConvertRequest) -> RVCConvertResponse:
    """声线转换（需部署 RVC 微服务）。"""
    # M26 占位：实际需要调用 RVC 微服务
    raise HTTPException(
        status_code=501,
        detail="RVC 微服务未部署。请参考 M26 文档部署 RVC 服务。"
    )


@router.get("/models")
async def list_models() -> dict:
    """列出可用的 RVC 模型。"""
    return {
        "models": [
            {"id": "default", "name": "默认模型"},
        ]
    }
