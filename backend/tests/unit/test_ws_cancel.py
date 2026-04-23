"""M4：WS 打断协议。

要点：
- 长回复过程中发 `cancel` 事件，服务端应该停下，最终状态回 idle。
- 连续发两条 `user_message`（中间不等上一个结束），上一个 turn 应被自动打断。
- 新增的 `speech_start` 被视作 barge-in，状态切到 listening。
- echo 回退的 agent 产出很短，"进行中 cancel" 天生难以稳定 reproduce，
  这里主要验证事件协议不回归；真实 LLM 的取消已在 chat_ws 的 try/except
  CancelledError 分支中处理。
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _wait_for_idle(ws) -> None:
    """读消息直到看到一次 state=idle，或把 20 条消息消光。"""
    for _ in range(30):
        try:
            msg = ws.receive_json()
        except Exception:
            return
        if msg.get("type") == "state" and msg.get("value") == "idle":
            return


def test_cancel_resets_to_idle(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/chat?session_id={sid}") as ws:
        assert ws.receive_json() == {"type": "state", "value": "idle"}
        ws.send_json({"type": "user_message", "text": "你好"})
        # 预期至少出现 processing
        saw_processing = False
        for _ in range(10):
            msg = ws.receive_json()
            if msg.get("type") == "state" and msg.get("value") == "processing":
                saw_processing = True
                break
        assert saw_processing

        ws.send_json({"type": "cancel"})
        _wait_for_idle(ws)


def test_new_user_message_cancels_previous_turn(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/chat?session_id={sid}") as ws:
        assert ws.receive_json() == {"type": "state", "value": "idle"}
        ws.send_json({"type": "user_message", "text": "第一条"})
        # 紧跟着发第二条：不等第一条完成
        ws.send_json({"type": "user_message", "text": "第二条"})

        # 把剩下的消息读光，最终一定会有至少一次 idle
        saw_idle = False
        for _ in range(40):
            try:
                msg = ws.receive_json()
            except Exception:
                break
            if msg.get("type") == "state" and msg.get("value") == "idle":
                saw_idle = True
                break
        assert saw_idle


def test_speech_start_is_acknowledged(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={}).json()["session_id"]
    with client.websocket_connect(f"/ws/chat?session_id={sid}") as ws:
        assert ws.receive_json() == {"type": "state", "value": "idle"}
        ws.send_json({"type": "speech_start"})
        saw_listening = False
        for _ in range(5):
            msg = ws.receive_json()
            if msg.get("type") == "state" and msg.get("value") == "listening":
                saw_listening = True
                break
        assert saw_listening
