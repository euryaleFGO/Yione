"""自主循环（M25）。

autonomy_service.tick() 定期运行，管理目标和主动对话。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class Goal:
    id: str
    description: str
    priority: int = 0
    done: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class AutonomyService:
    """自主循环：定期检查目标并主动发起对话。"""

    def __init__(self) -> None:
        self._goals: list[Goal] = []
        self._running = False

    def add_goal(self, goal_id: str, description: str, priority: int = 0) -> Goal:
        goal = Goal(id=goal_id, description=description, priority=priority)
        self._goals.append(goal)
        logger.info("添加目标: %s - %s", goal_id, description)
        return goal

    def complete_goal(self, goal_id: str) -> bool:
        for g in self._goals:
            if g.id == goal_id:
                g.done = True
                logger.info("完成目标: %s", goal_id)
                return True
        return False

    def list_goals(self, pending_only: bool = True) -> list[Goal]:
        if pending_only:
            return [g for g in self._goals if not g.done]
        return self._goals.copy()

    async def tick(self) -> None:
        """自主循环 tick：检查目标，决定是否主动对话。"""
        pending = self.list_goals(pending_only=True)
        if not pending:
            return
        # 按优先级排序
        pending.sort(key=lambda g: g.priority, reverse=True)
        top = pending[0]
        logger.info("自主循环 tick: 最高优先级目标 %s - %s", top.id, top.description)

    async def start(self, interval: float = 10.0) -> None:
        """启动自主循环，每 interval 秒 tick 一次。"""
        self._running = True
        logger.info("自主循环启动，间隔 %ss", interval)
        while self._running:
            await self.tick()
            await asyncio.sleep(interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("自主循环停止")


# 全局单例
_autonomy: AutonomyService | None = None


def get_autonomy_service() -> AutonomyService:
    global _autonomy
    if _autonomy is None:
        _autonomy = AutonomyService()
    return _autonomy
