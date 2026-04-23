"""M16：SpeakerService 业务逻辑（用 vector 级接口绕开音频依赖）。

identify 分支覆盖：
  - 引擎不可用 → engine_available=False
  - 未命中 & auto_enroll=False → matched=False
  - 未命中 & auto_enroll=True → 自动创建新说话人，is_new=True
  - 命中 → matched=True，且 voiceprint 会被合并
  - 维度不一致的旧条目应被跳过而不是崩
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.integrations.ling_sv_adapter import SVAdapter
from app.repositories.speaker_repo import JsonFileSpeakerRepo
from app.services.speaker_service import SpeakerService


@dataclass
class _FakeAdapter:
    """绕开真实 SVEngine 的最小替身，threshold 对齐默认值。"""

    available: bool = True
    threshold: float = 0.38

    @property
    def is_available(self) -> bool:
        return self.available

    @property
    def load_error(self) -> str | None:
        return None if self.available else "stub"

    def embed(self, audio, sample_rate: int = 16000):
        # 本测试文件不用这个方法，所有测试直接走 *_from_vector
        return None


def _make_service(tmp_path: Path, available: bool = True) -> tuple[SpeakerService, _FakeAdapter]:
    adapter = _FakeAdapter(available=available)
    repo = JsonFileSpeakerRepo(path=tmp_path / "speakers.json")
    svc = SpeakerService(adapter=adapter, repo=repo)  # type: ignore[arg-type]
    return svc, adapter


def _normed(vec: list[float]) -> list[float]:
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec]


def test_register_from_vector_roundtrip(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path)
    spk = svc.register_from_vector([1.0, 0.0, 0.0], name="alice")
    assert spk.id.startswith("spk_")
    assert spk.name == "alice"
    assert svc.get(spk.id).name == "alice"
    assert len(svc.list_all()) == 1


def test_identify_no_match_when_library_empty(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path)
    out = svc.identify_from_vector(_normed([1.0, 0.0]))
    assert out.engine_available is True
    assert out.matched is False
    assert out.speaker is None


def test_identify_hit_merges_voiceprint(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path)
    existing = svc.register_from_vector(_normed([1.0, 0.1, 0.0]), name="alice")
    # 一个很相近的向量（与 existing 内积 > 0.38）
    out = svc.identify_from_vector(_normed([1.0, 0.15, 0.05]))
    assert out.matched is True
    assert out.speaker is not None
    assert out.speaker.id == existing.id
    # 命中后 enrolled_samples 应该涨到 2
    refreshed = svc.get(existing.id)
    assert refreshed.enrolled_samples == 2


def test_identify_miss_without_auto_enroll(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path)
    svc.register_from_vector(_normed([1.0, 0.0, 0.0]), name="alice")
    # 与 alice 几乎正交 → 低于 0.38 阈值
    out = svc.identify_from_vector(_normed([0.0, 1.0, 0.0]))
    assert out.matched is False
    assert out.speaker is None
    assert len(svc.list_all()) == 1


def test_identify_miss_with_auto_enroll_creates_new(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path)
    svc.register_from_vector(_normed([1.0, 0.0, 0.0]), name="alice")
    out = svc.identify_from_vector(_normed([0.0, 1.0, 0.0]), auto_enroll=True)
    assert out.matched is True
    assert out.is_new is True
    assert out.speaker is not None
    assert out.speaker.name is None  # 自动注册不带名字
    assert len(svc.list_all()) == 2


def test_identify_skips_dim_mismatch_entries(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path)
    # 一条 3 维（旧模型），一条 4 维（与查询同维）
    svc.register_from_vector(_normed([1.0, 0.0, 0.0]), name="legacy")
    svc.register_from_vector(_normed([1.0, 0.0, 0.0, 0.0]), name="current")
    out = svc.identify_from_vector(_normed([0.98, 0.1, 0.1, 0.1]))
    assert out.matched is True
    assert out.speaker.name == "current"


def test_identify_engine_unavailable_returns_false(tmp_path: Path) -> None:
    svc, _ = _make_service(tmp_path, available=False)
    out = svc.identify_from_wav(b"whatever")
    assert out.engine_available is False
    assert out.matched is False
    assert out.speaker is None


def test_adapter_interface_matches_real_adapter() -> None:
    """确保 _FakeAdapter 的形状跟真正 SVAdapter 对得上，接口漂移早报错。"""
    real = SVAdapter(threshold=0.38)
    fake = _FakeAdapter()
    for attr in ("is_available", "load_error", "threshold", "embed"):
        assert hasattr(fake, attr), f"_FakeAdapter 缺少 {attr}"
        assert hasattr(real, attr), f"SVAdapter 缺少 {attr}"
