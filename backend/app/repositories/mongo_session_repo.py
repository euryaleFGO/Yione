"""MongoDB Session Repository（M7）。

替代内存 dict，数据持久化到 MongoDB sessions 集合。
无 Mongo 时降级到内存模式。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.chat import SessionInfo

logger = logging.getLogger(__name__)


class MongoSessionRepo:
    def __init__(self, db: AsyncIOMotorDatabase | None) -> None:
        self._db = db
        self._fallback: dict[str, SessionInfo] = {}

    async def create(self, session: SessionInfo) -> SessionInfo:
        if self._db is None:
            self._fallback[session.session_id] = session
            return session
        doc = session.model_dump(mode="json")
        await self._db.sessions.insert_one(doc)
        return session

    async def get(self, session_id: str) -> SessionInfo | None:
        if self._db is None:
            return self._fallback.get(session_id)
        doc = await self._db.sessions.find_one({"session_id": session_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return SessionInfo.model_validate(doc)
