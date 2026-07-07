"""Task-based LLM routing — different models for different tasks.

Architecture:
  TaskRouter.get_llm_for_task(task_type) -> LLMProvider

Task types:
  - sql_generation: fast/cheap (Groq Llama, GPT-4o-mini)
  - chart_recommendation: medium (GPT-4o, Claude Haiku)
  - natural_response: capable (Claude Sonnet, GPT-4o)
  - insight_generation: capable (Claude Sonnet, GPT-4o)
  - general_chat: fast (Gemini Flash, Groq)

Configured via environment variables:
  LLM_TASK_SQLGEN=groq:llama-3.3-70b-versatile
  LLM_TASK_CHART=openai:gpt-4o-mini
  LLM_TASK_RESPONSE=anthropic:claude-sonnet-4-6
  LLM_TASK_INSIGHT=anthropic:claude-sonnet-4-6
  LLM_TASK_CHAT=google:gemini-2.0-flash
"""
from __future__ import annotations

import os
from typing import Any


ENV_MAP = {
    "sql_generation": "LLM_TASK_SQLGEN",
    "chart_recommendation": "LLM_TASK_CHART",
    "natural_response": "LLM_TASK_RESPONSE",
    "insight_generation": "LLM_TASK_INSIGHT",
    "general_chat": "LLM_TASK_CHAT",
}


class TaskRouter:
    """Routes LLM tasks to the appropriate provider/model."""

    @staticmethod
    def get_llm_for_task(
        task_type: str,
        default_llm: Any | None = None,
    ) -> Any:
        """Get an LLM provider suitable for the given task type.

        Falls back to default_llm (or get_llm() with no args) if no
        task-specific model is configured.
        """
        from llm import get_llm

        env_var = ENV_MAP.get(task_type)
        config = os.getenv(env_var, "") if env_var else ""
        if not config:
            config = os.getenv("LLM_TASK_DEFAULT", "")

        if config and ":" in config:
            parts = config.split(":", 1)
            provider = parts[0].strip()
            model = parts[1].strip()
            return get_llm(model_name=model, provider_name=provider)

        if default_llm is not None:
            return default_llm

        return get_llm()

    @staticmethod
    def format_provider_hint(task_type: str) -> str:
        """Return a human-readable string showing which provider is used."""
        env_var = ENV_MAP.get(task_type)
        config = os.getenv(env_var, "") if env_var else ""
        if config:
            return config
        return "default model"
