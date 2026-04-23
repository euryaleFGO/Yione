"""Application settings loaded from environment variables (.env supported)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"],
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -- runtime --
    env: str = Field(default="development", alias="WEBLING_ENV")
    host: str = Field(default="0.0.0.0", alias="WEBLING_HOST")
    port: int = Field(default=8000, alias="WEBLING_PORT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="WEBLING_CORS_ORIGINS",
    )

    # -- Ling integration --
    ling_repo_path: str = Field(
        default="/Users/zert/Work/zert/lkl_code/Ling",
        alias="LING_REPO_PATH",
    )

    # -- LLM --
    llm_base_url: str = Field(default="http://192.168.251.56:8080/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="dummy", alias="LLM_API_KEY")
    llm_model: str = Field(default="MiniMax-M2.5", alias="LLM_MODEL")

    # -- TTS --
    tts_base_url: str = Field(default="http://192.168.251.56:5001", alias="TTS_BASE_URL")
    tts_default_spk_id: str = Field(default="", alias="TTS_DEFAULT_SPK_ID")
    tts_cache_dir: str = Field(default="backend/app/static/tts", alias="TTS_CACHE_DIR")
    tts_cache_ttl_seconds: int = Field(default=3600, alias="TTS_CACHE_TTL_SECONDS")

    # -- Mongo --
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="webling", alias="MONGO_DB")

    # -- Auth --
    jwt_secret: str = Field(default="change-me-in-prod", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_embed_ttl_seconds: int = Field(default=3600, alias="JWT_EMBED_TTL_SECONDS")
    jwt_refresh_ttl_seconds: int = Field(default=86400, alias="JWT_REFRESH_TTL_SECONDS")

    # -- limits --
    rate_limit_per_min: int = Field(default=60, alias="RATE_LIMIT_PER_MIN")
    quota_per_day: int = Field(default=2000, alias="QUOTA_PER_DAY")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
