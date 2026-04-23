"""Speakers REST 接口（M16）。

端点：
- GET    /api/speakers                列出所有说话人
- POST   /api/speakers/register       上传 wav + 可选 name，注册新说话人
- POST   /api/speakers/identify       上传 wav + 可选 session_id/auto_enroll，
                                      返回识别结果；命中时顺带通过 WS 把
                                      ``speaker_detected`` 推给 session_id 绑定的前端
- PATCH  /api/speakers/{id}           改昵称 / profile
- DELETE /api/speakers/{id}           删除

所有端点受 auth 中间件 require_user 保护（dev 环境允许匿名）。
"""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.middlewares.auth import require_user
from app.schemas.speaker import (
    SpeakerIdentifyResult,
    SpeakerInfo,
    SpeakerPatch,
    SpeakerRegisterResponse,
)
from app.schemas.ws import SpeakerDetectedEvent
from app.services.auth_service import TokenClaims
from app.services.speaker_service import (
    SpeakerService,
    SpeakerServiceError,
    get_speaker_service,
)
from app.ws.connections import get_ws_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speakers", tags=["speakers"])

# 10MB 上限；一段 16k/16bit 的 wav 大概 30KB/s，够注册用的 5-15s 片段
_MAX_WAV_BYTES = 10 * 1024 * 1024


async def _read_wav_upload(f: UploadFile) -> bytes:
    data = await f.read()
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传的音频为空",
        )
    if len(data) > _MAX_WAV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"音频超限（>{_MAX_WAV_BYTES} 字节）",
        )
    return data


@router.get("", response_model=list[SpeakerInfo])
async def list_speakers(
    _claims: TokenClaims = Depends(require_user),
    svc: SpeakerService = Depends(get_speaker_service),
) -> list[SpeakerInfo]:
    return [s.to_info() for s in svc.list_all()]


@router.post("/register", response_model=SpeakerRegisterResponse)
async def register_speaker(
    audio: UploadFile = File(..., description="wav / flac / ogg 音频片段"),
    name: str | None = Form(default=None),
    _claims: TokenClaims = Depends(require_user),
    svc: SpeakerService = Depends(get_speaker_service),
) -> SpeakerRegisterResponse:
    wav = await _read_wav_upload(audio)
    try:
        spk = svc.register_from_wav(wav, name=name)
    except SpeakerServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return SpeakerRegisterResponse(speaker=spk.to_info(), embedding_dim=spk.dim)


@router.post("/identify", response_model=SpeakerIdentifyResult)
async def identify_speaker(
    audio: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    auto_enroll: bool = Form(default=False),
    threshold: float | None = Form(default=None),
    _claims: TokenClaims = Depends(require_user),
    svc: SpeakerService = Depends(get_speaker_service),
) -> SpeakerIdentifyResult:
    wav = await _read_wav_upload(audio)
    try:
        outcome = svc.identify_from_wav(
            wav,
            threshold=threshold,
            auto_enroll=auto_enroll,
        )
    except SpeakerServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # 若带了 session_id 且识别出说话人，推 WS 事件给那条连接的前端
    if session_id and outcome.speaker is not None:
        event = SpeakerDetectedEvent(
            speaker_id=outcome.speaker.id,
            name=outcome.speaker.name,
            confidence=outcome.score,
            is_new=outcome.is_new,
        )
        ok = await get_ws_registry().send(session_id, event)
        if not ok:
            logger.debug("session_id=%s 没有活动 WS 连接，speaker_detected 未送达", session_id)

    return SpeakerIdentifyResult(
        matched=outcome.matched,
        score=outcome.score,
        threshold=outcome.threshold,
        speaker=outcome.speaker.to_info() if outcome.speaker else None,
        is_new=outcome.is_new,
        engine_available=outcome.engine_available,
    )


@router.patch("/{speaker_id}", response_model=SpeakerInfo)
async def patch_speaker(
    speaker_id: str,
    patch: SpeakerPatch,
    _claims: TokenClaims = Depends(require_user),
    svc: SpeakerService = Depends(get_speaker_service),
) -> SpeakerInfo:
    spk = svc.update(speaker_id, patch)
    if spk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="speaker not found")
    return spk.to_info()


@router.delete("/{speaker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_speaker(
    speaker_id: str,
    _claims: TokenClaims = Depends(require_user),
    svc: SpeakerService = Depends(get_speaker_service),
) -> None:
    ok = svc.delete(speaker_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="speaker not found")
