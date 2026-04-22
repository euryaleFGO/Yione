"""REST schemas for sessions + chat (M1 slim: in-memory, no Mongo yet)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    character_id: str = "ling"
    user_ref: str | None = None


class SessionInfo(BaseModel):
    session_id: str
    character_id: str
    user_ref: str | None = None
    greeting: str
    created_at: datetime


class ChatRequest(BaseModel):
    session_id: str
    text: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    emotion: str = "neutral"
    motion: str | None = None
