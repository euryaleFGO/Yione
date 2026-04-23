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

# 情绪 → expression 名（Hiyori `expressions/*.exp3.json`）
# 与 motion 是独立系统：motion 是身体动作（.motion3.json），expression 是面部参数
# 覆盖（.exp3.json）。两者可同时作用在模型上互不干扰。
HIYORI_EXPRESSION_MAP: dict[Emotion, str] = {
    "neutral": "neutral",
    "joy": "joy",
    "sadness": "sadness",
    "anger": "anger",
    "fear": "fear",
    "surprise": "surprise",
    "disgust": "disgust",
    "affection": "affection",
}


def motion_for(emotion: Emotion, character_id: str = "ling") -> str:
    """返回指定情绪对应的 motion group 名。

    character_id 暂时不起作用（只有 Hiyori）；保留参数是为了 M7 无痛扩展到多形象。
    """
    del character_id  # 预留
    return HIYORI_MOTION_MAP.get(emotion, "Idle")


def expression_for(emotion: Emotion, character_id: str = "ling") -> str:
    """情绪 → expression 名；对齐 model3.json 里 Expressions 的 Name 字段。"""
    del character_id  # 预留 M7
    return HIYORI_EXPRESSION_MAP.get(emotion, "neutral")


__all__ = [
    "HIYORI_EXPRESSION_MAP",
    "HIYORI_MOTION_MAP",
    "expression_for",
    "motion_for",
]
