import os
from functools import lru_cache

from backend.ai.claude import ClaudeProvider
from backend.ai.google import GoogleProvider
from backend.ai.openai import DeepSeekProvider, GroqProvider, OpenAIProvider

_PROVIDER_SPECS = {
    "claude": {
        "label": "Claude (Anthropic)",
        "default_model": "claude-sonnet-4-6",
        "default_model_env": "DVC_CLAUDE_MODEL",
        "models": [
            {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6"},
            {"id": "claude-3-7-sonnet-latest", "label": "Claude 3.7 Sonnet"},
            {"id": "claude-3-5-haiku-latest", "label": "Claude 3.5 Haiku"},
        ],
        "factory": ClaudeProvider,
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4.1-mini",
        "default_model_env": "DVC_OPENAI_MODEL",
        "models": [
            {"id": "gpt-4.1-mini", "label": "GPT-4.1 Mini"},
            {"id": "gpt-4.1", "label": "GPT-4.1"},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
        ],
        "factory": OpenAIProvider,
    },
    "google": {
        "label": "Google Gemini",
        "default_model": "gemini-2.5-flash",
        "default_model_env": "DVC_GOOGLE_MODEL",
        "models": [
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro"},
            {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
        ],
        "factory": GoogleProvider,
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-chat",
        "default_model_env": "DVC_DEEPSEEK_MODEL",
        "models": [
            {"id": "deepseek-chat", "label": "DeepSeek Chat"},
            {"id": "deepseek-reasoner", "label": "DeepSeek Reasoner"},
        ],
        "factory": DeepSeekProvider,
    },
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "default_model_env": "DVC_GROQ_MODEL",
        "models": [
            {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B Versatile"},
            {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant"},
            {"id": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
        ],
        "factory": GroqProvider,
    },
}


def _models_for_provider(provider_id: str) -> list[dict]:
    spec = _PROVIDER_SPECS[provider_id]
    models = [model.copy() for model in spec["models"]]
    default_model = os.environ.get(spec["default_model_env"], spec["default_model"])
    if not any(model["id"] == default_model for model in models):
        models.insert(0, {"id": default_model, "label": f"{default_model} (custom default)"})
    return models


def list_ai_providers() -> list[dict]:
    providers = []
    for provider_id, spec in _PROVIDER_SPECS.items():
        providers.append({
            "id": provider_id,
            "label": spec["label"],
            "default_model": os.environ.get(spec["default_model_env"], spec["default_model"]),
            "models": _models_for_provider(provider_id),
        })
    return providers


def validate_ai_selection(ai_provider: str, ai_model: str | None = None) -> tuple[str, str]:
    if ai_provider not in _PROVIDER_SPECS:
        raise ValueError(f"Unsupported ai_provider: {ai_provider}")
    models = {model["id"] for model in _models_for_provider(ai_provider)}
    resolved_model = ai_model or os.environ.get(
        _PROVIDER_SPECS[ai_provider]["default_model_env"],
        _PROVIDER_SPECS[ai_provider]["default_model"],
    )
    if resolved_model not in models:
        raise ValueError(f"Unsupported ai_model for {ai_provider}: {resolved_model}")
    return ai_provider, resolved_model


@lru_cache(maxsize=32)
def get_ai_provider(ai_provider: str, ai_model: str | None = None) -> object:
    provider_id, resolved_model = validate_ai_selection(ai_provider, ai_model)
    return _PROVIDER_SPECS[provider_id]["factory"](model=resolved_model)
