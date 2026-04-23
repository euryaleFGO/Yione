"""租户/API Key 管理（M6 最小版）。

Phase 2 的 M7 会迁到 Mongo。这里用 JSON 文件做最小持久化：

    backend/app/data/tenants.json
    {
      "tenants": [
        {
          "id": "demo",
          "api_key_hash": "<sha256>",
          "allowed_origins": ["http://localhost:5173", "https://example.com"],
          "character_whitelist": ["ling"],
          "daily_quota": 2000,
          "scope": ["chat", "embed"]
        }
      ]
    }

敏感信息都存 hash（``api_key_hash``）；明文 api key 只在 tenant 创建/展示时
短暂出现，不入盘。

开发流程（Phase 2 前）：手动新建/维护 tenants.json 文件即可；没这个文件时
服务进 dev 模式，认任何"demo" key 通过，方便本地联调。
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import BACKEND_ROOT

logger = logging.getLogger(__name__)


DEFAULT_TENANTS_PATH = BACKEND_ROOT / "app" / "data" / "tenants.json"


@dataclass(slots=True)
class Tenant:
    id: str
    api_key_hash: str
    allowed_origins: list[str] = field(default_factory=list)
    character_whitelist: list[str] = field(default_factory=list)
    daily_quota: int = 2000
    scope: list[str] = field(default_factory=lambda: ["chat", "embed"])

    def origin_allowed(self, origin: str | None) -> bool:
        if not self.allowed_origins or self.allowed_origins == ["*"]:
            return True
        return origin in self.allowed_origins if origin else False

    def character_allowed(self, character_id: str) -> bool:
        if not self.character_whitelist:
            return True
        return character_id in self.character_whitelist


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


class TenantService:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_TENANTS_PATH
        self._tenants: dict[str, Tenant] = {}
        self._dev_fallback = False
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            logger.warning(
                "tenants.json 未找到（%s），TenantService 进 dev 回退模式：任意 api_key 通过，"
                "tenant_id 固定为 'demo'；生产环境务必创建 tenants.json 并关掉 dev 环境。",
                self._path,
            )
            self._dev_fallback = True
            return

        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("tenants.json 解析失败: %s", exc)
            self._dev_fallback = True
            return

        for item in raw.get("tenants", []):
            try:
                t = Tenant(
                    id=item["id"],
                    api_key_hash=item["api_key_hash"],
                    allowed_origins=list(item.get("allowed_origins", [])),
                    character_whitelist=list(item.get("character_whitelist", [])),
                    daily_quota=int(item.get("daily_quota", 2000)),
                    scope=list(item.get("scope", ["chat", "embed"])),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.error("tenant 条目无效: %s (%s)", item, exc)
                continue
            self._tenants[t.id] = t
        logger.info("加载到 %d 个 tenant", len(self._tenants))

    def verify_api_key(self, api_key: str) -> Tenant | None:
        """比对 api_key 的 sha256 hash 找到对应的 Tenant。

        dev fallback 模式下永远返回一个内置 demo tenant，方便本地联调。
        """
        if not api_key:
            return None
        if self._dev_fallback:
            return Tenant(
                id="demo",
                api_key_hash=_hash_key(api_key),
                allowed_origins=[],
                character_whitelist=[],
                daily_quota=2000,
                scope=["chat", "embed"],
            )
        digest = _hash_key(api_key)
        for t in self._tenants.values():
            if t.api_key_hash == digest:
                return t
        return None


_singleton: TenantService | None = None


def get_tenant_service() -> TenantService:
    global _singleton
    if _singleton is None:
        _singleton = TenantService()
    return _singleton


__all__ = ["Tenant", "TenantService", "_hash_key", "get_tenant_service"]
