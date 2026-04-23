"""MongoDB 连接管理（M7）。

使用 motor 异步驱动连接 MongoDB，app.state.db 挂在 FastAPI 上。
无 Mongo 时自动降级到 dev fallback（db=None）。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)


async def init_db(app: FastAPI) -> None:
    """启动时连接 MongoDB，失败则降级到 dev fallback。"""
    settings = get_settings()
    try:
        client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        app.state.mongo_client = client
        app.state.db = client[settings.mongo_db]
        logger.info("MongoDB 已连接: %s/%s", settings.mongo_uri, settings.mongo_db)
    except Exception as exc:
        logger.warning("MongoDB 连接失败，进入 dev fallback 模式: %s", exc)
        app.state.mongo_client = None
        app.state.db = None


async def close_db(app: FastAPI) -> None:
    """关闭时断开 MongoDB 连接。"""
    client: AsyncIOMotorClient | None = getattr(app.state, "mongo_client", None)
    if client is not None:
        client.close()
        logger.info("MongoDB 连接已关闭")


def get_db(app: FastAPI) -> AsyncIOMotorDatabase | None:
    """获取数据库实例，无连接时返回 None。"""
    return getattr(app.state, "db", None)
