"""FunASR 流式 ASR 客户端（M18 + M34 实时对话循环）。

通过 WebSocket 连接 FunASR 服务，实现实时语音识别。

M34 把原本单句吐完即退的 yield 语义升级为事件流：每次 FunASR 吐 2pass-online
就 emit 一条 ``partial``（带当前累计文本），每次 2pass-offline 就 emit 一条
``final``（带刚完成的那一句）；调用方可按需做"句终提交 / 开口打断"。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import TypedDict

import websockets

from app.config import get_settings

logger = logging.getLogger(__name__)


class ASREvent(TypedDict):
    """ASR 识别事件。

    - ``mode="partial"``：2pass-online 中间稿。``text`` 为 ``committed + pending``。
    - ``mode="final"``：2pass-offline 句终稿到达，``text`` 为刚定稿的整句文本；
      ``committed`` 为截至此刻累积的所有定稿句子拼起来，方便消费方选择按句处理
      还是按累积稿处理。
    """

    mode: str  # "partial" | "final"
    text: str
    committed: str


class FunASRClient:
    """FunASR WebSocket 客户端。"""

    def __init__(self, ws_url: str | None = None) -> None:
        self._ws_url = ws_url or get_settings().funasr_ws_url

    async def recognize_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        sample_rate: int = 16000,
    ) -> AsyncIterator[ASREvent]:
        """流式识别：官方 2pass 协议，yield 结构化 ASREvent。

        - 上层 ``audio_chunks`` 不结束 → 本协程不结束（支持 M34 长会话、多句识别）。
        - 上层通过关闭/停止 ``audio_chunks`` 生成器，驱动本协程优雅收尾。
        """
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

                events: asyncio.Queue[ASREvent | None] = asyncio.Queue()
                state = {"committed": "", "pending": ""}

                async def receiver() -> None:
                    try:
                        async for msg in ws:
                            data = json.loads(msg)
                            text = data.get("text", "")
                            mode = data.get("mode", "")
                            if mode == "2pass-online":
                                # 中间稿：pending 直接覆盖
                                state["pending"] = text
                                if not text:
                                    continue
                                await events.put({
                                    "mode": "partial",
                                    "text": state["committed"] + state["pending"],
                                    "committed": state["committed"],
                                })
                            elif mode == "2pass-offline":
                                # 句终稿：累加到 committed，清 pending，发 final
                                if not text:
                                    continue
                                state["committed"] += text
                                state["pending"] = ""
                                await events.put({
                                    "mode": "final",
                                    "text": text,
                                    "committed": state["committed"],
                                })
                            else:
                                # 兜底：非 2pass 情况下把整段当一次 final
                                if not text:
                                    continue
                                state["committed"] = text
                                state["pending"] = ""
                                await events.put({
                                    "mode": "final",
                                    "text": text,
                                    "committed": state["committed"],
                                })
                    except Exception as exc:
                        logger.debug("FunASR receiver 结束：%s", exc)
                    await events.put(None)

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
                        evt = await events.get()
                        if evt is None:
                            break
                        yield evt
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
