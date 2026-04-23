"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import agent_service


@pytest.fixture(autouse=True)
def _force_echo_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the AgentService singleton to echo mode for tests.

    Unit tests should never reach out to a real LLM endpoint; forcing
    ``_agent = None`` keeps the service deterministic and offline.
    """
    svc = agent_service.AgentService()
    svc._agent = None  # type: ignore[attr-defined]
    monkeypatch.setattr(agent_service, "_singleton", svc)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
