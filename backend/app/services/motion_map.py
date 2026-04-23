"""情绪 → Live2D motion group 映射（M5）。

目前只服务于 Hiyori 形象（`apps/web/public/avatars/hiyori/hiyori_free_t08.model3.json`），
model3 文件里定义的 motion 分组如下：

  Idle / Flick / FlickDown / Tap / Tap@Body / Flick@Body

Phase 2 的 M7 会把每个 Character 的 motionMap 存到 Mongo，前端按 character_id 动态
加载。当前只有"玲"一个形象，先走字典常量就够。
"""

from __future__ import annotations

from app.schemas.ws import Emotion

# 情绪 → motion group（Hiyori）
HIYORI_MOTION_MAP: dict[Emotion, str] = {
    "neutral": "Idle",
    "joy": "Tap@Body",
    "sadness": "FlickDown",
    "anger": "Flick",
    "fear": "FlickDown",
    "surprise": "Tap",
    "disgust": "Flick",
    "affection": "Tap@Body",
}


def motion_for(emotion: Emotion, character_id: str = "ling") -> str:
    """返回指定情绪对应的 motion group 名。

    character_id 暂时不起作用（只有 Hiyori）；保留参数是为了 M7 无痛扩展到多形象。
    """
    del character_id  # 预留
    return HIYORI_MOTION_MAP.get(emotion, "Idle")


__all__ = ["HIYORI_MOTION_MAP", "motion_for"]
