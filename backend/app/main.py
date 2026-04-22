"""FastAPI entry point for webLing backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BACKEND_ROOT, get_settings
from app.integrations.ling_adapter import inject_ling_path
from app.routers import chat, health, sessions
from app.ws import chat_ws

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    inject_ling_path(settings.ling_repo_path)
    logger.info("webLing backend started (env=%s, port=%s).", settings.env, settings.port)
    yield
    logger.info("webLing backend stopped.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="webLing API",
        version="0.0.1",
        description="玲 Web 应用的后端 API (FastAPI)。",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = BACKEND_ROOT / "app" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(health.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(chat_ws.router)

    return app


app = create_app()
