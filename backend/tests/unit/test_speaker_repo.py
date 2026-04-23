"""M16：JsonFileSpeakerRepo 存取往返。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.domain.speaker import Speaker
from app.repositories.speaker_repo import JsonFileSpeakerRepo
from app.schemas.speaker import SpeakerProfile


def _make(speaker_id: str, vec: list[float], name: str | None = None) -> Speaker:
    now = datetime.now(tz=UTC)
    return Speaker(
        id=speaker_id,
        name=name,
        voiceprint=vec,
        profile=SpeakerProfile(nickname=name),
        enrolled_samples=1,
        created_at=now,
        updated_at=now,
    )


def test_save_and_list(tmp_path: Path) -> None:
    repo = JsonFileSpeakerRepo(path=tmp_path / "speakers.json")
    repo.save(_make("spk_a", [1.0, 0.0], "alice"))
    repo.save(_make("spk_b", [0.0, 1.0], "bob"))

    all_speakers = sorted(repo.list_all(), key=lambda s: s.id)
    assert [s.id for s in all_speakers] == ["spk_a", "spk_b"]
    assert repo.get("spk_a").name == "alice"


def test_persistence_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "speakers.json"
    r1 = JsonFileSpeakerRepo(path=path)
    r1.save(_make("spk_a", [1.0, 0.0], "alice"))

    r2 = JsonFileSpeakerRepo(path=path)
    spk = r2.get("spk_a")
    assert spk is not None
    assert spk.name == "alice"
    assert spk.voiceprint == [1.0, 0.0]


def test_delete(tmp_path: Path) -> None:
    repo = JsonFileSpeakerRepo(path=tmp_path / "speakers.json")
    repo.save(_make("spk_a", [1.0, 0.0]))
    assert repo.delete("spk_a") is True
    assert repo.delete("spk_a") is False
    assert repo.list_all() == []


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    repo = JsonFileSpeakerRepo(path=tmp_path / "nope.json")
    assert repo.list_all() == []
    assert repo.get("spk_x") is None
