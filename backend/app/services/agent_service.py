"""Agent service — talks to an OpenAI-compatible LLM endpoint.

Current default is the MiniMax-M2.5 instance deployed at
``LLM_BASE_URL`` (``/v1/chat/completions`` with SSE streaming).

M4+ reintroduces the Ling ``Agent`` with memory/RAG/tool-calling; until then
this lightweight adapter gives the UI real LLM output and keeps the rest of
the stack (WS / TTS / lipsync) exercised end-to-end. An echo stub covers the
case where the LLM server is unreachable so the UI never gets stuck.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "你是玲（Ling），一个 Live2D 虚拟助手。说话风格：自然口语、简洁，"
    "不使用 Markdown、列表或 emoji，因为你的回复会直接转成语音。"
    "单次回答 1-3 句为宜。"
)


class _OpenAIChatAgent:
    """Minimal OpenAI-compatible streaming client.

    Calls ``{base_url}/chat/completions`` with ``stream=true`` and yields
    `delta.content` chunks as they arrive (SSE ``data: {...}`` lines).
    """

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model = model
        # 5-min read timeout — MiniMax can take a beat before the first token.
        self._timeout = httpx.Timeout(300.0, connect=10.0)
        # Keep a persistent client so we reuse TCP.
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def stream(self, user_text: str) -> AsyncIterator[str]:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "stream": True,
            "temperature": 0.7,
        }
        client = await self._get_client()
        async with client.stream(
            "POST", url, headers=self._headers, json=payload
        ) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode("utf-8", errors="replace")[:500]
                raise RuntimeError(f"LLM HTTP {resp.status_code}: {body}")
            async for raw in resp.aiter_lines():
                line = raw.strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    logger.debug("skipping non-JSON SSE line: %r", data[:120])
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content


class AgentService:
    """Streaming chat wrapper around whichever backend ended up available."""

    def __init__(self, agent: _OpenAIChatAgent | None = None) -> None:
        if agent is not None:
            self._agent: _OpenAIChatAgent | None = agent
        else:
            s = get_settings()
            if s.llm_base_url and s.llm_api_key and s.llm_model:
                self._agent = _OpenAIChatAgent(s.llm_base_url, s.llm_api_key, s.llm_model)
            else:
                self._agent = None
                logger.warning("LLM not configured; falling back to echo stub")

    @property
    def is_echo(self) -> bool:
        return self._agent is None

    async def stream_reply(self, text: str) -> AsyncIterator[str]:
        """Yield reply chunks as the LLM streams them.

        Falls back to a deterministic echo on any transport/LLM error so
        downstream consumers (TTS, lipsync, UI) keep functioning.
        """
        if self._agent is None:
            prefix = "（echo stub）你说："
            for ch in (prefix, text):
                yield ch
            return

        try:
            async for chunk in self._agent.stream(text):
                yield chunk
        except Exception as exc:
            logger.warning("LLM stream failed (%s); echo fallback", exc)
            yield f"（LLM 错误：{exc}）"

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
