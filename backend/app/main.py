"""FastAPI entry point for webLing backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import BACKEND_ROOT, PROJECT_ROOT, get_settings
from app.db import close_db, init_db
from app.integrations.ling_adapter import inject_ling_path
from app.routers import characters, chat, embed, games, health, metrics, prompts, sessions, speakers, tts
from app.services.session_service import SessionService, set_session_service
from app.services.tenant_service import TenantService, get_tenant_service
from app.ws import chat_ws

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    inject_ling_path(settings.ling_repo_path)
    await init_db(app)

    # 注入 MongoDB repo 到 services
    db = getattr(app.state, "db", None)
    if db is not None:
        from app.repositories.mongo_session_repo import MongoSessionRepo
        from app.repositories.mongo_speaker_repo import MongoSpeakerRepo
        from app.repositories.mongo_tenant_repo import MongoTenantRepo

        session_repo = MongoSessionRepo(db)
        set_session_service(SessionService(repo=session_repo))

        mongo_tenant_repo = MongoTenantRepo(db)
        await mongo_tenant_repo.load_all()
        tenant_svc = get_tenant_service()
        tenant_svc._mongo_repo = mongo_tenant_repo

        mongo_speaker_repo = MongoSpeakerRepo(db)
        await mongo_speaker_repo.load_all()
        from app.services.speaker_service import get_speaker_service
        speaker_svc = get_speaker_service()
        speaker_svc._repo = mongo_speaker_repo

    logger.info("webLing backend started (env=%s, port=%s).", settings.env, settings.port)
    yield
    await close_db(app)
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

    # M8: 挂载 embed 构建产物（embed.js + embed.html）
    embed_dir = PROJECT_ROOT / "apps" / "embed" / "dist"
    if embed_dir.exists():
        app.mount("/embed", StaticFiles(directory=str(embed_dir)), name="embed")

    app.include_router(health.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(tts.router, prefix="/api")
    app.include_router(embed.router, prefix="/api")
    app.include_router(speakers.router, prefix="/api")
    app.include_router(characters.router, prefix="/api")
    app.include_router(prompts.router, prefix="/api")
    app.include_router(games.router, prefix="/api")
    app.include_router(metrics.router)
    app.include_router(chat_ws.router)

    return app


app = create_app()
