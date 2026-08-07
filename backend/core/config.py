"""
TalkSense AI — App Configuration

Loads all settings from environment variables / .env file.
Uses pydantic-settings for type-safe config with defaults.
"""

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor all paths to this file's location, never os.getcwd().
# config.py lives at backend/core/config.py, so:
#   _BACKEND_DIR = backend/
#   _PROJECT_DIR = talksense-ai/  (repository root)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_DIR = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Pydantic v2 loads env files in order. Later files override earlier files.
        # Order: Global -> Root Project -> Backend -> Backend Local
        # All paths are absolute — CWD has zero effect.
        env_file=(
            Path.home() / ".talksense.env",
            _PROJECT_DIR / ".env",
            _PROJECT_DIR / ".env.local",
            _BACKEND_DIR / ".env",
            _BACKEND_DIR / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/talksense"
    )

    # ── JWT Auth ──────────────────────────────────────────
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── Hugging Face ──────────────────────────────────────
    hf_token: str = ""

    # ── Whisper ───────────────────────────────────────────
    whisper_model: str = "small"
    whisper_compute_type: str = "int8"
    whisper_device: str = "cuda"
    whisper_language: str = ""  # e.g. "en"; empty = auto-detect (multilingual)
    gpu_concurrency: int = Field(
        default=3, description="Concurrent GPU inference requests"
    )

    # ── Gemini (LLM Role Classification) ──────────────────
    gemini_api_key: str = ""

    # ── Post-Session AI ───────────────────────────────────
    enable_post_session_ai: bool = False
    post_session_provider: str = "gemini"
    post_session_model: str = "gemini-1.5-flash"
    post_session_prompt_version: str = "v1"
    post_session_timeout: int = 30

    # ── App ───────────────────────────────────────────────
    env: str = "development"
    cors_origins: str = "http://localhost:5173"
    profiling_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (loaded once on first call)."""
    return Settings()
