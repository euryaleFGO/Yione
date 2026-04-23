"""Session management (M1 内存 → M7 MongoDB)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.schemas.chat import SessionCreate, SessionInfo
from app.services.session_service import SessionService, get_session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    svc: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    sessions = await svc.list_all()
    return SessionListResponse(sessions=sessions)


@router.post("", response_model=SessionInfo)
async def create_session(
    body: SessionCreate,
    svc: SessionService = Depends(get_session_service),
) -> SessionInfo:
    return await svc.create(character_id=body.character_id, user_ref=body.user_ref)


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
) -> SessionInfo:
    info = await svc.get(session_id)
    if info is None:
        raise HTTPException(status_code=404, detail="session not found")
    return info
