"""WebSocket event schemas.

**Must** stay in structural sync with ``packages/core/src/types/ws.ts`` —
that file is the shared source of truth. Any change here should be mirrored
there (and vice-versa); a CI check will guard this in M4.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Emotion = Literal[
    "neutral",
    "joy",
    "sadness",
    "anger",
    "fear",
    "surprise",
    "disgust",
    "affection",
]

AgentState = Literal["listening", "processing", "speaking", "idle"]


# -------- Client → Server --------


class _ClientBase(BaseModel):
    model_config = {"extra": "forbid"}


class UserMessageEvent(_ClientBase):
    type: Literal["user_message"] = "user_message"
    text: str


class CancelEvent(_ClientBase):
    type: Literal["cancel"] = "cancel"


class PingEvent(_ClientBase):
    type: Literal["ping"] = "ping"


class ChangeCharacterEvent(_ClientBase):
    type: Literal["change_character"] = "change_character"
    character_id: str


# M4 起引入：客户端在用户开始/结束说话时通知后端。
# Phase 1 只用来做日志 + 可选的"收到 speech_start 即取消当前 turn"（打断），
# 更完整的 VAD/ASR 链路留到 Phase 4（M18/M19）。
class SpeechStartEvent(_ClientBase):
    type: Literal["speech_start"] = "speech_start"


class SpeechEndEvent(_ClientBase):
    type: Literal["speech_end"] = "speech_end"


ClientEvent = (
    UserMessageEvent
    | CancelEvent
    | PingEvent
    | ChangeCharacterEvent
    | SpeechStartEvent
    | SpeechEndEvent
)


# -------- Server → Client --------


class _ServerBase(BaseModel):
    model_config = {"extra": "forbid"}


class StateEvent(_ServerBase):
    type: Literal["state"] = "state"
    value: AgentState


class SubtitleEvent(_ServerBase):
    type: Literal["subtitle"] = "subtitle"
    text: str
    is_final: bool
    emotion: Emotion = "neutral"


class MotionEvent(_ServerBase):
    type: Literal["motion"] = "motion"
    name: str


# M5 后续：情绪驱动 Live2D expression（面部表情，和 motion 是独立系统）
class ExpressionEvent(_ServerBase):
    type: Literal["expression"] = "expression"
    name: str


class AudioEvent(_ServerBase):
    type: Literal["audio"] = "audio"
    url: str
    segment_idx: int
    sample_rate: int


class VisemeTimelineItem(_ServerBase):
    char: str
    t_start: float
    t_end: float
    viseme: str  # "A" | "O" | "I" | "E" | "U" | "rest"


class VisemeTimelineEvent(_ServerBase):
    """M36：跟 AudioEvent 配对出现，把该段 TTS 的字符级嘴型时间轴推给前端。

    前端按 audio.currentTime 查 timeline，驱动 ParamMouthForm / ParamMouthOpenY，
    与情绪 expression 的 MouthForm 叠加。
    """

    type: Literal["viseme_timeline"] = "viseme_timeline"
    segment_idx: int
    timeline: list[VisemeTimelineItem]


class AudioRmsEvent(_ServerBase):
    type: Literal["audio_rms"] = "audio_rms"
    rms: float
    t: float


class VisemeEvent(_ServerBase):
    type: Literal["viseme"] = "viseme"
    open_y: float
    form: float


class ErrorEvent(_ServerBase):
    type: Literal["error"] = "error"
    code: str
    message: str


class PongEvent(_ServerBase):
    type: Literal["pong"] = "pong"


PlaceholderAction = Literal["start", "stop"]


class PlaceholderEvent(_ServerBase):
    type: Literal["placeholder_mouth"] = "placeholder_mouth"
    action: PlaceholderAction


# M16：声纹识别命中时推给前端；is_new=True 表示自动注册出的新说话人
class SpeakerDetectedEvent(_ServerBase):
    type: Literal["speaker_detected"] = "speaker_detected"
    speaker_id: str
    name: str | None = None
    confidence: float
    is_new: bool = False


ServerEvent = (
    StateEvent
    | SubtitleEvent
    | MotionEvent
    | ExpressionEvent
    | AudioEvent
    | AudioRmsEvent
    | VisemeEvent
    | VisemeTimelineEvent
    | ErrorEvent
    | PongEvent
    | PlaceholderEvent
    | SpeakerDetectedEvent
)


def parse_client_event(payload: dict[str, object]) -> ClientEvent:
    """Dispatch by ``type`` discriminator (pydantic validators raise on unknown)."""
    type_ = payload.get("type")
    match type_:
        case "user_message":
            return UserMessageEvent.model_validate(payload)
        case "cancel":
            return CancelEvent.model_validate(payload)
        case "ping":
            return PingEvent.model_validate(payload)
        case "change_character":
            return ChangeCharacterEvent.model_validate(payload)
        case "speech_start":
            return SpeechStartEvent.model_validate(payload)
        case "speech_end":
            return SpeechEndEvent.model_validate(payload)
        case _:
            raise ValueError(f"unknown client event type: {type_!r}")


__all__ = [
    "AgentState",
    "AudioEvent",
    "AudioRmsEvent",
    "CancelEvent",
    "ChangeCharacterEvent",
    "ClientEvent",
    "Emotion",
    "ErrorEvent",
    "ExpressionEvent",
    "MotionEvent",
    "PingEvent",
    "PlaceholderAction",
    "PlaceholderEvent",
    "PongEvent",
    "ServerEvent",
    "SpeakerDetectedEvent",
    "SpeechEndEvent",
    "SpeechStartEvent",
    "StateEvent",
    "SubtitleEvent",
    "UserMessageEvent",
    "VisemeEvent",
    "VisemeTimelineEvent",
    "VisemeTimelineItem",
    "parse_client_event",
]

# keep unused import for future use
_ = Field
