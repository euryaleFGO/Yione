"""In-memory session store (M1).

M7 replaces this with a Mongo-backed repository.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.schemas.chat import SessionInfo

_DEFAULT_GREETING = "你好呀，我是玲。很高兴见到你。"


class SessionService:
    def __init__(self) -> None:
        self._store: dict[str, SessionInfo] = {}

    def create(self, character_id: str, user_ref: str | None) -> SessionInfo:
        sid = f"sess_{uuid.uuid4().hex[:12]}"
        info = SessionInfo(
            session_id=sid,
            character_id=character_id,
            user_ref=user_ref,
            greeting=_DEFAULT_GREETING,
            created_at=datetime.now(tz=UTC),
        )
        self._store[sid] = info
        return info

    def get(self, session_id: str) -> SessionInfo | None:
        return self._store.get(session_id)


_singleton: SessionService | None = None


def get_session_service() -> SessionService:
    global _singleton
    if _singleton is None:
        _singleton = SessionService()
    return _singleton
