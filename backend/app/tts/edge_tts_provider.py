"""edge-tts TTS Provider（M11）。

使用 Microsoft Edge 的在线 TTS 服务，免费、无需部署。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import edge_tts

from app.config import BACKEND_ROOT
from app.tts.base import AudioSegment, TTSProvider, TTSError

logger = logging.getLogger(__name__)

# 中文默认语音
DEFAULT_VOICE = "zh-CN-XiaoyiNeural"


class EdgeTTSProvider(TTSProvider):
    """edge-tts provider（Microsoft Edge 在线 TTS）。"""

    def __init__(
        self,
        voice: str | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self._voice = voice or DEFAULT_VOICE
        self._cache_dir = cache_dir or (BACKEND_ROOT / "app" / "static" / "tts")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def synth_stream(
        self,
        text: str,
        *,
        spk_id: str | None = None,
        client_id: str = "webling",
    ) -> AsyncIterator[AudioSegment]:
        text = text.strip()
        if not text:
            return

        voice = spk_id or self._voice
        logger.info("edge-tts synth voice=%s text=%s", voice, text[:40])

        try:
            communicate = edge_tts.Communicate(text, voice)
            fname = f"{uuid.uuid4().hex}.mp3"
            path = self._cache_dir / fname

            seg_idx = 0
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    seg_idx += 1
                    # edge-tts 返回 mp3，直接写入文件
                    with open(path, "ab") as f:
                        f.write(chunk["data"])

            if seg_idx == 0:
                raise TTSError("edge-tts produced 0 audio chunks")

            # edge-tts 是一次性返回整段音频，作为一个 segment 返回
            file_size = path.stat().st_size
            # 估算时长（mp3 128kbps ≈ 16KB/s）
            duration_s = file_size / 16000.0

            yield AudioSegment(
                segment_idx=1,
                url=f"/static/tts/{fname}",
                path=path,
                sample_rate=24000,
                duration_s=duration_s,
            )
        except Exception as exc:
            raise TTSError(f"edge-tts failed: {exc}") from exc
