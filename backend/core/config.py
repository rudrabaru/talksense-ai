"""
TalkSense AI — App Configuration

Loads all settings from environment variables / .env file.
Uses pydantic-settings for type-safe config with defaults.
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            ".env",
            ".env.local",
            "../.env",
            "../.env.local",
            Path.home() / ".talksense.env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/talksense"

    # ── JWT Auth ──────────────────────────────────────────
    jwt_secret_key: str = "changeme_generate_with_secrets_token_hex_32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── Hugging Face ──────────────────────────────────────
    hf_token: str = ""

    # ── Whisper ───────────────────────────────────────────
    whisper_model: str = "small"
    whisper_compute_type: str = "int8"
    whisper_device: str = "cuda"
    whisper_language: str = ""   # e.g. "en"; empty = auto-detect (multilingual)

    # ── Pyannote ──────────────────────────────────────────
    pyannote_enabled: bool = True
    pyannote_device: str = "cuda"

    # ── Gemini (LLM Role Classification) ──────────────────
    gemini_api_key: str = ""

    # ── App ───────────────────────────────────────────────
    env: str = "development"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (loaded once on first call)."""
    return Settings()
