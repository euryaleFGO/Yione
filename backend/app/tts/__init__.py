"""TTS Provider 工厂（M11）。

根据配置返回对应的 TTS provider 实例。
支持：cosyvoice（默认）、edge-tts
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_provider: TTSProvider | None = None


def get_tts_provider() -> TTSProvider:
    """获取 TTS provider 单例。"""
    global _provider
    if _provider is not None:
        return _provider

    settings = get_settings()
    provider_name = getattr(settings, "tts_provider", "cosyvoice").lower()

    if provider_name == "edge-tts":
        from app.tts.edge_tts_provider import EdgeTTSProvider

        _provider = EdgeTTSProvider()
        logger.info("TTS provider: edge-tts")
    else:
        from app.tts.cosyvoice import CosyVoiceProvider

        _provider = CosyVoiceProvider()
        logger.info("TTS provider: cosyvoice")

    return _provider


def set_tts_provider(provider: TTSProvider | None) -> None:
    """设置 TTS provider（用于测试或运行时切换）。"""
    global _provider
    _provider = provider
