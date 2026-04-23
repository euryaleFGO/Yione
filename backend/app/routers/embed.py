"""Embed SDK token 签发（M6）。

调用者把 API Key 放 header ``X-API-Key``，Origin 由浏览器自动带上。
服务端：

1. 查 tenant，key 不对 → 401
2. 校验 Origin 是否在 tenant.allowed_origins（空列表/``["*"]`` 视为全通）
3. 签 JWT（kind=embed），返回 ``{token, expires_in, tenant_id}``

后续前端把 token 挂到 HttpClient / ChatSocket 的 ``getToken`` 上即可。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.services.auth_service import issue_embed_token
from app.services.tenant_service import get_tenant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embed", tags=["embed"])


class EmbedTokenResponse(BaseModel):
    token: str
    expires_in: int
    tenant_id: str


@router.post("/token", response_model=EmbedTokenResponse)
async def issue_token(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    origin: str | None = Header(default=None, alias="Origin"),
) -> EmbedTokenResponse:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-API-Key header",
        )

    tenants = get_tenant_service()
    tenant = tenants.verify_api_key(x_api_key)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )

    if not tenant.origin_allowed(origin):
        logger.warning(
            "tenant %s 拒绝来自 Origin=%s 的 embed token 请求（白名单=%s）",
            tenant.id,
            origin,
            tenant.allowed_origins,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"origin not allowed: {origin}",
        )

    token, expires_in = issue_embed_token(tenant.id, scope=tenant.scope)
    return EmbedTokenResponse(token=token, expires_in=expires_in, tenant_id=tenant.id)
