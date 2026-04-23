"""TTS Provider 接口（M11）。

所有 TTS provider 实现此接口，支持 CosyVoice / edge-tts 等引擎切换。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class AudioSegment:
    """一段 TTS 音频。"""

    segment_idx: int
    url: str
    path: Path
    sample_rate: int
    duration_s: float


class TTSError(RuntimeError):
    """TTS 引擎错误。"""


class TTSProvider(ABC):
    """TTS provider 抽象接口。"""

    @abstractmethod
    async def synth_stream(
        self,
        text: str,
        *,
        spk_id: str | None = None,
        client_id: str = "webling",
    ) -> AsyncIterator[AudioSegment]:
        """合成文本并逐段返回音频。"""
        ...

    async def close(self) -> None:
        """关闭连接（可选）。"""
