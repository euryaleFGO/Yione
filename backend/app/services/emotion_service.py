"""情绪检测服务（M5）。

轻量实现：
- 支持 LLM 用内联标签显式声明情绪，例如 `[joy]好呀！` / `[anger]吵死了`。
- 没有标签时退回关键词匹配，命中任一关键词即返回对应情绪。
- 都没命中则返回 ``neutral``。

Phase 4 会引入真正的分类模型（复用 Ling 的 emotion_classifier），但在 Phase 1
的目标只是把"字幕 → 情绪 → 动作"链路打通，规则版已经够用。
"""

from __future__ import annotations

import re
from typing import Literal

from app.schemas.ws import Emotion

# 所有合法 Emotion 枚举值（排除 neutral，用来匹配标签）
_TAG_EMOTIONS: frozenset[str] = frozenset(
    {"joy", "sadness", "anger", "fear", "surprise", "disgust", "affection"}
)

# 形如 `[joy]`、`[affection]` 的完整标签；只识别 ASCII 小写单词
_TAG_RE = re.compile(r"\[([a-zA-Z_]+)\]")

# 用来剥掉结尾残留的不完整标签（例如分片尚未到达的 `[jo`），避免字幕短暂显示尖括号
_TRAILING_INCOMPLETE_RE = re.compile(r"\[[a-zA-Z_]*$")


_KEYWORDS: dict[Emotion, tuple[str, ...]] = {
    "joy": (
        "哈哈", "嘻嘻", "真棒", "太好了", "好呀", "好的呀", "开心", "棒极了", "有意思",
        "嘿嘿", "高兴", "愉快", "满意", "快乐", "欢喜", "yay", "nice", "great",
    ),
    "sadness": (
        "难过", "伤心", "抱歉", "对不起", "遗憾", "呜呜", "沉沉", "沉重", "失落",
        "委屈", "心疼", "无奈", "唉", "叹气", "可怜", "sorry",
    ),
    "anger": (
        "讨厌", "生气", "气死", "烦死", "别吵", "闭嘴", "不爽", "火大", "可恶",
    ),
    "fear": (
        "害怕", "好可怕", "别吓", "恐怖", "吓人", "担心", "紧张",
    ),
    "surprise": (
        "真的吗", "诶？", "咦", "哇", "哎呀", "天哪", "没想到", "竟然", "居然", "wow",
    ),
    "disgust": (
        "恶心", "呸", "难吃", "难闻", "讨人厌",
    ),
    "affection": (
        "喜欢你", "爱你", "抱抱", "乖乖", "最喜欢", "温柔", "暖心", "贴心", "疼你",
        "想你", "亲亲", "mua",
    ),
}


def _keyword_match(text: str) -> Emotion:
    """基于关键词猜测情绪，全部找不到返回 neutral。"""
    lowered = text.lower()
    for emo, words in _KEYWORDS.items():
        for w in words:
            if w in lowered:
                return emo
    return "neutral"


def detect(text: str) -> Emotion:
    """从一段文本识别情绪。

    - 文本里若有任何 `[xxx]` 合法情绪标签，取最后一个出现的（LLM 允许中途转情绪）
    - 否则回退到关键词规则
    """
    last_tag: str | None = None
    for m in _TAG_RE.finditer(text):
        tag = m.group(1).lower()
        if tag in _TAG_EMOTIONS:
            last_tag = tag
    if last_tag is not None:
        return last_tag  # type: ignore[return-value]
    return _keyword_match(text)


def strip_emotion_tags(raw: str) -> tuple[str, Emotion | Literal["neutral"] | None]:
    """剥掉 raw 中的 `[xxx]` 标签，返回 (清洗后的文本, 最后一次合法情绪 tag)。

    - 只会匹配完整 `[word]`；结尾未闭合的 `[jo` 之类会被临时从 clean 结果里摘掉，
      等待下一次带闭合的 chunk 到来时再整体处理（配合逐 chunk 调用是稳态的）。
    - 返回值第二项为 None 表示整段没见过任何合法情绪 tag。
    """
    last_tag: Emotion | None = None
    collected: list[str] = []
    idx = 0
    for m in _TAG_RE.finditer(raw):
        collected.append(raw[idx : m.start()])
        idx = m.end()
        tag = m.group(1).lower()
        if tag in _TAG_EMOTIONS:
            last_tag = tag  # type: ignore[assignment]
    collected.append(raw[idx:])
    clean = "".join(collected)

    # 尾巴上若残留未闭合标签（例如分片尚未补齐），先临时去掉，后续 chunk 会重新拼回
    incomplete = _TRAILING_INCOMPLETE_RE.search(clean)
    if incomplete is not None:
        clean = clean[: incomplete.start()]
    return clean, last_tag


__all__ = ["detect", "strip_emotion_tags"]
