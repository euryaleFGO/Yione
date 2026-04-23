"""聊天 WebSocket 端点。

M1 接入文本对话；M3 做 LLM → TTS 按句流式；M4 重构为**可取消的 turn**，
并补上 emotion / motion 事件（M5）。

为什么把 turn 包成 asyncio.Task：
    之前 ``await _handle_user_message(...)`` 会阻塞主 receive 循环，导致
    在 turn 进行中发过来的 ``cancel`` 无法被读到。现在主循环创建 Task 跑生成
    管线，自己继续 ``receive_json``；遇到 ``cancel`` 直接 ``task.cancel()``，
    cancellation 会从 httpx streaming context / asyncio.Queue 顺着抛上来，
    finally 分支负责把 TTS worker 停掉、状态回 idle。

整体数据流：
    user_message → LLM stream → 按句切 → pending 队列 → TTS worker →
      AudioEvent（每句 1..N 段，segment_idx 全局递增）

emotion / motion：
    - LLM 输出支持 ``[joy]`` / ``[anger]`` 等内联标签，strip 掉后再展示与合成
    - 每产生一句话跑一次 emotion_service.detect，带进 SubtitleEvent.emotion
    - 当 turn 内首次出现非 neutral 情绪、或情绪切换时，额外发一次 MotionEvent
      驱动 Hiyori 做对应动作（Tap@Body / FlickDown / ...）
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.middlewares.auth import decode_ws_token
from app.schemas.ws import (
    AudioEvent,
    Emotion,
    ErrorEvent,
    MotionEvent,
    PongEvent,
    ServerEvent,
    StateEvent,
    SubtitleEvent,
    parse_client_event,
)
from app.services import emotion_service
from app.services.agent_service import get_agent_service
from app.services.auth_service import AuthError
from app.services.motion_map import motion_for
from app.services.session_service import get_session_service
from app.services.tts_service import TTSError, get_tts_service
from app.ws.connections import get_ws_registry

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send(ws: WebSocket, event: ServerEvent) -> None:
    """把 ServerEvent 序列化后发给前端；被取消 / 连接断开时静默忽略。"""
    try:
        await ws.send_json(event.model_dump(mode="json"))
    except Exception as exc:  # 网络层任何异常都不该炸上游
        logger.debug("send failed (%s): %s", type(exc).__name__, exc)


_SENTENCE_END = re.compile(r"[。！？.!?\n]")
# 过短的单字也切下会污染 TTS，至少要 2 字
_MIN_SENTENCE_CHARS = 2
# LLM 出了 N 字还没碰到句号，就在逗号/分号处抢先切一刀，让 TTS 不积压
_SOFT_BREAK = re.compile(r"[，、；,;]")
_SOFT_BREAK_AFTER = 18


def _pop_sentence(buf: str) -> tuple[str | None, str]:
    """从 buf 头部切出一句话；切不出来就原样返回。

    硬切：``。！？.!?\\n``；buf 长度超过 _SOFT_BREAK_AFTER 时软切在逗号/分号处。
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
    """LLM 循环 + TTS worker 共享的 turn 级状态。"""

    t0: float
    next_idx: int = 0
    # 当前 turn 已经触发过哪个情绪的 motion，避免重复触发同一个动作
    last_motion_emotion: Emotion | None = None
    # turn 级当前情绪，每遇到新一句就重新评估
    current_emotion: Emotion = "neutral"
    sentences_queued: int = 0


@dataclass
class _PendingSentence:
    """推进 TTS worker 的载荷：一句话 + 它已评估好的情绪。"""

    text: str
    emotion: Emotion


# 队列里的 None 表示"没有更多句子了，worker 可以收摊"
_PendingItem = _PendingSentence | None


