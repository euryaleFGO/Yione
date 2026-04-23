"""M5 情绪服务单测：标签识别、关键词回退、tag 剥离的边界情况。"""

from __future__ import annotations

from app.services import emotion_service


def test_detect_returns_neutral_on_empty() -> None:
    assert emotion_service.detect("") == "neutral"
    assert emotion_service.detect("   ") == "neutral"


def test_detect_parses_explicit_tag() -> None:
    assert emotion_service.detect("[joy]好的呀") == "joy"
    assert emotion_service.detect("前面说一下[anger]吵死了") == "anger"


def test_detect_last_tag_wins_when_multiple() -> None:
    # LLM 中途换情绪时以最后一个标签为准
    assert emotion_service.detect("[joy]开心[sadness]后来伤心") == "sadness"


def test_detect_ignores_unknown_tag() -> None:
    assert emotion_service.detect("[foo]随便") == "neutral"


def test_detect_keyword_fallback() -> None:
    assert emotion_service.detect("哈哈真棒") == "joy"
    assert emotion_service.detect("我有点难过") == "sadness"
    assert emotion_service.detect("讨厌啦你") == "anger"


def test_detect_no_match_returns_neutral() -> None:
    assert emotion_service.detect("今天天气如何") == "neutral"


def test_strip_tags_complete() -> None:
    clean, tag = emotion_service.strip_emotion_tags("[joy]好的呀")
    assert clean == "好的呀"
    assert tag == "joy"


def test_strip_tags_multiple_keeps_last() -> None:
    clean, tag = emotion_service.strip_emotion_tags("[joy]开心[sadness]伤心")
    assert clean == "开心伤心"
    assert tag == "sadness"


def test_strip_tags_trailing_incomplete_is_deferred() -> None:
    # 半个标签（LLM 分片尚未到达闭合 `]`）不应该出现在清洗文本里
    clean, tag = emotion_service.strip_emotion_tags("好的[jo")
    assert clean == "好的"
    assert tag is None


def test_strip_tags_incomplete_then_complete_across_calls() -> None:
    # 模拟逐 chunk 累加：清洗后文本始终单调增长
    raw = ""
    prev_clean = ""
    for chunk in ["[jo", "y]好", "的"]:
        raw += chunk
        clean, _ = emotion_service.strip_emotion_tags(raw)
        assert clean.startswith(prev_clean)  # 新 clean 以旧 clean 开头
        prev_clean = clean
    assert prev_clean == "好的"


def test_strip_tags_ignores_unknown_tags() -> None:
    # 未知标签依然会被当作 tag 结构剥掉，但不会改 emotion
    clean, tag = emotion_service.strip_emotion_tags("[foo]你好")
    assert clean == "你好"
    assert tag is None
