"""Chat WebSocket endpoint.

Accepts ``?session_id=...`` for now; full JWT auth lands in M6.

Pipelined LLM → TTS:
- LLM stream is split into sentences on ``。！？.!?\\n``.
- Each completed sentence is enqueued to a serial TTS worker that runs
  concurrently with the LLM, so the first audio segment starts playing
  well before the LLM has finished generating.
- The worker stamps every wav segment with a monotonically increasing
  *global* ``segment_idx`` so the browser's AudioQueue plays in reply order
  even though several TTS jobs are fired back to back.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass

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


_SENTENCE_END = re.compile(r"[。！？.!?\n]")
# 让短句也能走 TTS，比如 "你好！"；过滤掉 "好"/"。" 这种个别字符的噪声
_MIN_SENTENCE_CHARS = 2
# 若 LLM 已经出了 N 个字还没碰到句号，在逗号/分号处也提前切一刀，避免长串积压
_SOFT_BREAK = re.compile(r"[，、；,;]")
_SOFT_BREAK_AFTER = 18


def _pop_sentence(buf: str) -> tuple[str | None, str]:
    """Find the first complete sentence in *buf*.

    Hard break on ``。！？.!?\\n``; if the buffer grows past
    ``_SOFT_BREAK_AFTER`` chars without one, soft-break on a comma instead
    so the user doesn't wait for a whole long sentence.
    """
    match = _SENTENCE_END.search(buf)
    if match is not None:
        end = match.end()
        sentence = buf[:end]
        if len(sentence.strip()) < _MIN_SENTENCE_CHARS:
            return None, buf
        return sentence, buf[end:]

    if len(buf) >= _SOFT_BREAK_AFTER:
        soft = _SOFT_BREAK.search(buf)
        if soft is not None:
            end = soft.end()
            sentence = buf[:end]
            if len(sentence.strip()) >= _MIN_SENTENCE_CHARS:
                return sentence, buf[end:]
    return None, buf


@dataclass
class _TurnState:
    """Shared between the LLM loop and the TTS worker for one user turn."""

    t0: float
    next_idx: int = 0


async def _tts_worker(
    ws: WebSocket,
    pending: asyncio.Queue[str | None],
    state: _TurnState,
) -> None:
    """Drain *pending* sentences → TTS → AudioEvent. Sentinel ``None`` quits."""
    tts = get_tts_service()
    while True:
        sentence = await pending.get()
        if sentence is None:
            return
        try:
            first = True
            async for seg in tts.synth_stream(sentence):
                state.next_idx += 1
                if first:
                    logger.info(
                        "[%.2fs] TTS first seg for %r → idx=%d url=%s",
                        time.monotonic() - state.t0,
                        sentence[:20],
                        state.next_idx,
                        seg.url,
                    )
                    first = False
                await _send(
                    ws,
                    AudioEvent(
                        url=seg.url,
                        segment_idx=state.next_idx,
                        sample_rate=seg.sample_rate,
                    ),
                )
        except TTSError as exc:
            logger.warning("TTS failed: %s", exc)
            await _send(ws, ErrorEvent(code="tts_failed", message=str(exc)))


async def _handle_user_message(ws: WebSocket, user_text: str) -> None:
    agent = get_agent_service()
    t0 = time.monotonic()
    logger.info("[0.00s] user_message received: %r", user_text[:40])

    await _send(ws, StateEvent(value="processing"))

    pending: asyncio.Queue[str | None] = asyncio.Queue()
    state = _TurnState(t0=t0)
    worker = asyncio.create_task(_tts_worker(ws, pending, state))

    buffer = ""      # rolling LLM output (all of it, for final subtitle)
    unspoken = ""    # text accumulated but not yet sent to TTS
    first_chunk = True
    sentences_queued = 0

    async for chunk in agent.stream_reply(user_text):
        if first_chunk:
            logger.info("[%.2fs] LLM first chunk (%r…)", time.monotonic() - t0, chunk[:20])
            first_chunk = False
        buffer += chunk
        unspoken += chunk
        await _send(
            ws,
            SubtitleEvent(text=buffer, is_final=False, emotion="neutral"),
        )
        while True:
            sentence, unspoken = _pop_sentence(unspoken)
            if sentence is None:
                break
            sentences_queued += 1
            logger.info(
                "[%.2fs] queue sentence #%d: %r",
                time.monotonic() - t0,
                sentences_queued,
                sentence[:30],
            )
            await pending.put(sentence)

    logger.info(
        "[%.2fs] LLM stream done, buffer=%d chars, unspoken=%r",
        time.monotonic() - t0,
        len(buffer),
        unspoken[:40],
    )

    # Final subtitle + flush remainder to TTS
    await _send(ws, SubtitleEvent(text=buffer, is_final=True, emotion="neutral"))
    if unspoken.strip():
        sentences_queued += 1
        await pending.put(unspoken)

    await pending.put(None)  # stop the worker after the last sentence
    await _send(ws, StateEvent(value="speaking"))
    await worker  # let it finish draining
    logger.info("[%.2fs] all segments emitted", time.monotonic() - t0)
    await _send(ws, StateEvent(value="idle"))


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket, session_id: str = Query(...)) -> None:
    sessions = get_session_service()
    if sessions.get(session_id) is None:
        await ws.close(code=4404, reason="session not found")
        return

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
                await _handle_user_message(ws, event.text)
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