async def _tts_worker(
    ws: WebSocket,
    pending: asyncio.Queue[_PendingItem],
    state: _TurnState,
) -> None:
    """消费 pending，每拿到一句就调 TTS，产生 AudioEvent。

    ``None`` 是结束哨兵。被 ``cancel()`` 时也会自然向上抛 CancelledError，
    调用方在 finally 里 await 保证不遗留 Task。
    """
    tts = get_tts_service()
    while True:
        item = await pending.get()
        if item is None:
            return
        try:
            first = True
            async for seg in tts.synth_stream(item.text):
                state.next_idx += 1
                if first:
                    logger.info(
                        "[%.2fs] TTS first seg for %r → idx=%d url=%s",
                        time.monotonic() - state.t0,
                        item.text[:20],
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


async def _maybe_emit_motion(
    ws: WebSocket,
    state: _TurnState,
    emotion: Emotion,
    character_id: str,
) -> None:
    """若情绪变了且非 neutral，就发一次 MotionEvent 驱动 Live2D 做动作。"""
    if emotion == "neutral":
        return
    if emotion == state.last_motion_emotion:
        return
    motion = motion_for(emotion, character_id=character_id)
    await _send(ws, MotionEvent(name=motion))
    state.last_motion_emotion = emotion
    logger.info("motion %s triggered by emotion=%s", motion, emotion)


async def _handle_user_message(
    ws: WebSocket,
    user_text: str,
    character_id: str,
) -> None:
    """一次完整的用户 turn。被 cancel() 时在 finally 里清理 worker 并发 idle。"""
    agent = get_agent_service()
    t0 = time.monotonic()
    logger.info("[0.00s] user_message received: %r", user_text[:40])

    await _send(ws, StateEvent(value="processing"))

    pending: asyncio.Queue[_PendingItem] = asyncio.Queue()
    state = _TurnState(t0=t0)
    worker = asyncio.create_task(_tts_worker(ws, pending, state))

    # 两份缓冲：raw 保留 LLM 原始输出（含 [tag]），clean 是剥掉标签后的字幕文本。
    raw = ""
    clean = ""
    unspoken = ""  # clean 里还没入 TTS 队列的部分
    first_chunk = True

    try:
        async for chunk in agent.stream_reply(user_text):
            if first_chunk:
                logger.info("[%.2fs] LLM first chunk (%r…)", time.monotonic() - t0, chunk[:20])
                first_chunk = False
            raw += chunk
            new_clean, last_tag = emotion_service.strip_emotion_tags(raw)
            if last_tag is not None:
                state.current_emotion = last_tag
                await _maybe_emit_motion(ws, state, state.current_emotion, character_id)
            # clean 单调增长（raw append-only + strip 幂等）
            delta = new_clean[len(clean):]
            clean = new_clean
            unspoken += delta

            await _send(
                ws,
                SubtitleEvent(text=clean, is_final=False, emotion=state.current_emotion),
            )
            while True:
                sentence, unspoken = _pop_sentence(unspoken)
                if sentence is None:
                    break
                # 每句话单独再评估一次：没有标签时可以靠关键词兜底
                sentence_emotion = emotion_service.detect(sentence)
                if sentence_emotion != "neutral":
                    state.current_emotion = sentence_emotion
                    await _maybe_emit_motion(ws, state, state.current_emotion, character_id)
                state.sentences_queued += 1
                logger.info(
                    "[%.2fs] queue sentence #%d (%s): %r",
                    time.monotonic() - t0,
                    state.sentences_queued,
                    state.current_emotion,
                    sentence[:30],
                )
                await pending.put(_PendingSentence(text=sentence, emotion=state.current_emotion))

        logger.info(
            "[%.2fs] LLM stream done, clean=%d chars, unspoken=%r",
            time.monotonic() - t0,
            len(clean),
            unspoken[:40],
        )

        await _send(
            ws,
            SubtitleEvent(text=clean, is_final=True, emotion=state.current_emotion),
        )
        if unspoken.strip():
            state.sentences_queued += 1
            await pending.put(_PendingSentence(text=unspoken, emotion=state.current_emotion))

        await pending.put(None)  # worker 收尾
        await _send(ws, StateEvent(value="speaking"))
        await worker
        logger.info("[%.2fs] all segments emitted", time.monotonic() - t0)
        await _send(ws, StateEvent(value="idle"))
    except asyncio.CancelledError:
        # 被打断：清空待合成句、停掉 worker、发一个 idle 让前端 UI 恢复
        logger.info("[%.2fs] turn cancelled", time.monotonic() - t0)
        _drain_queue(pending)
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await worker
        with contextlib.suppress(Exception):
            await _send(ws, StateEvent(value="idle"))
        raise
    except Exception:
        # 非取消错误同样要把 worker 收掉，避免泄漏 Task
        logger.exception("turn failed")
        _drain_queue(pending)
        worker.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await worker
        with contextlib.suppress(Exception):
            await _send(ws, StateEvent(value="idle"))
        raise


def _drain_queue(q: asyncio.Queue[_PendingItem]) -> None:
    """把队列里未处理的项丢掉；q.get 正被 worker 阻塞也没关系，worker 会被 cancel。"""
    try:
        while True:
            q.get_nowait()
    except asyncio.QueueEmpty:
        return


@dataclass
class _Session:
    """一个 WS 连接当前跟踪的唯一 turn。"""

    character_id: str = "ling"
    current_turn: asyncio.Task[None] | None = None

    async def cancel_current(self) -> None:
        t = self.current_turn
        if t is None or t.done():
            return
        t.cancel()
        # 等它真的结束，避免后续 send/state 与它交错
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await t
        self.current_turn = None

    def run_turn(self, coro: Coroutine[Any, Any, None]) -> None:
        self.current_turn = asyncio.create_task(coro)


@router.websocket("/ws/chat")
async def chat_ws(
    ws: WebSocket,
    session_id: str = Query(...),
    token: str | None = Query(default=None),
) -> None:
    sessions = get_session_service()
    info = sessions.get(session_id)
    if info is None:
        await ws.close(code=4404, reason="session not found")
        return

    # 生产模式下必须带 token；dev 环境可以匿名。claims 暂时没用到（Phase 2
    # 起会用 tenant_id 做 character 白名单），但先校验再握手，避免 bad actor
    # 先连上来再说。
    try:
        _ = decode_ws_token(token)
    except AuthError as exc:
        await ws.close(code=4401, reason=f"auth: {exc}")
        return

    await ws.accept()
    registry = get_ws_registry()
    await registry.register(session_id, ws)
    await _send(ws, StateEvent(value="idle"))

    sess = _Session(character_id=info.character_id)
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
                # 若上一轮还在进行，直接打断，用户最新诉求优先
                await sess.cancel_current()
                sess.run_turn(
                    _handle_user_message(ws, event.text, sess.character_id)
                )
                continue

            if event.type == "cancel":
                await sess.cancel_current()
                await _send(ws, StateEvent(value="idle"))
                continue

            if event.type == "speech_start":
                # M4 占位：未来 Phase 4 会把它接到 barge-in。
                # 现在先直接视为一次"请打断正在说话的玲"信号。
                logger.info("speech_start received; treating as barge-in cancel")
                await sess.cancel_current()
                await _send(ws, StateEvent(value="listening"))
                continue

            if event.type == "speech_end":
                logger.info("speech_end received")
                await _send(ws, StateEvent(value="idle"))
                continue

            if event.type == "change_character":
                # M7 才真正落地；这里先更新本连接的 character_id 以便后续 turn 的
                # motion map 走对角色（目前只有 Hiyori，行为一致）
                sess.character_id = event.character_id
                continue

    except WebSocketDisconnect:
        logger.info("ws disconnected for session %s", session_id)
    finally:
        # 连接断了也要把正在跑的 turn 停掉 + 从 registry 摘掉
        await sess.cancel_current()
        await registry.unregister(session_id, ws)
