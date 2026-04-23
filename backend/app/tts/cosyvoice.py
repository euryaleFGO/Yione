"""CosyVoice TTS Provider（M11）。

对接 Ling 项目的 CosyVoice HTTP 服务。
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx

from app.config import BACKEND_ROOT, get_settings
from app.tts.base import AudioSegment, TTSError, TTSProvider, VisemeItem

logger = logging.getLogger(__name__)


class CosyVoiceProvider(TTSProvider):
    """CosyVoice TTS provider。"""

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
        spk_id: str | None = None,
        client_id: str = "webling",
        first_segment_deadline: float = 120.0,
        dequeue_timeout: float = 10.0,
    ) -> AsyncIterator[AudioSegment]:
        text = text.strip()
        if not text:
            return

        effective_spk = spk_id or self._default_spk_id or None
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

        logger.info("CosyVoice job %s text=%s", job_id[:8], text[:40])

        seg_idx = 0
        deadline = time.monotonic() + first_segment_deadline
        while True:
            if seg_idx == 0 and time.monotonic() > deadline:
                raise TTSError("first segment timeout")

            try:
                # with_timeline=1 → 服务端返 JSON，带 wav_b64 + viseme timeline
                seg_resp = await self._client.get(
                    f"{self._base_url}/tts/dequeue",
                    params={
                        "job_id": job_id,
                        "timeout": dequeue_timeout,
                        "with_timeline": 1,
                    },
                    timeout=dequeue_timeout + 5,
                )
            except httpx.HTTPError as exc:
                raise TTSError(f"dequeue failed: {exc}") from exc

            if seg_resp.status_code == 204:
                if seg_idx == 0:
                    raise TTSError("CosyVoice produced 0 segments")
                return
            if seg_resp.status_code == 202:
                continue
            if seg_resp.status_code == 409:
                raise TTSError(f"job failed: {seg_resp.text[:200]}")
            if seg_resp.status_code == 404:
                raise TTSError(f"job {job_id[:8]} disappeared")
            if seg_resp.status_code != 200:
                raise TTSError(f"dequeue status {seg_resp.status_code}")

            seg_idx += 1
            body = seg_resp.json()
            sample_rate = int(body.get("sample_rate") or 22050)
            wav_bytes = base64.b64decode(body.get("wav_b64") or "")
            timeline_raw = body.get("timeline") or []
            timeline = tuple(
                VisemeItem(
                    char=str(it.get("char", "")),
                    t_start=float(it.get("t_start", 0.0)),
                    t_end=float(it.get("t_end", 0.0)),
                    viseme=str(it.get("viseme", "rest")),
                )
                for it in timeline_raw
                if isinstance(it, dict)
            )

            fname = f"{uuid.uuid4().hex}.wav"
            path = self._cache_dir / fname
            await asyncio.to_thread(path.write_bytes, wav_bytes)

            yield AudioSegment(
                segment_idx=seg_idx,
                url=f"/static/tts/{fname}",
                path=path,
                sample_rate=sample_rate,
                duration_s=0.0,
                timeline=timeline,
            )
