"""Speaker 持久化层（M16）。

接口是个 ``Protocol``，方便 M7 把 Mongo impl 插进来而不改 service。当前默认实现
是 JSON 文件（和 tenant_service 同一套思路），读写走互斥锁保证多请求下不撕裂。

文件位置：``backend/app/data/speakers.json``，已 gitignore（声纹向量算敏感
信息，不入库）。JSON 结构：

    {
      "speakers": [
        {
          "id": "spk_xxx",
          "name": "...",
          "voiceprint": [... floats ...],
          "profile": { "relationship": ..., ... },
          "enrolled_samples": 3,
          "created_at": "ISO8601",
          "updated_at": "ISO8601"
        }
      ]
    }
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.config import BACKEND_ROOT
from app.domain.speaker import Speaker
from app.schemas.speaker import SpeakerProfile

logger = logging.getLogger(__name__)


DEFAULT_PATH = BACKEND_ROOT / "app" / "data" / "speakers.json"


class SpeakerRepository(Protocol):
    def list_all(self) -> list[Speaker]: ...
    def get(self, speaker_id: str) -> Speaker | None: ...
    def save(self, speaker: Speaker) -> None: ...
    def delete(self, speaker_id: str) -> bool: ...


class JsonFileSpeakerRepo:
    """最小持久化：读写一个 JSON 文件，每次写入重写全量。

    Phase 2 的 M7 会换成 MongoSpeakerRepo（pymongo / motor）。目前 speakers
    数量肯定是个位数到两位数，单文件足够。
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_PATH
        self._lock = threading.Lock()
        self._cache: dict[str, Speaker] | None = None

    # ---- Protocol ----

    def list_all(self) -> list[Speaker]:
        cache = self._load()
        return list(cache.values())

    def get(self, speaker_id: str) -> Speaker | None:
        return self._load().get(speaker_id)

    def save(self, speaker: Speaker) -> None:
        with self._lock:
            cache = self._load_locked()
            cache[speaker.id] = speaker
            self._flush_locked(cache)

    def delete(self, speaker_id: str) -> bool:
        with self._lock:
            cache = self._load_locked()
            if speaker_id not in cache:
                return False
            cache.pop(speaker_id)
            self._flush_locked(cache)
            return True

    # ---- 内部 ----

    def _load(self) -> dict[str, Speaker]:
        with self._lock:
            return self._load_locked().copy()

    def _load_locked(self) -> dict[str, Speaker]:
        if self._cache is not None:
            return self._cache
        self._cache = {}
        if not self._path.exists():
            return self._cache
        try:
            raw = json.loads(self._path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("speakers.json 解析失败: %s", exc)
            return self._cache
        for item in raw.get("speakers", []):
            try:
                spk = _speaker_from_dict(item)
            except (KeyError, TypeError, ValueError) as exc:
                logger.error("speaker 条目无效: %s (%s)", item.get("id"), exc)
                continue
            self._cache[spk.id] = spk
        return self._cache

    def _flush_locked(self, cache: dict[str, Speaker]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"speakers": [_speaker_to_dict(s) for s in cache.values()]}
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self._path)


def _speaker_from_dict(item: dict) -> Speaker:
    return Speaker(
        id=item["id"],
        name=item.get("name"),
        voiceprint=[float(x) for x in item["voiceprint"]],
        profile=SpeakerProfile.model_validate(item.get("profile") or {}),
        enrolled_samples=int(item.get("enrolled_samples", 1)),
        created_at=_parse_dt(item["created_at"]),
        updated_at=_parse_dt(item["updated_at"]),
    )


def _speaker_to_dict(s: Speaker) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "voiceprint": s.voiceprint,
        "profile": s.profile.model_dump(mode="json"),
        "enrolled_samples": s.enrolled_samples,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _parse_dt(raw: str) -> datetime:
    # 3.11+ 的 fromisoformat 可以吃 "Z" 结尾；保险起见手动替换
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


_singleton: JsonFileSpeakerRepo | None = None


def get_speaker_repo() -> JsonFileSpeakerRepo:
    global _singleton
    if _singleton is None:
        _singleton = JsonFileSpeakerRepo()
    return _singleton


def set_speaker_repo_for_tests(repo: JsonFileSpeakerRepo | None) -> None:
    global _singleton
    _singleton = repo


__all__ = [
    "JsonFileSpeakerRepo",
    "SpeakerRepository",
    "get_speaker_repo",
    "set_speaker_repo_for_tests",
]
