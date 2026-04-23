"""MongoDB Tenant Repository（M7）。

启动时从 MongoDB 加载 tenants 到内存缓存，同步查询走缓存。
无 Mongo 时降级到 dev fallback（任意 key 通过）。
"""

from __future__ import annotations

import hashlib
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.tenant_service import Tenant

logger = logging.getLogger(__name__)


class MongoTenantRepo:
    def __init__(self, db: AsyncIOMotorDatabase | None) -> None:
        self._db = db
        self._cache: dict[str, Tenant] = {}
        self._dev_fallback = db is None

    async def load_all(self) -> None:
        """启动时从 MongoDB 加载所有 tenants 到内存缓存。"""
        if self._db is None:
            return
        cursor = self._db.tenants.find()
        docs = await cursor.to_list(length=1000)
        self._cache = {}
        for doc in docs:
            doc.pop("_id", None)
            try:
                t = Tenant(**doc)
                self._cache[t.id] = t
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("tenant 文档无效: %s (%s)", doc, exc)
        logger.info("从 MongoDB 加载 %d 个 tenant", len(self._cache))

    def verify_api_key(self, api_key: str) -> Tenant | None:
        """同步查询，走内存缓存。"""
        if not api_key:
            return None
        if self._dev_fallback:
            return Tenant(
                id="demo",
                api_key_hash=hashlib.sha256(api_key.encode("utf-8")).hexdigest(),
                allowed_origins=[],
                character_whitelist=[],
                daily_quota=2000,
                scope=["chat", "embed"],
            )
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        for t in self._cache.values():
            if t.api_key_hash == digest:
                return t
        return None
