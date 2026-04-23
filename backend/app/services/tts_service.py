"""TTS proxy — talks to the Ling CosyVoice HTTP server.

Protocol (matches Ling's ``backend/tts/service.py``):

- ``POST {base}/tts/enqueue`` with ``{text, use_clone, spk_id, client_id}`` →
  ``{status, job_id}``
- ``GET  {base}/tts/dequeue?job_id=...&timeout=N`` repeatedly returns one wav
  segment at a time (``audio/wav`` body). 204 = no content (still rendering
  OR task finished + queue drained); 409 = job failed; 404 = unknown job.

The stream ends when dequeue returns 204 *without* yielding a fresh segment
within a short idle window (the reference Ling client uses a soft 120s
first-segment deadline, then short timeouts; we copy that pattern).

Each segment is persisted under ``backend/app/static/tts/<uuid>.wav`` and
exposed at ``/static/tts/<uuid>.wav`` so the browser can stream it back in
via ``<audio>`` / fetch. M11 will add a TTL sweeper.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import BACKEND_ROOT, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class AudioSegment:
    """One TTS segment on disk, with the public URL the frontend should fetch."""

    segment_idx: int
    url: str  # e.g. "/static/tts/abc123.wav"
    path: Path
    sample_rate: int
    duration_s: float


class TTSError(RuntimeError):
    """Raised when the upstream CosyVoice service fails."""


class TTSService:
    """Async CosyVoice client with wav-segment persistence."""

    def __init__(
        self,
        base_url: str | None = None,
        default_spk_id: str | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.tts_base_url).rstrip("/")
        self._default_spk_id = default_spk_id or settings.tts_default_spk_id
        self._cache_dir = cache_dir or (BACKEND_ROOT / "app" / "static" / "tts")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def synth_stream(
        self,
        text: str,
        *,
        use_clone: bool = True,
        spk_id: str | None = None,
        client_id: str = "webling",
        first_segment_deadline: float = 120.0,
        dequeue_timeout: float = 10.0,
    ) -> AsyncIterator[AudioSegment]:
        """Yield wav segments in order as CosyVoice produces them."""
        text = text.strip()
        if not text:
            return

        effective_spk = spk_id or self._default_spk_id
        try:
            resp = await self._client.post(
                f"{self._base_url}/tts/enqueue",
                json={
                    "text": text,
                    "use_clone": use_clone,
                    "spk_id": effective_spk,
                    "client_id": client_id,
                },
            )
        except httpx.HTTPError as exc:
            raise TTSError(f"enqueue failed: {exc}") from exc

        if resp.status_code != 200:
            raise TTSError(f"enqueue status {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        job_id = data.get("job_id")
        if not job_id:
            raise TTSError(f"enqueue returned no job_id: {data}")

        logger.info("TTS job %s text=%s", job_id[:8], text[:40])

        seg_idx = 0
        deadline = time.monotonic() + first_segment_deadline
        while True:
            if seg_idx == 0 and time.monotonic() > deadline:
                raise TTSError("first segment timeout")

            try:
                seg_resp = await self._client.get(
                    f"{self._base_url}/tts/dequeue",
                    params={"job_id": job_id, "timeout": dequeue_timeout},
                    timeout=dequeue_timeout + 5,
                )
            except httpx.HTTPError as exc:
                raise TTSError(f"dequeue failed: {exc}") from exc

            if seg_resp.status_code == 204:
                # Empty or done. Ling's service doesn't distinguish; after
                # receiving at least one segment, 204 is the terminator.
                if seg_idx > 0:
                    return
                # Still waiting for first segment; keep polling.
                continue
            if seg_resp.status_code == 409:
                detail = seg_resp.text[:200]
                raise TTSError(f"job failed: {detail}")
            if seg_resp.status_code != 200:
                raise TTSError(f"dequeue status {seg_resp.status_code}")

            seg_idx += 1
            header_idx = seg_resp.headers.get("X-Segment-Idx")
            try:
                parsed_idx = int(header_idx) if header_idx else seg_idx
            except ValueError:
                parsed_idx = seg_idx

            sample_rate = int(seg_resp.headers.get("X-Sample-Rate", 22050))
            duration = float(seg_resp.headers.get("X-Duration", 0.0) or 0.0)

            fname = f"{uuid.uuid4().hex}.wav"
            path = self._cache_dir / fname
            await asyncio.to_thread(path.write_bytes, seg_resp.content)

            yield AudioSegment(
                segment_idx=parsed_idx,
                url=f"/static/tts/{fname}",
                path=path,
                sample_rate=sample_rate,
                duration_s=duration,
            )


_singleton: TTSService | None = None


def get_tts_service() -> TTSService:
    global _singleton
    if _singleton is None:
        _singleton = TTSService()
    return _singleton
