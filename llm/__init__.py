"""Unified LLM provider abstraction — supports OpenAI, Anthropic, Google, Ollama, Groq, DeepSeek, xAI, Together, OpenRouter, LiteLLM."""

from __future__ import annotations
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

from config.settings import settings


# ── Data classes ──

@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str

    def dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    raw: Any = None


# ── Functional prompts bundled as data ──

SYSTEM_PROMPTS = {
    "data_analyst": (
        "You are an expert data analyst. Given a dataset description and a user question, "
        "answer with clear analysis. When appropriate, suggest specific visualizations "
        "(bar chart, line chart, scatter plot, pie chart, heatmap, etc.) and the exact "
        "columns to use. Format findings with markdown."
    ),
    "sql_generator": (
        "You are an expert SQL query generator. Given a database schema and a natural language "
        "question, generate the SQL query that best answers it. Return ONLY the SQL query "
        "in a code block, nothing else. Use standard SQL syntax compatible with PostgreSQL/MySQL."
    ),
    "insight_generator": (
        "You are a senior business intelligence analyst. Given a dataset summary, "
        "identify key insights, trends, outliers, correlations, and actionable recommendations. "
        "Be specific — reference actual column names and values. Structure your output with "
        "sections: Overview, Key Metrics, Trends, Anomalies, Recommendations."
    ),
    "dashboard_designer": (
        "You are an expert dashboard designer. Given a dataset summary, design a comprehensive "
        "dashboard layout. For each chart, specify: chart type, columns to use, aggregation method, "
        "and what insight it conveys. Return a structured plan that can be programmatically rendered."
    ),
    "kpi_identifier": (
        "You are a KPI specialist. Given a dataset, identify the most relevant Key Performance "
        "Indicators (KPIs). For each KPI provide: name, formula/calculation, target direction "
        "(higher is better / lower is better), and the story it tells. Prioritize actionable KPIs."
    ),
}


# ── Abstract base ──

class LLMProvider(ABC):
    """Abstract LLM provider — each subclass wraps a different API."""

    provider_name: str = "abstract"
    default_model: str = ""
    supports_streaming: bool = False
    supports_vision: bool = False

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        self.model = model or self.default_model
        self.kwargs = kwargs

    @abstractmethod
    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        ...

    @abstractmethod
    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        ...

    def count_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    def build_messages(self, system_prompt: str, user_prompt: str) -> list[LLMMessage]:
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]


# ── OpenAI ──

class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    default_model = settings.OPENAI_DEFAULT_MODEL
    supports_streaming = True

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="openai",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )


# ── Anthropic ──

