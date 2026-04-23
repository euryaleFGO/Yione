"""Non-streaming TTS endpoint (M1/M3 surface; WS is the primary path)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.tts_service import TTSError, TTSService, get_tts_service

router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice_id: str | None = None


class TTSSegmentOut(BaseModel):
    url: str
    segment_idx: int
    sample_rate: int
    duration_s: float


class TTSResponse(BaseModel):
    segments: list[TTSSegmentOut]


@router.post("/synth", response_model=TTSResponse)
async def synth(
    body: TTSRequest,
    tts: TTSService = Depends(get_tts_service),
) -> TTSResponse:
    try:
        segments = [
            TTSSegmentOut(
                url=seg.url,
                segment_idx=seg.segment_idx,
                sample_rate=seg.sample_rate,
                duration_s=seg.duration_s,
            )
            async for seg in tts.synth_stream(body.text, spk_id=body.voice_id)
        ]
    except TTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TTSResponse(segments=segments)
