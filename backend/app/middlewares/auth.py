"""鉴权依赖（M6）。

三个层级，分别用不同 FastAPI Depends：

- ``optional_user``：解析 Bearer token，成功则返回 TokenClaims，没带/无效则返回 None。
  用于主站公开接口（例如匿名 demo）。
- ``require_user``：必须有 token，无效/缺失直接 401。
- ``require_scope(scope)``：在 require_user 基础上再校验权限字符串。

WebSocket 握手走单独路径：chat_ws 会自行从 query 参数读 token，用
``decode_ws_token`` 校验，因为 FastAPI 的 Depends 在 WebSocket 上用法有限。
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.services.auth_service import AuthError, TokenClaims, decode_token

# auto_error=False：我们自己决定缺 token 该不该报错（optional vs require）
_bearer = HTTPBearer(auto_error=False)


def _is_dev_mode() -> bool:
    """开发/测试模式下允许匿名：主站 demo 没登录也能聊。"""
    return get_settings().env in {"development", "test"}


def optional_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenClaims | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        claims = decode_token(creds.credentials)
    except AuthError:
        return None
    request.state.auth = claims
    return claims


def require_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenClaims:
    # 开发模式下允许未带 token 直接进入（方便本地 dev 跑主站）；
    # 生产环境必须带 Bearer token
    if creds is None or creds.scheme.lower() != "bearer":
        if _is_dev_mode():
            return TokenClaims(
                sub="anon:dev",
                tenant_id=None,
                scope=("chat",),
                kind="access",
                iat=0,
                exp=2**31 - 1,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_token(creds.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    request.state.auth = claims
    return claims


def require_scope(scope: str) -> Callable[[TokenClaims], TokenClaims]:
    """返回一个 Depends factory，要求 token 带上指定 scope。"""

    def _checker(claims: TokenClaims = Depends(require_user)) -> TokenClaims:
        if not claims.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing scope: {scope}",
            )
        return claims

    return _checker


def decode_ws_token(token: str | None) -> TokenClaims | None:
    """WS 握手专用：带 token 校验，否则（dev 环境下）放行。

    - 没带 token 且 dev → None（chat_ws 就当匿名用户处理）
    - 没带 token 且非 dev → 抛 AuthError（上层 close 连接）
    - 带了但无效 → 抛 AuthError
    """
    if not token:
        if _is_dev_mode():
            return None
        raise AuthError("missing token")
    return decode_token(token)


__all__ = [
    "decode_ws_token",
    "optional_user",
    "require_scope",
    "require_user",
]
