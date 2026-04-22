"""Inject the Ling repo into sys.path so its modules can be imported.

Ling is consumed as a read-only sibling project. We deliberately do NOT package
it — instead we extend sys.path at process startup so that
``from src.backend.llm.agent import Agent`` keeps working.

The actual Agent adapter lives in services/agent_service.py; this module is just
the bootstrap hook.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def inject_ling_path(ling_repo_path: str | Path) -> Path | None:
    """Prepend the Ling repo root to sys.path.

    Returns the resolved path on success, None if the path is missing.
    Does not raise: Phase-1 M0 boots even when Ling is unavailable so we can
    develop the shell before wiring the agent.
    """
    root = Path(ling_repo_path).expanduser().resolve()
    if not root.exists():
        logger.warning("Ling repo not found at %s — agent will be unavailable.", root)
        return None

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
        logger.info("Injected Ling path into sys.path: %s", root_str)
    return root
