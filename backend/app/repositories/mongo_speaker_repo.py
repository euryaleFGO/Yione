"""MongoDB Speaker Repository（M7）。

启动时从 MongoDB 加载 speakers 到内存，同步查询走缓存。
写操作同时更新内存和 MongoDB（fire-and-forget）。
无 Mongo 时降级到 JsonFileSpeakerRepo。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.speaker import Speaker
from app.repositories.speaker_repo import JsonFileSpeakerRepo, _speaker_from_dict, _speaker_to_dict
from app.schemas.speaker import SpeakerProfile

logger = logging.getLogger(__name__)


class MongoSpeakerRepo:
    def __init__(self, db: AsyncIOMotorDatabase | None, fallback_path: Path | None = None) -> None:
        self._db = db
        self._cache: dict[str, Speaker] = {}
        if db is None:
            self._fallback = JsonFileSpeakerRepo(path=fallback_path)
        else:
            self._fallback = None

    async def load_all(self) -> None:
        """启动时从 MongoDB 加载所有 speakers 到内存缓存。"""
        if self._fallback is not None:
            return
        cursor = self._db.speakers.find()
        docs = await cursor.to_list(length=1000)
        self._cache = {}
        for doc in docs:
            doc.pop("_id", None)
            try:
                spk = _speaker_from_dict(doc)
                self._cache[spk.id] = spk
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("speaker 文档无效: %s (%s)", doc, exc)
        logger.info("从 MongoDB 加载 %d 个 speaker", len(self._cache))

    # ---- 同步接口（兼容 SpeakerService） ----

    def list_all(self) -> list[Speaker]:
        if self._fallback is not None:
            return self._fallback.list_all()
        return list(self._cache.values())

    def get(self, speaker_id: str) -> Speaker | None:
        if self._fallback is not None:
            return self._fallback.get(speaker_id)
        return self._cache.get(speaker_id)

    def save(self, speaker: Speaker) -> None:
        if self._fallback is not None:
            self._fallback.save(speaker)
            return
        self._cache[speaker.id] = speaker
        self._fire_and_forget(self._save_to_mongo(speaker))

    def delete(self, speaker_id: str) -> bool:
        if self._fallback is not None:
            return self._fallback.delete(speaker_id)
        removed = self._cache.pop(speaker_id, None)
        if removed is None:
            return False
        self._fire_and_forget(self._delete_from_mongo(speaker_id))
        return True

    # ---- 内部 ----

    async def _save_to_mongo(self, speaker: Speaker) -> None:
        doc = _speaker_to_dict(speaker)
        await self._db.speakers.update_one(
            {"id": speaker.id},
            {"$set": doc},
            upsert=True,
        )

    async def _delete_from_mongo(self, speaker_id: str) -> None:
        await self._db.speakers.delete_one({"id": speaker_id})

    @staticmethod
    def _fire_and_forget(coro) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)
