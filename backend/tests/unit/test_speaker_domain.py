"""M16 领域对象：余弦相似度、向量合并、SpeakerInfo 转换。"""

from __future__ import annotations

from app.domain.speaker import Speaker, cosine_similarity, new_speaker
from app.schemas.speaker import SpeakerProfile


def test_cosine_similarity_orthogonal() -> None:
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_identical() -> None:
    v = [0.6, 0.8, 0.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_length_mismatch_returns_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


def test_new_speaker_stamps_times_and_single_sample() -> None:
    spk = new_speaker(speaker_id="spk_1", voiceprint=[1.0, 0.0], name="alice")
    assert spk.enrolled_samples == 1
    assert spk.dim == 2
    assert spk.created_at == spk.updated_at


def test_merge_voiceprint_averages_and_renormalizes() -> None:
    spk = new_speaker(speaker_id="spk_1", voiceprint=[1.0, 0.0])
    spk.merge_voiceprint([0.0, 1.0])
    # 加权平均 (1,0) + (0,1) → (0.5, 0.5) 归一化 → (0.7071, 0.7071)
    assert spk.enrolled_samples == 2
    assert abs(spk.voiceprint[0] - spk.voiceprint[1]) < 1e-9
    norm = sum(v * v for v in spk.voiceprint) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_merge_voiceprint_rejects_dim_mismatch() -> None:
    spk = new_speaker(speaker_id="spk_1", voiceprint=[1.0, 0.0])
    try:
        spk.merge_voiceprint([1.0, 0.0, 0.0])
    except ValueError as exc:
        assert "维度不一致" in str(exc)
    else:
        raise AssertionError("应抛 ValueError")


def test_to_info_hides_voiceprint() -> None:
    spk = Speaker(
        id="spk_x",
        name="bob",
        voiceprint=[1.0, 0.0, 0.0],
        profile=SpeakerProfile(nickname="B"),
        enrolled_samples=5,
        created_at=__import__("datetime").datetime.fromisoformat("2026-04-23T00:00:00+00:00"),
        updated_at=__import__("datetime").datetime.fromisoformat("2026-04-23T01:00:00+00:00"),
    )
    info = spk.to_info()
    assert info.id == "spk_x"
    assert info.name == "bob"
    assert info.enrolled_samples == 5
    # SpeakerInfo pydantic model 不能有 voiceprint 字段
    assert "voiceprint" not in info.model_dump()
