"""FunASR 流式 ASR 客户端（M18）。

通过 WebSocket 连接 FunASR 服务，实现实时语音识别。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import websockets

from app.config import get_settings

logger = logging.getLogger(__name__)


class FunASRClient:
    """FunASR WebSocket 客户端。"""

    def __init__(self, ws_url: str | None = None) -> None:
        self._ws_url = ws_url or get_settings().funasr_ws_url

    async def recognize_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        sample_rate: int = 16000,
    ) -> AsyncIterator[str]:
        """流式识别：官方 2pass 协议。

        FunASR 2pass 会返回两种 mode 的结果：
          - 2pass-online：流式中间稿，会被后续覆盖
          - 2pass-offline：VAD 句尾离线纠错的句终稿，需要累加

        这里把两者拼装成"committed + pending"并 yield，上层无需区分。
        """
        import json

        try:
            async with websockets.connect(self._ws_url) as ws:
                config = {
                    "mode": "2pass",
                    "chunk_size": [5, 10, 5],
                    "chunk_interval": 10,
                    "encoder_chunk_look_back": 4,
                    "decoder_chunk_look_back": 0,
                    "wav_name": "webling",
                    "wav_format": "pcm",
                    "audio_fs": sample_rate,
                    "is_speaking": True,
                    "hotwords": "",
                    "itn": True,
                }
                await ws.send(json.dumps(config))
                logger.debug("FunASR config sent: %s", config)

                results: asyncio.Queue[str | None] = asyncio.Queue()
                state = {"committed": "", "pending": ""}

                async def receiver() -> None:
                    try:
                        async for msg in ws:
                            data = json.loads(msg)
                            text = data.get("text", "")
                            if not text:
                                continue
                            mode = data.get("mode", "")
                            if mode == "2pass-online":
                                state["pending"] = text
                            elif mode == "2pass-offline":
                                state["committed"] += text
                                state["pending"] = ""
                            else:
                                # 兜底：其他 mode 当作整段覆盖
                                state["committed"] = text
                                state["pending"] = ""
                            await results.put(state["committed"] + state["pending"])
                    except Exception as exc:
                        logger.debug("FunASR receiver 结束：%s", exc)
                    await results.put(None)

                async def sender() -> None:
                    try:
                        async for chunk in audio_chunks:
                            await ws.send(chunk)
                        # 音频流结束后通知 FunASR flush 最终结果
                        await ws.send(json.dumps({"is_speaking": False}))
                    except Exception as exc:
                        logger.debug("FunASR sender 结束：%s", exc)

                recv_task = asyncio.create_task(receiver())
                send_task = asyncio.create_task(sender())

                try:
                    while True:
                        text = await results.get()
                        if text is None:
                            break
                        yield text
                finally:
                    send_task.cancel()
                    recv_task.cancel()

        except Exception as exc:
            logger.error("FunASR 连接失败: %s", exc)
            raise


# 全局单例
_client: FunASRClient | None = None


def get_funasr_client() -> FunASRClient:
    global _client
    if _client is None:
        _client = FunASRClient()
    return _client
