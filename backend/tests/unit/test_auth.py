"""M6 鉴权单测：JWT 签发/校验 + embed token 端点 + tenant 校验。"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services import auth_service, tenant_service


def test_encode_decode_roundtrip() -> None:
    token, expires_in = auth_service.issue_embed_token("demo")
    assert isinstance(token, str) and token.count(".") == 2
    assert expires_in > 0
    claims = auth_service.decode_token(token)
    assert claims.tenant_id == "demo"
    assert claims.kind == "embed"
    assert "chat" in claims.scope
    assert claims.exp > claims.iat


def test_decode_rejects_tampered_token() -> None:
    token, _ = auth_service.issue_embed_token("demo")
    header, payload, sig = token.split(".")
    # 反转签名段 —— 非空改动，签名校验必然失败
    bad = f"{header}.{payload}.{sig[::-1]}"
    with pytest.raises(auth_service.AuthError):
        auth_service.decode_token(bad)


def test_decode_rejects_tampered_payload() -> None:
    token, _ = auth_service.issue_embed_token("demo")
    header, payload, sig = token.split(".")
    # 往 payload 段里插一个字符，签名校验应失败
    bad = f"{header}.{payload}X.{sig}"
    with pytest.raises(auth_service.AuthError):
        auth_service.decode_token(bad)


def test_decode_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    # 手动构造一个 exp 已经在过去的 token，避免 sleep 带来的不稳定
    real_time = time.time

    def fake_time_past() -> float:
        return real_time() - 3600

    monkeypatch.setattr(auth_service.time, "time", fake_time_past)
    token, _ = auth_service.issue_embed_token("demo", ttl_seconds=60)
    monkeypatch.setattr(auth_service.time, "time", real_time)

    with pytest.raises(auth_service.AuthError):
        auth_service.decode_token(token)


def test_tenant_service_dev_fallback_accepts_any_key(tmp_path: Path) -> None:
    # 指向一个不存在的文件 → 应该进 dev fallback，任意 key 返回 demo tenant
    svc = tenant_service.TenantService(path=tmp_path / "missing.json")
    t = svc.verify_api_key("whatever")
    assert t is not None
    assert t.id == "demo"


def test_tenant_service_hash_match(tmp_path: Path) -> None:
    api_key = "test-key-xyz"
    digest = hashlib.sha256(api_key.encode()).hexdigest()
    path = tmp_path / "tenants.json"
    path.write_text(
        json.dumps(
            {
                "tenants": [
                    {
                        "id": "acme",
                        "api_key_hash": digest,
                        "allowed_origins": ["http://example.com"],
                        "character_whitelist": ["ling"],
                        "daily_quota": 100,
                        "scope": ["chat"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    svc = tenant_service.TenantService(path=path)

    assert svc.verify_api_key("wrong") is None
    t = svc.verify_api_key(api_key)
    assert t is not None
    assert t.id == "acme"
    assert t.origin_allowed("http://example.com")
    assert not t.origin_allowed("http://evil.com")
    assert t.character_allowed("ling")
    assert not t.character_allowed("xiaolv")


def test_embed_token_endpoint_happy_path(client: TestClient) -> None:
    # dev fallback 下 demo tenant 的 origin 白名单为空 → 默认放行
    resp = client.post(
        "/api/embed/token",
        headers={"X-API-Key": "demo-key"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_id"] == "demo"
    assert body["expires_in"] > 0
    claims = auth_service.decode_token(body["token"])
    assert claims.tenant_id == "demo"
    assert claims.kind == "embed"


def test_embed_token_endpoint_rejects_missing_key(client: TestClient) -> None:
    resp = client.post("/api/embed/token")
    assert resp.status_code == 401


def test_embed_token_endpoint_enforces_origin(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 装一个只放行 example.com 的 tenant，然后不带 Origin 请求，应该 403
    api_key = "strict-key"
    digest = hashlib.sha256(api_key.encode()).hexdigest()
    path = tmp_path / "tenants.json"
    path.write_text(
        json.dumps(
            {
                "tenants": [
                    {
                        "id": "strict",
                        "api_key_hash": digest,
                        "allowed_origins": ["https://example.com"],
                        "character_whitelist": [],
                        "daily_quota": 100,
                        "scope": ["chat", "embed"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    svc = tenant_service.TenantService(path=path)
    monkeypatch.setattr(tenant_service, "_singleton", svc)

    # 没带 Origin → 403
    bad = client.post("/api/embed/token", headers={"X-API-Key": api_key})
    assert bad.status_code == 403

    # 带上白名单里的 Origin → 200
    ok = client.post(
        "/api/embed/token",
        headers={"X-API-Key": api_key, "Origin": "https://example.com"},
    )
    assert ok.status_code == 200, ok.text
