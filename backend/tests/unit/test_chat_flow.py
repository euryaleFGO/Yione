"""M1: exercise session + chat + WS end-to-end against the in-memory stack.

Uses the echo agent fallback when Ling isn't importable (CI default).
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_session_and_chat(client: TestClient) -> None:
    create = client.post("/api/sessions", json={"character_id": "ling"})
    assert create.status_code == 200, create.text
    sid = create.json()["session_id"]

    reply = client.post("/api/chat", json={"session_id": sid, "text": "你好"})
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert "你好" in body["reply"]  # echo stub includes the user text


def test_unknown_session_chat_404(client: TestClient) -> None:
    resp = client.post("/api/chat", json={"session_id": "sess_nope", "text": "hi"})
    assert resp.status_code == 404


def test_ws_user_message_echo(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={}).json()["session_id"]

    with client.websocket_connect(f"/ws/chat?session_id={sid}") as ws:
        # Initial state event
        first = ws.receive_json()
        assert first == {"type": "state", "value": "idle"}

        ws.send_json({"type": "user_message", "text": "ping"})

        processing = ws.receive_json()
        assert processing == {"type": "state", "value": "processing"}

        final_text = ""
        got_final = False
        # Expect some subtitle events (at least one, plus a final)
        for _ in range(10):
            msg = ws.receive_json()
            if msg["type"] == "subtitle":
                final_text = msg["text"]
                if msg["is_final"]:
                    got_final = True
                    break
        assert got_final, "never saw is_final subtitle"
        assert "ping" in final_text

        idle = ws.receive_json()
        assert idle == {"type": "state", "value": "idle"}
