"""Centralized configuration loaded from environment variables."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def _bool(val: str | bool | None, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "y", "on")


def _int(val: str | int | None, default: int) -> int:
    if isinstance(val, int):
        return val
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _str(val: str | None, default: str = "") -> str:
    return val if val else default


class Settings:
    """Application settings from environment / .env file."""

    # ── App ──
    APP_NAME: str = _str(os.getenv("APP_NAME"), "Instant BI")
    APP_THEME: str = _str(os.getenv("APP_THEME"), "light")
    DEBUG: bool = _bool(os.getenv("DEBUG"), False)
    SECRET_KEY: str = _str(os.getenv("SECRET_KEY"), "change-me-in-production")

    # ── Upload ──
    MAX_UPLOAD_SIZE_MB: int = _int(os.getenv("MAX_UPLOAD_SIZE_MB"), 200)
    UPLOAD_DIR: Path = Path(__file__).parent.parent / "uploads"

    # ── Cache ──
    CACHE_TTL_SECONDS: int = _int(os.getenv("CACHE_TTL_SECONDS"), 3600)

    # ── LLM Providers ──
    OPENAI_API_KEY: str = _str(os.getenv("OPENAI_API_KEY"))
    OPENAI_DEFAULT_MODEL: str = _str(os.getenv("OPENAI_DEFAULT_MODEL"), "gpt-4o")

    ANTHROPIC_API_KEY: str = _str(os.getenv("ANTHROPIC_API_KEY"))
    ANTHROPIC_DEFAULT_MODEL: str = _str(os.getenv("ANTHROPIC_DEFAULT_MODEL"), "claude-sonnet-4-6")

    GOOGLE_API_KEY: str = _str(os.getenv("GOOGLE_API_KEY"))
    GOOGLE_DEFAULT_MODEL: str = _str(os.getenv("GOOGLE_DEFAULT_MODEL"), "gemini-2.0-flash")

    GROQ_API_KEY: str = _str(os.getenv("GROQ_API_KEY"))
    GROQ_DEFAULT_MODEL: str = _str(os.getenv("GROQ_DEFAULT_MODEL"), "llama3-70b-8192")

    OLLAMA_BASE_URL: str = _str(os.getenv("OLLAMA_BASE_URL"), "http://localhost:11434")
    OLLAMA_DEFAULT_MODEL: str = _str(os.getenv("OLLAMA_DEFAULT_MODEL"), "llama3.1")

    # ── DeepSeek ──
    DEEPSEEK_API_KEY: str = _str(os.getenv("DEEPSEEK_API_KEY"))
    DEEPSEEK_DEFAULT_MODEL: str = _str(os.getenv("DEEPSEEK_DEFAULT_MODEL"), "deepseek-chat")

    # ── xAI (Grok) ──
    XAI_API_KEY: str = _str(os.getenv("XAI_API_KEY"))
    XAI_DEFAULT_MODEL: str = _str(os.getenv("XAI_DEFAULT_MODEL"), "grok-2")

    # ── Together AI ──
    TOGETHER_API_KEY: str = _str(os.getenv("TOGETHER_API_KEY"))
    TOGETHER_DEFAULT_MODEL: str = _str(os.getenv("TOGETHER_DEFAULT_MODEL"), "meta-llama/Llama-3.3-70B-Instruct-Turbo")

    # ── OpenRouter ──
    OPENROUTER_API_KEY: str = _str(os.getenv("OPENROUTER_API_KEY"))
    OPENROUTER_DEFAULT_MODEL: str = _str(os.getenv("OPENROUTER_DEFAULT_MODEL"), "openai/gpt-4o")

    # ── Database connections ──
    POSTGRES_HOST: str = _str(os.getenv("POSTGRES_HOST"))
    POSTGRES_PORT: int = _int(os.getenv("POSTGRES_PORT"), 5432)
    POSTGRES_DB: str = _str(os.getenv("POSTGRES_DB"))
    POSTGRES_USER: str = _str(os.getenv("POSTGRES_USER"))
    POSTGRES_PASSWORD: str = _str(os.getenv("POSTGRES_PASSWORD"))

    @property
    def postgres_url(self) -> str | None:
        if all([self.POSTGRES_HOST, self.POSTGRES_DB, self.POSTGRES_USER, self.POSTGRES_PASSWORD]):
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return None

    @property
    def available_llm_providers(self) -> list[str]:
        providers = []
        if self.GROQ_API_KEY:
            providers.append("groq")
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if self.GOOGLE_API_KEY:
            providers.append("google")
        if self.DEEPSEEK_API_KEY:
            providers.append("deepseek")
        if self.XAI_API_KEY:
            providers.append("xai")
        if self.TOGETHER_API_KEY:
            providers.append("together")
        if self.OPENROUTER_API_KEY:
            providers.append("openrouter")
        try:
            import ollama  # noqa: F401
            providers.append("ollama")
        except ImportError:
            pass
        return providers

    @property
    def upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
