"""Speaker 业务层（M16）。

把下面几件事粘起来：
  SVAdapter.embed  ──→  Speaker 向量
  SpeakerRepository ──→ 存 / 查 / 改 / 删
  cosine_similarity ──→ identify 时的打分

对外暴露的是"业务动词"：register(wav) / identify(wav) / update / list / delete。
路由层和测试都只跟 SpeakerService 打交道。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.domain.speaker import Speaker, cosine_similarity, new_speaker
from app.integrations.audio_io import AudioDecodeError, decode_wav_bytes
from app.integrations.ling_sv_adapter import (
    DEFAULT_THRESHOLD,
    SVAdapter,
    get_sv_adapter,
)
from app.repositories.speaker_repo import (
    JsonFileSpeakerRepo,
    get_speaker_repo,
)
from app.schemas.speaker import SpeakerPatch

logger = logging.getLogger(__name__)


class SpeakerServiceError(Exception):
    """业务级错误（引擎挂、解码失败、向量维度不一致等）。"""


@dataclass(slots=True)
class IdentifyOutcome:
    matched: bool
    score: float
    threshold: float
    speaker: Speaker | None
    is_new: bool
    engine_available: bool


def _new_id() -> str:
    return f"spk_{uuid.uuid4().hex[:12]}"


class SpeakerService:
    def __init__(
        self,
        adapter: SVAdapter | None = None,
        repo: JsonFileSpeakerRepo | None = None,
    ) -> None:
        self._adapter = adapter or get_sv_adapter()
        self._repo = repo or get_speaker_repo()

    # ---- 对外动词 ----

    def list_all(self) -> list[Speaker]:
        return self._repo.list_all()

    def get(self, speaker_id: str) -> Speaker | None:
        return self._repo.get(speaker_id)

    def update(self, speaker_id: str, patch: SpeakerPatch) -> Speaker | None:
        spk = self._repo.get(speaker_id)
        if spk is None:
            return None
        if patch.name is not None:
            spk.name = patch.name
        if patch.profile is not None:
            spk.profile = patch.profile
        # 触发一次 updated_at 刷新
        from datetime import UTC, datetime

        spk.updated_at = datetime.now(tz=UTC)
        self._repo.save(spk)
        return spk

    def delete(self, speaker_id: str) -> bool:
        return self._repo.delete(speaker_id)

    def register_from_wav(
        self,
        wav_bytes: bytes,
        *,
        name: str | None = None,
    ) -> Speaker:
        """从 wav 字节流登记一个新说话人。"""
        vec = self._embed_wav(wav_bytes)
        return self.register_from_vector(vec, name=name)

    def register_from_vector(
        self,
        voiceprint: list[float],
        *,
        name: str | None = None,
    ) -> Speaker:
        """已有 voiceprint 向量直接入库（testable seam，不依赖音频解码）。"""
        spk = new_speaker(speaker_id=_new_id(), voiceprint=voiceprint, name=name)
        self._repo.save(spk)
        logger.info("注册新说话人 id=%s name=%s dim=%d", spk.id, name, len(voiceprint))
        return spk

    def identify_from_wav(
        self,
        wav_bytes: bytes,
        *,
        threshold: float | None = None,
        auto_enroll: bool = False,
    ) -> IdentifyOutcome:
        """对一段 wav 做识别，返回是否命中 + 打分 + （可选）自动注册。"""
        effective_threshold = (
            threshold if threshold is not None else self._adapter.threshold
        )

        if not self._adapter.is_available:
            logger.info("SVAdapter 不可用（%s），identify 走降级", self._adapter.load_error)
            return IdentifyOutcome(
                matched=False,
                score=0.0,
                threshold=effective_threshold,
                speaker=None,
                is_new=False,
                engine_available=False,
            )

        vec = self._embed_wav(wav_bytes)
        return self.identify_from_vector(
            vec,
            threshold=effective_threshold,
            auto_enroll=auto_enroll,
        )

    def identify_from_vector(
        self,
        vec: list[float],
        *,
        threshold: float | None = None,
        auto_enroll: bool = False,
    ) -> IdentifyOutcome:
        """已有 voiceprint 向量直接识别（testable seam）。"""
        effective_threshold = (
            threshold if threshold is not None else self._adapter.threshold
        )
        all_speakers = self._repo.list_all()
        best: tuple[float, Speaker | None] = (-1.0, None)
        for s in all_speakers:
            if s.dim != len(vec):
                # 维度不同说明那条是早期换模型时入库的；跳过而不是炸
                logger.warning(
                    "speaker %s 向量维度 %d 与当前 embed 维度 %d 不一致，跳过比对",
                    s.id,
                    s.dim,
                    len(vec),
                )
                continue
            score = cosine_similarity(s.voiceprint, vec)
            if score > best[0]:
                best = (score, s)

        score, candidate = best
        if candidate is not None and score >= effective_threshold:
            # 命中：把这条新样本并进已有 speaker，持续细化 voiceprint
            candidate.merge_voiceprint(vec)
            self._repo.save(candidate)
            return IdentifyOutcome(
                matched=True,
                score=score,
                threshold=effective_threshold,
                speaker=candidate,
                is_new=False,
                engine_available=True,
            )

        if auto_enroll:
            spk = new_speaker(speaker_id=_new_id(), voiceprint=vec)
            self._repo.save(spk)
            logger.info(
                "identify 未命中（best=%.3f < %.3f）；auto_enroll 创建 %s",
                score,
                effective_threshold,
                spk.id,
            )
            return IdentifyOutcome(
                matched=True,
                score=score,
                threshold=effective_threshold,
                speaker=spk,
                is_new=True,
                engine_available=True,
            )

        return IdentifyOutcome(
            matched=False,
            score=max(score, 0.0),
            threshold=effective_threshold,
            speaker=None,
            is_new=False,
            engine_available=True,
        )

    # ---- 内部 ----

    def _embed_wav(self, wav_bytes: bytes) -> list[float]:
        try:
            audio, sr = decode_wav_bytes(wav_bytes)
        except AudioDecodeError as exc:
            raise SpeakerServiceError(str(exc)) from exc
        vec = self._adapter.embed(audio, sample_rate=sr)
        if vec is None:
            raise SpeakerServiceError(
                "SVEngine 不可用或 embed 失败；检查 [sv] 依赖与 Ling 仓库路径"
            )
        return vec


_singleton: SpeakerService | None = None


def get_speaker_service() -> SpeakerService:
    global _singleton
    if _singleton is None:
        _singleton = SpeakerService()
    return _singleton


def set_speaker_service_for_tests(svc: SpeakerService | None) -> None:
    global _singleton
    _singleton = svc


__all__ = [
    "DEFAULT_THRESHOLD",
    "IdentifyOutcome",
    "SpeakerService",
    "SpeakerServiceError",
    "get_speaker_service",
    "set_speaker_service_for_tests",
]
