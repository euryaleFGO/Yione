"""Non-streaming chat endpoint (M1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import AgentService, get_agent_service
from app.services.session_service import SessionService, get_session_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    agent: AgentService = Depends(get_agent_service),
    sessions: SessionService = Depends(get_session_service),
) -> ChatResponse:
    if sessions.get(body.session_id) is None:
        raise HTTPException(status_code=404, detail="session not found")
    reply = await agent.reply_text(body.text)
    return ChatResponse(reply=reply)
