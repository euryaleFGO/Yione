"""M16：/api/speakers/* 端到端协议测试。

用 FakeService 替换 singleton，绕开真的 SVEngine + 音频解码。重点是验证：
- 上传 multipart 文件能正确拿到字节流并转发给 service
- session_id 绑定的 WS 连接在 identify 命中时能收到 speaker_detected
- 404 / 400 / 503 各种错误路径
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.speaker import Speaker
from app.repositories.speaker_repo import (
    JsonFileSpeakerRepo,
    set_speaker_repo_for_tests,
)
from app.schemas.speaker import SpeakerProfile
from app.services.speaker_service import (
    IdentifyOutcome,
    SpeakerService,
    SpeakerServiceError,
    set_speaker_service_for_tests,
)


class _FakeService(SpeakerService):
    """完全重写 wav 通道，embed_map 决定每个 bytes 映射成哪个说话人。"""

    def __init__(self, repo: JsonFileSpeakerRepo) -> None:
        super().__init__(adapter=_DummyAdapter(), repo=repo)  # type: ignore[arg-type]
        # bytes 内容 → 预置 outcome
        self.planned_register: dict[bytes, str] = {}
        self.planned_identify: dict[bytes, IdentifyOutcome] = {}
        self.raise_on_register: Exception | None = None

    def register_from_wav(self, wav_bytes: bytes, *, name: str | None = None) -> Speaker:
        if self.raise_on_register is not None:
            raise self.raise_on_register
        return self.register_from_vector([1.0, 0.0, 0.0], name=name)

    def identify_from_wav(
        self,
        wav_bytes: bytes,
        *,
        threshold: float | None = None,
        auto_enroll: bool = False,
    ) -> IdentifyOutcome:
        return self.planned_identify.get(
            wav_bytes,
            IdentifyOutcome(
                matched=False,
                score=0.0,
                threshold=threshold or 0.38,
                speaker=None,
                is_new=False,
                engine_available=True,
            ),
        )


class _DummyAdapter:
    threshold = 0.38
    is_available = True
    load_error = None

    def embed(self, audio: Any, sample_rate: int = 16000) -> list[float] | None:
        return [1.0, 0.0, 0.0]


@pytest.fixture
def svc(tmp_path: Path) -> _FakeService:
    repo = JsonFileSpeakerRepo(path=tmp_path / "speakers.json")
    set_speaker_repo_for_tests(repo)
    fake = _FakeService(repo)
    set_speaker_service_for_tests(fake)
    yield fake
    set_speaker_service_for_tests(None)
    set_speaker_repo_for_tests(None)


def test_register_returns_speaker_info(client: TestClient, svc: _FakeService) -> None:
    resp = client.post(
        "/api/speakers/register",
        files={"audio": ("sample.wav", b"fake-wav-bytes", "audio/wav")},
        data={"name": "alice"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["speaker"]["name"] == "alice"
    assert body["speaker"]["enrolled_samples"] == 1
    assert body["embedding_dim"] == 3
    # voiceprint 不能泄露
    assert "voiceprint" not in body["speaker"]


def test_register_rejects_empty_audio(client: TestClient, svc: _FakeService) -> None:
    resp = client.post(
        "/api/speakers/register",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 400


def test_register_503_when_service_error(client: TestClient, svc: _FakeService) -> None:
    svc.raise_on_register = SpeakerServiceError("引擎不可用")
    resp = client.post(
        "/api/speakers/register",
        files={"audio": ("sample.wav", b"xxx", "audio/wav")},
    )
    assert resp.status_code == 503


def test_list_and_patch_and_delete(client: TestClient, svc: _FakeService) -> None:
    # 先登记一个
    resp = client.post(
        "/api/speakers/register",
        files={"audio": ("sample.wav", b"aaa", "audio/wav")},
        data={"name": "alice"},
    )
    sid = resp.json()["speaker"]["id"]

    # list
    listed = client.get("/api/speakers").json()
    assert any(s["id"] == sid for s in listed)

    # patch name + profile
    patch = client.patch(
        f"/api/speakers/{sid}",
        json={"name": "Alice Lee", "profile": {"nickname": "小爱", "preferences": {"tone": "gentle"}}},
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "Alice Lee"
    assert patch.json()["profile"]["nickname"] == "小爱"

    # patch 不存在的 id → 404
    miss = client.patch("/api/speakers/spk_nope", json={"name": "?"})
    assert miss.status_code == 404

    # delete
    gone = client.delete(f"/api/speakers/{sid}")
    assert gone.status_code == 204

    # 二次删 → 404
    again = client.delete(f"/api/speakers/{sid}")
    assert again.status_code == 404


def test_identify_miss(client: TestClient, svc: _FakeService) -> None:
    resp = client.post(
        "/api/speakers/identify",
        files={"audio": ("q.wav", b"query-bytes", "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is False
    assert body["speaker"] is None
    assert body["engine_available"] is True


def test_identify_hit_pushes_ws_event(client: TestClient, svc: _FakeService) -> None:
    # 先建一个说话人
    spk = Speaker(
        id="spk_demo",
        name="demo",
        voiceprint=[1.0, 0.0, 0.0],
        profile=SpeakerProfile(),
        enrolled_samples=1,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    # 预置 identify 命中这条
    query_bytes = b"hit-query"
    svc.planned_identify[query_bytes] = IdentifyOutcome(
        matched=True,
        score=0.91,
        threshold=0.38,
        speaker=spk,
        is_new=False,
        engine_available=True,
    )

    # 开一条 WS，然后在另一条连接上发 identify，期望 WS 收到 speaker_detected
    session_id = client.post("/api/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/chat?session_id={session_id}") as ws:
        # 先把初始 state=idle 消掉
        assert ws.receive_json()["type"] == "state"

        resp = client.post(
            "/api/speakers/identify",
            files={"audio": ("q.wav", query_bytes, "audio/wav")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched"] is True
        assert body["speaker"]["id"] == "spk_demo"

        # WS 端应当收到 speaker_detected 事件
        got_event = False
        for _ in range(5):
            ev = ws.receive_json()
            if ev.get("type") == "speaker_detected":
                assert ev["speaker_id"] == "spk_demo"
                assert ev["name"] == "demo"
                assert ev["is_new"] is False
                assert ev["confidence"] > 0.9
                got_event = True
                break
        assert got_event


def test_identify_auto_enroll_new_speaker(client: TestClient, svc: _FakeService) -> None:
    query_bytes = b"novel-voice"
    new_spk = Speaker(
        id="spk_new",
        name=None,
        voiceprint=[0.0, 1.0, 0.0],
        profile=SpeakerProfile(),
        enrolled_samples=1,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    svc.planned_identify[query_bytes] = IdentifyOutcome(
        matched=True,
        score=0.0,
        threshold=0.38,
        speaker=new_spk,
        is_new=True,
        engine_available=True,
    )
    resp = client.post(
        "/api/speakers/identify",
        files={"audio": ("q.wav", query_bytes, "audio/wav")},
        data={"auto_enroll": "true"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_new"] is True
    assert body["speaker"]["id"] == "spk_new"
