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
        use_clone: bool | None = None,
        spk_id: str | None = None,
        client_id: str = "webling",
        first_segment_deadline: float = 120.0,
        dequeue_timeout: float = 10.0,
    ) -> AsyncIterator[AudioSegment]:
        """Yield wav segments in order as CosyVoice produces them.

        ``use_clone`` defaults to True iff a concrete ``spk_id`` resolves,
        otherwise False — on a CosyVoice instance with no registered speakers
        (see ``GET /tts/speakers``), clone mode would fail silently.
        """
        text = text.strip()
        if not text:
            return

        effective_spk = spk_id or self._default_spk_id or None
        # A "default" / empty spk_id cannot drive cloning; fall back to
        # zero-shot TTS so we always get audible output.
        if use_clone is None:
            use_clone = bool(effective_spk and effective_spk != "default")

        enqueue_body: dict[str, object] = {
            "text": text,
            "use_clone": use_clone,
            "client_id": client_id,
        }
        if use_clone and effective_spk:
            enqueue_body["spk_id"] = effective_spk

        try:
            resp = await self._client.post(
                f"{self._base_url}/tts/enqueue",
                json=enqueue_body,
            )
        except httpx.HTTPError as exc:
            raise TTSError(f"enqueue failed: {exc}") from exc

        if resp.status_code != 200:
            raise TTSError(f"enqueue status {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        job_id = data.get("job_id")
        if not job_id:
            raise TTSError(f"enqueue returned no job_id: {data}")
        logger.debug(
            "TTS enqueue ok: job=%s spk=%s resp=%s",
            job_id,
            effective_spk,
            data,
        )

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

            # Ling's service.py returns 204 both when the queue is transiently
            # empty AND when the worker's terminal `None` sentinel is popped.
            # There is no protocol-level way to distinguish them — on 204 the
            # server *pops the job* if it was the sentinel, so polling again
            # yields 404. We match Ling's official client and treat 204 as
            # terminal. If no audio segments were produced, surface a clear
            # diagnostic (usually: spk_id/use_clone combo rejected silently).
            if seg_resp.status_code == 204:
                if seg_idx == 0:
                    raise TTSError(
                        "server finished with 0 audio segments — check "
                        "spk_id / use_clone and CosyVoice logs"
                    )
                return
            if seg_resp.status_code == 202:
                # Some CosyVoice builds use 202 = "pending, keep polling".
                continue
            if seg_resp.status_code == 409:
                detail = seg_resp.text[:200]
                raise TTSError(f"job failed: {detail}")
            if seg_resp.status_code == 404:
                # Job popped under us (multi-worker deploy w/o sticky routing,
                # or previous 204 already terminated). Nothing more to do.
                raise TTSError(
                    f"job {job_id[:8]} disappeared mid-stream — multi-worker "
                    "upstream or already terminated"
                )
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
