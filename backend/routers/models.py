"""REST endpoint for listing available LLM models."""

from __future__ import annotations

from fastapi import APIRouter

from llm import get_available_models
from backend.schemas import ModelInfo

router = APIRouter()


@router.get("/models")
async def list_models():
    """List all available LLM models."""
    raw_models = get_available_models()
    return [
        ModelInfo(id=m["id"], provider=m["provider"], name=m["name"])
        for m in raw_models
    ]
