"""ASR WebSocket 端点（M18）。

接收前端音频流，转发给 FunASR，返回识别文本。
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.funasr_client import get_funasr_client

logger = logging.getLogger(__name__)

router = APIRouter()


async def _safe_send_json(ws: WebSocket, payload: dict) -> bool:
    """向 WebSocket 发 JSON，连接已关闭时返回 False 不抛异常。"""
    try:
        await ws.send_json(payload)
        return True
    except Exception as exc:
        logger.debug("send_json 失败（连接可能已关）：%s", exc)
        return False


@router.websocket("/ws/asr")
async def asr_ws(ws: WebSocket) -> None:
    """ASR WebSocket：接收音频流，返回识别文本。

    协议：
      - 首条 text frame：{"sample_rate": 16000}
      - 之后 binary frame：PCM 16-bit 音频 chunk
      - 音频结束：发送 text frame {"eof": true}，后端 flush FunASR 并回传最终文本
      - 回传 text frame：{"type": "asr_result", "text": "...", "is_final": bool}
    """
    await ws.accept()
    logger.info("ASR WebSocket connected")

    try:
        # 第一条消息是配置
        config_raw = await ws.receive_text()
        config = json.loads(config_raw)
        sample_rate = config.get("sample_rate", 16000)
        logger.debug("ASR config: %s", config)

        # 创建音频队列
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        # 启动接收任务：同时处理音频 bytes 和控制 text（eof）
        async def receiver():
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

        # 转发给 FunASR
        client = get_funasr_client()

        async def audio_iter():
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                yield chunk

        last_text = ""
        try:
            async for text in client.recognize_stream(audio_iter(), sample_rate=sample_rate):
                last_text = text
                ok = await _safe_send_json(
                    ws, {"type": "asr_result", "text": text, "is_final": False}
                )
                if not ok:
                    break
        except Exception as exc:
            logger.error("FunASR error: %s", exc)
            await _safe_send_json(ws, {"type": "asr_error", "message": str(exc)})

        # 发送最终结果（带最后一次识别文本，供前端提交对话）
        await _safe_send_json(
            ws, {"type": "asr_result", "text": last_text, "is_final": True}
        )
        recv_task.cancel()

    except WebSocketDisconnect:
        logger.info("ASR WebSocket disconnected")
    except Exception as exc:
        logger.error("ASR WebSocket error: %s", exc)
