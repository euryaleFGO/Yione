"""Speaker 领域对象（M16）。

domain 层只承载数据 + 纯计算逻辑；具体存储（JSON 文件 / Mongo）放 repositories
下面。这样未来 M7 把 speakers 表迁到 Mongo 时只换 repo，service 层不动。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.schemas.speaker import SpeakerInfo, SpeakerProfile


@dataclass(slots=True)
class Speaker:
    """内部领域对象，持有 voiceprint 明文向量。"""

    id: str
    name: str | None
    voiceprint: list[float]
    profile: SpeakerProfile
    enrolled_samples: int
    created_at: datetime
    updated_at: datetime

    @property
    def dim(self) -> int:
        return len(self.voiceprint)

    def to_info(self) -> SpeakerInfo:
        """去掉 voiceprint，转成对前端可见的形状。"""
        return SpeakerInfo(
            id=self.id,
            name=self.name,
            profile=self.profile,
            enrolled_samples=self.enrolled_samples,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def merge_voiceprint(self, other: list[float]) -> None:
        """新增样本时走加权平均再重归一化，避免 voiceprint 抖动。"""
        if len(other) != len(self.voiceprint):
            raise ValueError(
                f"voiceprint 维度不一致: 现存 {len(self.voiceprint)} vs 新样本 {len(other)}"
            )
        n = self.enrolled_samples
        merged = [
            (self.voiceprint[i] * n + other[i]) / (n + 1) for i in range(len(other))
        ]
        norm = sum(v * v for v in merged) ** 0.5
        if norm > 0:
            merged = [v / norm for v in merged]
        self.voiceprint = merged
        self.enrolled_samples = n + 1
        self.updated_at = datetime.now(tz=UTC)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """两个向量的点积。CampPlus 输出已 L2 归一化，点积即余弦相似度。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True))


def new_speaker(
    *,
    speaker_id: str,
    voiceprint: list[float],
    name: str | None = None,
) -> Speaker:
    now = datetime.now(tz=UTC)
    return Speaker(
        id=speaker_id,
        name=name,
        voiceprint=voiceprint,
        profile=SpeakerProfile(),
        enrolled_samples=1,
        created_at=now,
        updated_at=now,
    )


__all__ = ["Speaker", "cosine_similarity", "new_speaker"]


# 保留 field 占位导入以便将来扩展 Speaker 默认工厂字段不引 ruff
_ = field
