"""JWT 签发与校验（M6）。

Phase 1 / Phase 2 先用最小可用形态：

- 主站首页是公开 demo，不强制登录；用户直接开 `/` 走匿名 session。
- 第三方 embed 走 ``POST /api/embed/token``（header ``X-API-Key``），服务端
  查 tenants.json 确认 key + Origin 白名单后签发短期 JWT，前端把 token
  挂到 HttpClient 和 ChatSocket 上。

JWT payload 字段：

- ``sub``：主体 id（embed 用 tenant_id；未来用户登录后换成 user_id）
- ``tenant_id``：租户，用来做 quota / character 白名单
- ``scope``：一组权限字符串（``chat``、``embed``、``admin``）
- ``kind``：``access`` | ``embed`` | ``refresh``，便于 middleware 快速分类
- ``iat`` / ``exp``：签发 / 过期时间戳（秒）
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

from jose import JWTError, jwt

from app.config import get_settings

logger = logging.getLogger(__name__)

TokenKind = Literal["access", "embed", "refresh"]


class AuthError(Exception):
    """凭证缺失 / 无效 / 过期 — 对外统一 401。"""


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """解码后的 JWT 内容；中间件把它注入到 Request.state。"""

    sub: str
    tenant_id: str | None
    scope: tuple[str, ...]
    kind: TokenKind
    iat: int
    exp: int

    def has_scope(self, required: str) -> bool:
        return required in self.scope


def _now() -> int:
    return int(time.time())


def _encode(
    *,
    sub: str,
    tenant_id: str | None,
    scope: list[str],
    kind: TokenKind,
    ttl_seconds: int,
) -> str:
    s = get_settings()
    iat = _now()
    payload: dict[str, Any] = {
        "sub": sub,
        "tenant_id": tenant_id,
        "scope": scope,
        "kind": kind,
        "iat": iat,
        "exp": iat + ttl_seconds,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def issue_embed_token(
    tenant_id: str,
    *,
    scope: list[str] | None = None,
    ttl_seconds: int | None = None,
) -> tuple[str, int]:
    """签发第三方 embed 用的短期 token，返回 ``(token, expires_in_seconds)``。"""
    s = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else s.jwt_embed_ttl_seconds
    token = _encode(
        sub=f"tenant:{tenant_id}",
        tenant_id=tenant_id,
        scope=scope or ["chat", "embed"],
        kind="embed",
        ttl_seconds=ttl,
    )
    return token, ttl


def issue_access_token(
    user_id: str,
    tenant_id: str | None = None,
    *,
    scope: list[str] | None = None,
    ttl_seconds: int | None = None,
) -> tuple[str, int]:
    """签发普通用户 access token（未来登录时用；M6 先留接口）。"""
    s = get_settings()
    # access 默认比 embed 短，跟 embed TTL 共用；refresh 会更长
    ttl = ttl_seconds if ttl_seconds is not None else s.jwt_embed_ttl_seconds
    token = _encode(
        sub=f"user:{user_id}",
        tenant_id=tenant_id,
        scope=scope or ["chat"],
        kind="access",
        ttl_seconds=ttl,
    )
    return token, ttl


def decode_token(token: str) -> TokenClaims:
    """校验签名和 exp，返回 TokenClaims；失败抛 AuthError。"""
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError as exc:
        raise AuthError(f"invalid token: {exc}") from exc

    try:
        return TokenClaims(
            sub=str(payload["sub"]),
            tenant_id=payload.get("tenant_id"),
            scope=tuple(payload.get("scope") or ()),
            kind=payload.get("kind", "access"),
            iat=int(payload["iat"]),
            exp=int(payload["exp"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError(f"malformed token payload: {exc}") from exc


__all__ = [
    "AuthError",
    "TokenClaims",
    "TokenKind",
    "decode_token",
    "issue_access_token",
    "issue_embed_token",
]
