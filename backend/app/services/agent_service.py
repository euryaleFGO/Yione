"""Agent service — thin wrapper over Ling's ``Agent``.

M1 behaviour:
- If the Ling repo is on ``sys.path`` and imports succeed, use the real Agent.
- Otherwise fall back to an echo stub so the rest of the stack stays testable
  when Ling isn't available (e.g. CI without Ling).

The real Agent's ``chat(stream=True)`` is a *synchronous* generator. We wrap it
with ``anyio.to_thread`` so FastAPI's event loop stays unblocked.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol

import anyio

logger = logging.getLogger(__name__)


class _AgentLike(Protocol):
    def chat(self, message: str, stream: bool = True) -> Iterator[str]: ...


def _try_load_ling_agent() -> _AgentLike | None:
    try:
        from src.backend.llm.agent.agent import Agent  # type: ignore[import-not-found]
    except Exception as exc:
        logger.warning("Ling Agent unavailable (%s); using echo fallback.", exc)
        return None
    try:
        return Agent(user_id="webling_default", enable_tools=False)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("Ling Agent init failed (%s); using echo fallback.", exc)
        return None


class _EchoAgent:
    """Deterministic stub used when Ling is unreachable."""

    def chat(self, message: str, stream: bool = True) -> Iterator[str]:
        del stream  # echo is not actually streaming
        prefix = "（echo stub）你说："
        yield from (prefix, message)


class AgentService:
    """Per-process singleton wrapper. Not thread-safe by design (M1)."""

    def __init__(self, agent: _AgentLike | None = None) -> None:
        self._agent: _AgentLike = agent or _try_load_ling_agent() or _EchoAgent()
        self._is_echo = isinstance(self._agent, _EchoAgent)

    @property
    def is_echo(self) -> bool:
        return self._is_echo

    async def stream_reply(self, text: str) -> AsyncIterator[str]:
        """Stream text chunks of the reply. Bridges sync generator → async."""
        # Collect in a worker thread to keep the event loop free. We read the
        # whole generator because bridging a *pull-based* sync generator to an
        # async iterator without a thread-per-call is fiddly; a small reply is
        # fine for M1. M4 will switch to a proper streaming bridge.
        chunks: list[str] = await anyio.to_thread.run_sync(
            lambda: list(self._agent.chat(text, stream=True))
        )
        for chunk in chunks:
            yield chunk

    async def reply_text(self, text: str) -> str:
        """Non-streaming convenience (POST /api/chat)."""
        parts = [c async for c in self.stream_reply(text)]
        return "".join(parts)


_singleton: AgentService | None = None


def get_agent_service() -> AgentService:
    global _singleton
    if _singleton is None:
        _singleton = AgentService()
    return _singleton


# Mark Any re-export to avoid unused import noise.
_ = Any
