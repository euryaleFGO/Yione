"""情绪-动作联动（M27）。

情感状态驱动 Live2D 动作选择。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 情绪 → Live2D motion group 映射
EMOTION_MOTION_MAP = {
    "joy": "Tap@Body",
    "sadness": "FlickDown",
    "anger": "Flick",
    "fear": "Tap@Body",
    "surprise": "Tap@Head",
    "disgust": "Flick",
    "affection": "Tap@Body",
    "neutral": None,
}


def motion_for_emotion(emotion: str) -> str | None:
    """根据情感返回 Live2D motion group 名。"""
    return EMOTION_MOTION_MAP.get(emotion)
