"""Session 存储（M1 内存 → M7 MongoDB）。

M7 升级：优先使用 MongoSessionRepo，无 Mongo 时降级到内存模式。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.schemas.chat import SessionInfo

_DEFAULT_GREETING = "你好呀，我是玲。很高兴见到你。"


class SessionService:
    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._fallback: dict[str, SessionInfo] = {}

    async def create(self, character_id: str, user_ref: str | None) -> SessionInfo:
        sid = f"sess_{uuid.uuid4().hex[:12]}"
        info = SessionInfo(
            session_id=sid,
            character_id=character_id,
            user_ref=user_ref,
            greeting=_DEFAULT_GREETING,
            created_at=datetime.now(tz=UTC),
        )
        if self._repo is not None:
            return await self._repo.create(info)
        self._fallback[sid] = info
        return info

    async def get(self, session_id: str) -> SessionInfo | None:
        if self._repo is not None:
            return await self._repo.get(session_id)
        return self._fallback.get(session_id)

    async def list_all(self) -> list[SessionInfo]:
        if self._repo is not None:
            return await self._repo.list_all()
        return list(self._fallback.values())


_singleton: SessionService | None = None


def get_session_service() -> SessionService:
    global _singleton
    if _singleton is None:
        _singleton = SessionService()
    return _singleton


def set_session_service(svc: SessionService | None) -> None:
    global _singleton
    _singleton = svc
