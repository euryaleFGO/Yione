"""ASR WebSocket 端点（M18 + M34 实时对话循环）。

接收前端音频流，转发给 FunASR，返回识别事件。

M34 协议变化：
  - 不再"一条 is_final 就关连接"，而是保持 WS 存活直到前端主动关闭或断开
  - 每条 FunASR 2pass-online 中间稿 → emit ``asr_partial``
  - 每条 FunASR 2pass-offline 句终稿 → emit ``asr_final``
  - 前端可以收到任意多对 partial/final 事件，直到它关 WS

向后兼容：为了不破坏已有 M18 前端逻辑，后端在每次 ``asr_final`` 之后额外
emit 一条带 ``is_final=true`` 的老式 ``asr_result``，前端可自行取舍。
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.funasr_client import get_funasr_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def _safe_send_json(ws: WebSocket, payload: dict[str, object]) -> bool:
    """向 WebSocket 发 JSON，连接已关闭时返回 False 不抛异常。"""
    try:
        await ws.send_json(payload)
        return True
    except Exception as exc:
        logger.debug("send_json 失败（连接可能已关）：%s", exc)
        return False


@router.websocket("/ws/asr")
async def asr_ws(ws: WebSocket) -> None:
    """ASR WebSocket：接收音频流，返回识别事件。

    协议：
      - 首条 text frame：``{"sample_rate": 16000}``
      - 之后 binary frame：PCM 16-bit 音频 chunk
      - 前端主动结束：发 text frame ``{"eof": true}`` 或直接 close
      - 回传事件（text frame）：
          * ``{"type": "asr_partial", "text": "...", "committed": "..."}``
          * ``{"type": "asr_final", "text": "...", "committed": "..."}``
          * ``{"type": "asr_result", "text": "...", "is_final": true}``（兼容旧版）
          * ``{"type": "asr_error", "message": "..."}``
    """
    await ws.accept()
    logger.info("ASR WebSocket connected")

    try:
        # 第一条消息是配置
        config_raw = await ws.receive_text()
        config = json.loads(config_raw)
        sample_rate = config.get("sample_rate", 16000)
        logger.debug("ASR config: %s", config)

        # 音频队列
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def receiver() -> None:
            """同时处理音频 bytes 和控制 text（eof / disconnect）。"""
            try:
                while True:
                    message = await ws.receive()
                    if message.get("type") == "websocket.disconnect":
                        break
                    chunk = message.get("bytes")
                    if chunk:
                        await audio_queue.put(chunk)
                        continue
                    text_payload = message.get("text")
                    if text_payload:
                        try:
                            ctrl = json.loads(text_payload)
                        except json.JSONDecodeError:
                            continue
                        if ctrl.get("eof"):
                            break
            except Exception as exc:
                logger.debug("ASR receiver 结束：%s", exc)
            await audio_queue.put(None)

        recv_task = asyncio.create_task(receiver())

        client = get_funasr_client()

        async def audio_iter() -> AsyncIterator[bytes]:
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                yield chunk

        try:
            async for evt in client.recognize_stream(audio_iter(), sample_rate=sample_rate):
                mode = evt["mode"]
                if mode == "partial":
                    ok = await _safe_send_json(ws, {
                        "type": "asr_partial",
                        "text": evt["text"],
                        "committed": evt["committed"],
                    })
                elif mode == "final":
                    # 新格式：句终稿独立事件
                    ok = await _safe_send_json(ws, {
                        "type": "asr_final",
                        "text": evt["text"],
                        "committed": evt["committed"],
                    })
                    # 旧格式兼容：给没迁移的前端继续喂 asr_result
                    if ok:
                        ok = await _safe_send_json(ws, {
                            "type": "asr_result",
                            "text": evt["committed"],
                            "is_final": True,
                        })
                else:
                    ok = True
                if not ok:
                    break
        except Exception as exc:
            logger.error("FunASR error: %s", exc)
            await _safe_send_json(ws, {"type": "asr_error", "message": str(exc)})

        recv_task.cancel()

    except WebSocketDisconnect:
        logger.info("ASR WebSocket disconnected")
    except Exception as exc:
        logger.error("ASR WebSocket error: %s", exc)
