"""TTS 服务层（M11 重构）。

提供统一的 TTS 接口，底层委托给配置的 provider（cosyvoice / edge-tts）。
保留原有 TTSService 类签名以兼容现有调用方。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path

from app.tts import get_tts_provider
from app.tts.base import AudioSegment, TTSError

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["TTSError", "AudioSegment", "TTSService", "get_tts_service"]


class TTSService:
    """兼容层：委托给底层 provider。"""

    async def synth_stream(
        self,
        text: str,
        *,
        spk_id: str | None = None,
        client_id: str = "webling",
    ) -> AsyncIterator[AudioSegment]:
        provider = get_tts_provider()
        async for seg in provider.synth_stream(text, spk_id=spk_id, client_id=client_id):
            yield seg

    async def close(self) -> None:
        provider = get_tts_provider()
        await provider.close()


_singleton: TTSService | None = None


def get_tts_service() -> TTSService:
    global _singleton
    if _singleton is None:
        _singleton = TTSService()
    return _singleton
