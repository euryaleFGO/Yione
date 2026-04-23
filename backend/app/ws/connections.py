"""活动 WebSocket 连接的进程内 registry（M16）。

chat_ws 握手成功时 register、断开时 unregister。非 WS 模块（比如 speakers
router）需要把事件推给某个 session 时，通过这里拿到 WebSocket 再 send_json。

单进程假设：webLing 现在就一个 FastAPI worker。多 worker 部署留给 M14 的
可观测 + Redis pub/sub 方案，不是本里程碑范围。
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

from app.schemas.ws import ServerEvent

logger = logging.getLogger(__name__)


class WsConnectionRegistry:
    def __init__(self) -> None:
        self._conns: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(self, session_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._conns[session_id] = ws

    async def unregister(self, session_id: str, ws: WebSocket) -> None:
        """只有当注册的那个还是同一条连接时才移除，防止误清了新连接。"""
        async with self._lock:
            if self._conns.get(session_id) is ws:
                self._conns.pop(session_id, None)

    def get(self, session_id: str) -> WebSocket | None:
        return self._conns.get(session_id)

    async def send(self, session_id: str, event: ServerEvent) -> bool:
        """返回是否成功发出；没找到连接或发送失败都返回 False，不抛。"""
        ws = self._conns.get(session_id)
        if ws is None:
            return False
        try:
            await ws.send_json(event.model_dump(mode="json"))
            return True
        except Exception as exc:  # 网络 / 连接状态异常
            logger.debug("broadcaster.send 失败: %s", exc)
            return False

    def session_ids(self) -> list[str]:
        return list(self._conns.keys())


_singleton: WsConnectionRegistry | None = None


def get_ws_registry() -> WsConnectionRegistry:
    global _singleton
    if _singleton is None:
        _singleton = WsConnectionRegistry()
    return _singleton


__all__ = ["WsConnectionRegistry", "get_ws_registry"]
