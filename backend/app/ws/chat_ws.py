"""Chat WebSocket endpoint.

Accepts ``?session_id=...`` for now; full JWT auth lands in M6.
After a subtitle-final event the server optionally triggers a TTS stream
and emits ``audio`` events as wav segments become available (M3).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.schemas.ws import (
    AudioEvent,
    ErrorEvent,
    PongEvent,
    ServerEvent,
    StateEvent,
    SubtitleEvent,
    parse_client_event,
)
from app.services.agent_service import get_agent_service
from app.services.session_service import get_session_service
from app.services.tts_service import TTSError, get_tts_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send(ws: WebSocket, event: ServerEvent) -> None:
    await ws.send_json(event.model_dump(mode="json"))


async def _speak(ws: WebSocket, text: str) -> None:
    """Drive a TTS stream, emitting ``audio`` events per segment.

    Errors (CosyVoice unreachable, job failed) are reported via ``error``
    events but do not tear down the WS — text chat stays usable.
    """
    tts = get_tts_service()
    try:
        async for seg in tts.synth_stream(text):
            await _send(
                ws,
                AudioEvent(
                    url=seg.url,
                    segment_idx=seg.segment_idx,
                    sample_rate=seg.sample_rate,
                ),
            )
    except TTSError as exc:
        logger.warning("TTS failed: %s", exc)
        await _send(ws, ErrorEvent(code="tts_failed", message=str(exc)))


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket, session_id: str = Query(...)) -> None:
    sessions = get_session_service()
    if sessions.get(session_id) is None:
        await ws.close(code=4404, reason="session not found")
        return

    agent = get_agent_service()
    await ws.accept()
    await _send(ws, StateEvent(value="idle"))

    try:
        while True:
            payload = await ws.receive_json()
            try:
                event = parse_client_event(payload)
            except ValueError as exc:
                await _send(ws, ErrorEvent(code="bad_event", message=str(exc)))
                continue

            if event.type == "ping":
                await _send(ws, PongEvent())
                continue

            if event.type == "user_message":
                await _send(ws, StateEvent(value="processing"))
                buffer: list[str] = []
                async for chunk in agent.stream_reply(event.text):
                    buffer.append(chunk)
                    await _send(
                        ws,
                        SubtitleEvent(
                            text="".join(buffer),
                            is_final=False,
                            emotion="neutral",
                        ),
                    )
                final_text = "".join(buffer)
                await _send(
                    ws,
                    SubtitleEvent(text=final_text, is_final=True, emotion="neutral"),
                )
                await _send(ws, StateEvent(value="speaking"))
                await _speak(ws, final_text)
                await _send(ws, StateEvent(value="idle"))
                continue

            if event.type == "cancel":
                # M4: actually cancel in-flight generation
                await _send(ws, StateEvent(value="idle"))
                continue

            if event.type == "change_character":
                # M7 implementation; M1 no-op ack
                await _send(
                    ws,
                    ErrorEvent(
                        code="not_implemented",
                        message="change_character ships in M7",
                    ),
                )
                continue

    except WebSocketDisconnect:
        logger.info("ws disconnected for session %s", session_id)
