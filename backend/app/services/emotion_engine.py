"""情感引擎（M22）。

EmotionState 8 维模型：joy, sadness, anger, fear, surprise, disgust, affection, neutral。
支持触发器、衰减、注入 system prompt。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 8 维情感向量
EMOTION_DIMS = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "affection", "neutral"]


@dataclass
class EmotionState:
    """情感状态：8 维向量，每维 0-1。"""

    joy: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    affection: float = 0.0
    neutral: float = 1.0  # 默认中性

    updated_at: float = field(default_factory=time.time)

    def dominant(self) -> str:
        """返回最强烈的情感维度。"""
        vals = {d: getattr(self, d) for d in EMOTION_DIMS if d != "neutral"}
        return max(vals, key=vals.get) if max(vals.values()) > 0.1 else "neutral"

    def decay(self, rate: float = 0.05) -> None:
        """情感衰减：每调用一次，非中性维度衰减 rate。"""
        for d in EMOTION_DIMS:
            if d == "neutral":
                continue
            val = getattr(self, d)
            if val > 0:
                setattr(self, d, max(0, val - rate))
        # neutral 补偿
        total = sum(getattr(self, d) for d in EMOTION_DIMS if d != "neutral")
        self.neutral = max(0, 1.0 - total)
        self.updated_at = time.time()

    def trigger(self, emotion: str, intensity: float = 0.3) -> None:
        """触发情感变化。"""
        if emotion not in EMOTION_DIMS:
            return
        current = getattr(self, emotion)
        setattr(self, emotion, min(1.0, current + intensity))
        # neutral 补偿
        total = sum(getattr(self, d) for d in EMOTION_DIMS if d != "neutral")
        self.neutral = max(0, 1.0 - total)
        self.updated_at = time.time()

    def to_prompt(self) -> str:
        """注入 system prompt 的情感描述。"""
        dominant = self.dominant()
        if dominant == "neutral":
            return ""
        return f"当前情感状态：{dominant}（强度 {getattr(self, dominant):.1f}）"

    def to_dict(self) -> dict:
        return {d: getattr(self, d) for d in EMOTION_DIMS}


# 全局单例
_emotion_state: EmotionState | None = None


def get_emotion_state() -> EmotionState:
    global _emotion_state
    if _emotion_state is None:
        _emotion_state = EmotionState()
    return _emotion_state


# 情感关键词触发器
EMOTION_TRIGGERS = {
    "joy": ["开心", "高兴", "快乐", "太好了", "哈哈", "嘻嘻"],
    "sadness": ["难过", "伤心", "可惜", "遗憾", "唉"],
    "anger": ["生气", "愤怒", "烦死了", "讨厌"],
    "fear": ["害怕", "恐惧", "担心", "可怕"],
    "surprise": ["惊讶", "哇", "天啊", "没想到"],
    "disgust": ["恶心", "讨厌", "受不了"],
    "affection": ["喜欢", "爱你", "亲爱的", "想你"],
}


def detect_emotion(text: str) -> str:
    """从文本中检测情感。"""
    for emotion, keywords in EMOTION_TRIGGERS.items():
        for kw in keywords:
            if kw in text:
                return emotion
    return "neutral"
