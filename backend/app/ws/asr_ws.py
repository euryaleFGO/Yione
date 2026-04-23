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


@router.websocket("/ws/asr")
async def asr_ws(ws: WebSocket) -> None:
    """ASR WebSocket：接收音频流，返回识别文本。"""
    await ws.accept()
    logger.info("ASR WebSocket connected")

    try:
        # 第一条消息是配置
        config_raw = await ws.receive_text()
        config = json.loads(config_raw)
        sample_rate = config.get("sample_rate", 16000)
        logger.info("ASR config: %s", config)

        # 创建音频队列
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        # 启动接收任务
        async def receiver():
            try:
                while True:
                    data = await ws.receive_bytes()
                    await audio_queue.put(data)
            except Exception:
                pass
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

        try:
            async for text in client.recognize_stream(audio_iter(), sample_rate=sample_rate):
                await ws.send_json({"type": "asr_result", "text": text, "is_final": False})
        except Exception as exc:
            logger.error("FunASR error: %s", exc)
            await ws.send_json({"type": "asr_error", "message": str(exc)})

        # 发送最终结果
        await ws.send_json({"type": "asr_result", "text": "", "is_final": True})
        recv_task.cancel()

    except WebSocketDisconnect:
        logger.info("ASR WebSocket disconnected")
    except Exception as exc:
        logger.error("ASR WebSocket error: %s", exc)
