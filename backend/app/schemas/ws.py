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


ClientEvent = UserMessageEvent | CancelEvent | PingEvent | ChangeCharacterEvent


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


class AudioEvent(_ServerBase):
    type: Literal["audio"] = "audio"
    url: str
    segment_idx: int
    sample_rate: int


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


ServerEvent = (
    StateEvent
    | SubtitleEvent
    | MotionEvent
    | AudioEvent
    | AudioRmsEvent
    | VisemeEvent
    | ErrorEvent
    | PongEvent
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
    "MotionEvent",
    "PingEvent",
    "PongEvent",
    "ServerEvent",
    "StateEvent",
    "SubtitleEvent",
    "UserMessageEvent",
    "VisemeEvent",
    "parse_client_event",
]

# keep unused import for future use
_ = Field