class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"
    default_model = settings.ANTHROPIC_DEFAULT_MODEL
    supports_streaming = True

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system_msgs = [m for m in messages if m.role == "system"]
        chat_msgs = [m.dict() for m in messages if m.role != "system"]

        system = system_msgs[0].content if system_msgs else ""

        t0 = time.perf_counter()
        resp = client.messages.create(
            model=self.model,
            system=system,
            messages=chat_msgs,
            max_tokens=self.kwargs.get("max_tokens", 4096),
            **kwargs,
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if hasattr(resp, "usage") and resp.usage:
            usage = {
                "prompt_tokens": getattr(resp.usage, "input_tokens", 0),
                "completion_tokens": getattr(resp.usage, "output_tokens", 0),
                "total_tokens": (getattr(resp.usage, "input_tokens", 0) +
                                 getattr(resp.usage, "output_tokens", 0)),
            }
        content = ""
        if resp.content:
            for block in resp.content:
                if hasattr(block, "text"):
                    content += block.text
        return LLMResponse(
            content=content,
            model=self.model,
            provider="anthropic",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system_msgs = [m for m in messages if m.role == "system"]
        chat_msgs = [m.dict() for m in messages if m.role != "system"]
        system = system_msgs[0].content if system_msgs else ""
        with client.messages.stream(
            model=self.model,
            system=system,
            messages=chat_msgs,
            max_tokens=self.kwargs.get("max_tokens", 4096),
        ) as stream:
            for text in stream.text_stream:
                yield text


# ── Google Gemini ──

class GoogleProvider(LLMProvider):
    provider_name = "google"
    default_model = settings.GOOGLE_DEFAULT_MODEL
    supports_streaming = True

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(self.model)
        t0 = time.perf_counter()
        resp = model.generate_content(
            [m.content for m in messages],
            **kwargs,
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage = {
                "prompt_tokens": getattr(resp.usage_metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(resp.usage_metadata, "candidates_token_count", 0),
                "total_tokens": getattr(resp.usage_metadata, "total_token_count", 0),
            }
        return LLMResponse(
            content=resp.text if hasattr(resp, "text") else str(resp),
            model=self.model,
            provider="google",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            [m.content for m in messages],
            stream=True,
            **kwargs,
        )
        for chunk in response:
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text


# ── Ollama (local models) ──

class OllamaProvider(LLMProvider):
    provider_name = "ollama"
    default_model = settings.OLLAMA_DEFAULT_MODEL
    supports_streaming = True

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        import ollama
        t0 = time.perf_counter()
        resp = ollama.chat(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if hasattr(resp, "prompt_eval_count") or ("prompt_eval_count" in resp if isinstance(resp, dict) else False):
            d = resp if isinstance(resp, dict) else resp.__dict__
            usage = {
                "prompt_tokens": d.get("prompt_eval_count", 0),
                "completion_tokens": d.get("eval_count", 0),
                "total_tokens": d.get("prompt_eval_count", 0) + d.get("eval_count", 0),
            }
        content = resp["message"]["content"] if isinstance(resp, dict) else resp.message.content
        return LLMResponse(
            content=content,
            model=self.model,
            provider="ollama",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        import ollama
        stream = ollama.chat(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )
        for chunk in stream:
            content = chunk["message"]["content"] if isinstance(chunk, dict) else chunk.message.content
            if content:
                yield content


# ── Groq (OpenAI-compatible, fast inference) ──

class GroqProvider(LLMProvider):
    """Groq LPU Inference — OpenAI-compatible API, uses the openai SDK with a custom base URL."""
    provider_name = "groq"
    default_model = settings.GROQ_DEFAULT_MODEL
    supports_streaming = True

    def _client(self):
        import openai
        return openai.OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        client = self._client()
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="groq",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        client = self._client()
        return client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )


# ── LiteLLM (universal fallback) ──

class LiteLLMProvider(LLMProvider):
    """Meta-provider: dispatches to any provider via LiteLLM."""
    provider_name = "litellm"
    default_model = "gpt-4o"
    supports_streaming = True

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        from litellm import completion
        t0 = time.perf_counter()
        resp = completion(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if hasattr(resp, "usage") and resp.usage:
            usage = {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                "total_tokens": getattr(resp.usage, "total_tokens", 0),
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="litellm",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        from litellm import completion
        resp = completion(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )
        for chunk in resp:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and hasattr(delta, "content") and delta.content:
                yield delta.content


# ── DeepSeek (OpenAI-compatible) ──

class DeepSeekProvider(LLMProvider):
    """DeepSeek — OpenAI-compatible API via custom base URL."""
    provider_name = "deepseek"
    default_model = settings.DEEPSEEK_DEFAULT_MODEL
    supports_streaming = True

    def _client(self):
        import openai
        return openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1",
        )

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        client = self._client()
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="deepseek",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        client = self._client()
        return client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )


# ── xAI / Grok (OpenAI-compatible) ──

class XAIProvider(LLMProvider):
    """xAI (Grok) — OpenAI-compatible API via custom base URL."""
    provider_name = "xai"
    default_model = settings.XAI_DEFAULT_MODEL
    supports_streaming = True

    def _client(self):
        import openai
        return openai.OpenAI(
            api_key=settings.XAI_API_KEY,
            base_url="https://api.x.ai/v1",
        )

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        client = self._client()
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="xai",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        client = self._client()
        return client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )


# ── Together AI (OpenAI-compatible) ──

class TogetherProvider(LLMProvider):
    """Together AI — OpenAI-compatible API via custom base URL."""
    provider_name = "together"
    default_model = settings.TOGETHER_DEFAULT_MODEL
    supports_streaming = True

    def _client(self):
        import openai
        return openai.OpenAI(
            api_key=settings.TOGETHER_API_KEY,
            base_url="https://api.together.xyz/v1",
        )

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        client = self._client()
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="together",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        client = self._client()
        return client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )


# ── OpenRouter (OpenAI-compatible multi-provider router) ──

class OpenRouterProvider(LLMProvider):
    """OpenRouter — routes to 200+ models via a single OpenAI-compatible API."""
    provider_name = "openrouter"
    default_model = settings.OPENROUTER_DEFAULT_MODEL
    supports_streaming = True

    def _client(self):
        import openai
        return openai.OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": settings.APP_NAME,
                "X-Title": settings.APP_NAME,
            },
        )

    def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        client = self._client()
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            **{**self.kwargs, **kwargs},
        )
        latency = (time.perf_counter() - t0) * 1000
        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=self.model,
            provider="openrouter",
            usage=usage,
            latency_ms=latency,
            raw=resp,
        )

    def chat_stream(self, messages: list[LLMMessage], **kwargs: Any) -> Any:
        client = self._client()
        return client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            **{**self.kwargs, **kwargs},
        )


