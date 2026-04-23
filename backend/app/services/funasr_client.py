"""FunASR 流式 ASR 客户端（M18）。

通过 WebSocket 连接 FunASR 服务，实现实时语音识别。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import websockets

logger = logging.getLogger(__name__)

FUNASR_WS_URL = "ws://192.168.251.56:10095"


class FunASRClient:
    """FunASR WebSocket 客户端。"""

    def __init__(self, ws_url: str | None = None) -> None:
        self._ws_url = ws_url or FUNASR_WS_URL

    async def recognize_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        sample_rate: int = 16000,
    ) -> AsyncIterator[str]:
        """流式识别：发送音频 chunks，返回识别文本。"""
        try:
            async with websockets.connect(self._ws_url) as ws:
                # 发送配置
                import json
                config = {
                    "mode": "online",
                    "chunk_size": [5, 10, 5],
                    "wav_name": "stream",
                    "is_speaking": True,
                    "wav_format": "pcm",
                    "audio_fs": sample_rate,
                }
                await ws.send(json.dumps(config))

                # 启动接收任务
                results = asyncio.Queue()

                async def receiver():
                    try:
                        async for msg in ws:
                            import json as j
                            data = j.loads(msg)
                            if "text" in data and data["text"]:
                                await results.put(data["text"])
                    except Exception:
                        pass
                    await results.put(None)

                recv_task = asyncio.create_task(receiver())

                # 发送音频
                async for chunk in audio_chunks:
                    await ws.send(chunk)

                # 结束
                await ws.send(json.dumps({"is_speaking": False}))

                # 读取结果
                while True:
                    text = await results.get()
                    if text is None:
                        break
                    yield text

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
