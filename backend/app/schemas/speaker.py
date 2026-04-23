"""Speaker / 声纹相关的 pydantic schemas（M16）。

Phase 4 的声纹识别只用到这几类载荷：
- API 创建/查询时前端看到的 SpeakerInfo（不包含原始 voiceprint 向量，避免
  数十 KB 级的无用数据在 JSON 里来回）
- identify 结果（匹配到 + 未匹配两种情况）
- 自动注册时返回的 is_new 标志

原始 voiceprint（float32 向量）只在服务端 / 存储层流转。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SpeakerProfile(BaseModel):
    """关于说话人的软信息，LLM 做上下文注入时会读这里。"""

    relationship: str | None = None  # 比如 "friend" / "family"
    nickname: str | None = None
    preferences: dict[str, str] = Field(default_factory=dict)
    notes: str | None = None


class SpeakerInfo(BaseModel):
    """对外暴露的说话人记录；不包含 voiceprint 向量本身。"""

    id: str
    name: str | None = None
    profile: SpeakerProfile = Field(default_factory=SpeakerProfile)
    enrolled_samples: int = 1
    created_at: datetime
    updated_at: datetime


class SpeakerRegisterResponse(BaseModel):
    speaker: SpeakerInfo
    embedding_dim: int


class SpeakerIdentifyRequest(BaseModel):
    """identify 的可选元数据，一般通过 multipart form 表单字段传。"""

    session_id: str | None = None
    auto_enroll: bool = False
    # 命中阈值：None 表示用服务端默认值（0.38，对齐 Ling SVEngine）
    threshold: float | None = None


class SpeakerIdentifyResult(BaseModel):
    matched: bool
    score: float
    threshold: float
    speaker: SpeakerInfo | None = None
    # 若 auto_enroll=True 且未命中现有库，会自动注册一个新说话人；is_new=True
    is_new: bool = False
    # 引擎不可用时走降级路径，前端能据此展示合适提示
    engine_available: bool = True


class SpeakerPatch(BaseModel):
    """PATCH /api/speakers/{id} 只允许改软信息，不动 voiceprint。"""

    name: str | None = None
    profile: SpeakerProfile | None = None


__all__ = [
    "SpeakerIdentifyRequest",
    "SpeakerIdentifyResult",
    "SpeakerInfo",
    "SpeakerPatch",
    "SpeakerProfile",
    "SpeakerRegisterResponse",
]