# ── Provider factory ──

PROVIDER_MAP: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
    "xai": XAIProvider,
    "together": TogetherProvider,
    "openrouter": OpenRouterProvider,
    "ollama": OllamaProvider,
    "litellm": LiteLLMProvider,
}

MODEL_TO_PROVIDER: dict[str, str] = {
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "o1": "openai",
    "o3-mini": "openai",
    # Anthropic
    "claude-sonnet-4-6": "anthropic",
    "claude-opus-4-8": "anthropic",
    "claude-haiku-4-5": "anthropic",
    "claude-opus-4-5": "anthropic",
    "claude-sonnet-4": "anthropic",
    "claude-3-5-sonnet-latest": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    # Google
    "gemini-2.0-flash": "google",
    "gemini-2.0-pro": "google",
    "gemini-1.5-pro": "google",
    "gemini-1.5-flash": "google",
    # Ollama (prefix)
    "llama3": "ollama",
    "llama3.1": "ollama",
    "llama3.2": "ollama",
    "mistral": "ollama",
    "mixtral": "ollama",
    "codellama": "ollama",
    "phi": "ollama",
    "qwen": "ollama",
    "deepseek-coder": "ollama",
    # Groq (prefix — uses OpenAI-compatible API)
    "llama3-70b": "groq",
    "llama3-8b": "groq",
    "llama-3.3-70b": "groq",
    "llama-3.1-70b": "groq",
    "llama-3.1-8b": "groq",
    "mixtral-8x7b": "groq",
    "gemma2-9b": "groq",
    "gemma-7b": "groq",
    "deepseek-r1-distill": "groq",
    "qwen-qwq-32b": "groq",
    # DeepSeek
    "deepseek-chat": "deepseek",
    "deepseek-reasoner": "deepseek",
    "deepseek-v3": "deepseek",
    "deepseek-r1": "deepseek",
    # xAI / Grok
    "grok-2": "xai",
    "grok-3": "xai",
    "grok-vision": "xai",
    # Together AI
    "together": "together",
    # OpenRouter (catch-all)
    "openrouter": "openrouter",
}


def get_llm(
    model_name: str | None = None,
    provider_name: str | None = None,
    task_type: str | None = None,
    **kwargs: Any,
) -> LLMProvider:
    """Resolve a model name or provider name to an LLMProvider instance.

    If task_type is given and no model/provider is explicitly specified,
    routes to a task-appropriate model via TaskRouter (multi-agent routing).
    """
    if task_type and not model_name and not provider_name:
        try:
            from llm.task_router import TaskRouter
            return TaskRouter.get_llm_for_task(task_type)
        except ImportError:
            pass
    if provider_name and provider_name in PROVIDER_MAP:
        return PROVIDER_MAP[provider_name](model=model_name, **kwargs)

    if model_name:
        # Try model prefix match
        for prefix, prov in MODEL_TO_PROVIDER.items():
            if model_name.startswith(prefix):
                return PROVIDER_MAP[prov](model=model_name, **kwargs)
        # Fallback: try LiteLLM
        return LiteLLMProvider(model=model_name, **kwargs)

    # Default: first available
    avail = settings.available_llm_providers
    if not avail:
        # No API keys — use Ollama as fallback
        return OllamaProvider(model=settings.OLLAMA_DEFAULT_MODEL, **kwargs)

    provider_name = avail[0]
    return PROVIDER_MAP[provider_name](**kwargs)


