"""事件总线（M24）。

简单的发布/订阅事件系统，支持定时事件。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """简单的异步事件总线。"""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._running = False

    def on(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器。"""
        self._handlers.setdefault(event_type, []).append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """移除事件处理器。"""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event_type: str, **kwargs: Any) -> None:
        """触发事件。"""
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(**kwargs)
            except Exception:
                logger.exception("Event handler error: %s", event_type)

    async def start(self) -> None:
        """启动定时事件循环。"""
        self._running = True
        asyncio.create_task(self._tick_loop())
        logger.info("EventBus started")

    async def stop(self) -> None:
        """停止事件循环。"""
        self._running = False
        logger.info("EventBus stopped")

    async def _tick_loop(self) -> None:
        """每分钟检查定时事件。"""
        while self._running:
            now = datetime.now(tz=UTC)
            hour, minute = now.hour, now.minute

            # 早安事件：每天 8:00
            if hour == 8 and minute == 0:
                await self.emit("daily_greeting", greeting="早安")

            # 晚安事件：每天 22:00
            if hour == 22 and minute == 0:
                await self.emit("daily_greeting", greeting="晚安")

            await asyncio.sleep(60)


# 全局单例
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
