"""REST endpoints for reading and updating app settings."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from config.settings import settings
from backend.schemas import SettingsResponse, SettingsUpdateRequest

router = APIRouter()
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Read current application settings."""
    return SettingsResponse(
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
        groq_api_key="••••" + settings.GROQ_API_KEY[-4:] if settings.GROQ_API_KEY else "",
        openai_api_key="••••" + settings.OPENAI_API_KEY[-4:] if settings.OPENAI_API_KEY else "",
        anthropic_api_key="••••" + settings.ANTHROPIC_API_KEY[-4:] if settings.ANTHROPIC_API_KEY else "",
        google_api_key="••••" + settings.GOOGLE_API_KEY[-4:] if settings.GOOGLE_API_KEY else "",
        deepseek_api_key="••••" + settings.DEEPSEEK_API_KEY[-4:] if settings.DEEPSEEK_API_KEY else "",
        xai_api_key="••••" + settings.XAI_API_KEY[-4:] if settings.XAI_API_KEY else "",
        together_api_key="••••" + settings.TOGETHER_API_KEY[-4:] if settings.TOGETHER_API_KEY else "",
        openrouter_api_key="••••" + settings.OPENROUTER_API_KEY[-4:] if settings.OPENROUTER_API_KEY else "",
        groq_default_model=settings.GROQ_DEFAULT_MODEL,
        openai_default_model=settings.OPENAI_DEFAULT_MODEL,
        anthropic_default_model=settings.ANTHROPIC_DEFAULT_MODEL,
        google_default_model=settings.GOOGLE_DEFAULT_MODEL,
        deepseek_default_model=settings.DEEPSEEK_DEFAULT_MODEL,
        xai_default_model=settings.XAI_DEFAULT_MODEL,
        together_default_model=settings.TOGETHER_DEFAULT_MODEL,
        openrouter_default_model=settings.OPENROUTER_DEFAULT_MODEL,
        ollama_default_model=settings.OLLAMA_DEFAULT_MODEL,
        max_upload_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        cache_ttl_seconds=settings.CACHE_TTL_SECONDS,
        available_providers=settings.available_llm_providers,
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdateRequest):
    """Update select application settings (writes to .env file)."""
    updates = {}
    if req.groq_default_model is not None:
        updates["GROQ_DEFAULT_MODEL"] = req.groq_default_model
    if req.openai_default_model is not None:
        updates["OPENAI_DEFAULT_MODEL"] = req.openai_default_model
    if req.anthropic_default_model is not None:
        updates["ANTHROPIC_DEFAULT_MODEL"] = req.anthropic_default_model
    if req.google_default_model is not None:
        updates["GOOGLE_DEFAULT_MODEL"] = req.google_default_model
    if req.deepseek_default_model is not None:
        updates["DEEPSEEK_DEFAULT_MODEL"] = req.deepseek_default_model
    if req.xai_default_model is not None:
        updates["XAI_DEFAULT_MODEL"] = req.xai_default_model
    if req.together_default_model is not None:
        updates["TOGETHER_DEFAULT_MODEL"] = req.together_default_model
    if req.openrouter_default_model is not None:
        updates["OPENROUTER_DEFAULT_MODEL"] = req.openrouter_default_model
    if req.max_upload_size_mb is not None:
        updates["MAX_UPLOAD_SIZE_MB"] = str(req.max_upload_size_mb)
    if req.cache_ttl_seconds is not None:
        updates["CACHE_TTL_SECONDS"] = str(req.cache_ttl_seconds)

    if updates and ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
        for i, line in enumerate(lines):
            for key, value in updates.items():
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    break
        ENV_PATH.write_text("\n".join(lines) + "\n")

        # Reload settings
        import importlib
        importlib.reload(settings.__class__)

    return await get_settings()