def get_available_models() -> list[dict]:
    """Return a list of available model configurations."""
    models = []

    if settings.OPENAI_API_KEY:
        models.extend([
            {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini"},
            {"id": "o3-mini", "provider": "openai", "name": "o3-mini"},
        ])
    if settings.ANTHROPIC_API_KEY:
        models.extend([
            {"id": "claude-opus-4-8", "provider": "anthropic", "name": "Claude Opus 4.8"},
            {"id": "claude-sonnet-4-6", "provider": "anthropic", "name": "Claude Sonnet 4.6"},
            {"id": "claude-haiku-4-5", "provider": "anthropic", "name": "Claude Haiku 4.5"},
        ])
    if settings.GOOGLE_API_KEY:
        models.extend([
            {"id": "gemini-2.0-flash", "provider": "google", "name": "Gemini 2.0 Flash"},
            {"id": "gemini-2.0-pro", "provider": "google", "name": "Gemini 2.0 Pro"},
        ])
    if settings.GROQ_API_KEY:
        models.extend([
            {"id": "llama-3.3-70b-versatile", "provider": "groq", "name": "Groq: Llama 3.3 70B"},
            {"id": "llama-3.1-70b-versatile", "provider": "groq", "name": "Groq: Llama 3.1 70B"},
            {"id": "llama-3.1-8b-instant", "provider": "groq", "name": "Groq: Llama 3.1 8B"},
            {"id": "mixtral-8x7b-32768", "provider": "groq", "name": "Groq: Mixtral 8x7B"},
            {"id": "gemma2-9b-it", "provider": "groq", "name": "Groq: Gemma 2 9B"},
        ])
    if settings.DEEPSEEK_API_KEY:
        models.extend([
            {"id": "deepseek-chat", "provider": "deepseek", "name": "DeepSeek: V3 Chat"},
            {"id": "deepseek-reasoner", "provider": "deepseek", "name": "DeepSeek: R1 Reasoner"},
        ])
    if settings.XAI_API_KEY:
        models.extend([
            {"id": "grok-2", "provider": "xai", "name": "xAI: Grok 2"},
            {"id": "grok-3", "provider": "xai", "name": "xAI: Grok 3"},
        ])
    if settings.TOGETHER_API_KEY:
        models.extend([
            {"id": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "provider": "together", "name": "Together: Llama 3.3 70B"},
            {"id": "mistralai/Mixtral-8x22B-Instruct-v0.1", "provider": "together", "name": "Together: Mixtral 8x22B"},
            {"id": "deepseek-ai/DeepSeek-R1", "provider": "together", "name": "Together: DeepSeek R1"},
        ])
    if settings.OPENROUTER_API_KEY:
        models.extend([
            {"id": "openai/gpt-4o", "provider": "openrouter", "name": "OpenRouter: GPT-4o"},
            {"id": "anthropic/claude-sonnet-4-6", "provider": "openrouter", "name": "OpenRouter: Claude Sonnet 4.6"},
            {"id": "google/gemini-2.0-flash-001", "provider": "openrouter", "name": "OpenRouter: Gemini 2.0 Flash"},
            {"id": "deepseek/deepseek-chat", "provider": "openrouter", "name": "OpenRouter: DeepSeek V3"},
        ])

    # Ollama models (local)
    try:
        import ollama
        local_models = ollama.list()
        for m in local_models.get("models", []):
            mid = m["name"] if isinstance(m, dict) else m.name
            models.append({"id": mid, "provider": "ollama", "name": f"Ollama: {mid}"})
    except Exception:
        models.append({"id": "llama3.1", "provider": "ollama", "name": "Ollama: llama3.1 (local)"})
        models.append({"id": "mistral", "provider": "ollama", "name": "Ollama: mistral (local)"})

    return models
