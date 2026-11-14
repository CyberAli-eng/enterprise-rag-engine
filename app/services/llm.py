"""
LLM provider abstraction.

`LLM_PROVIDER` selects the backend:
- "openai"   -> OpenAI hosted models (gpt-4o-mini, gpt-4o, ...)
- "groq"     -> Groq's OpenAI-compatible API serving Llama-3 at very low
                latency/cost — a good "modern AI + cost-aware engineering"
                talking point for a portfolio piece.
- "together" -> Together AI, another OpenAI-compatible host for Llama-3 /
                Mixtral etc.
- "ollama"   -> a local model served by Ollama (free, nothing leaves the
                machine; no API key needed).

All of them speak the OpenAI-compatible chat completions protocol, so we only
need one client class with a swappable base_url + api_key.
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings

_PROVIDER_BASE_URLS = {
    "openai": None,  # use OpenAI's default
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
}

# Ollama ignores the key, but the OpenAI client requires a non-empty one.
_OLLAMA_PLACEHOLDER_KEY = "ollama"


@lru_cache
def get_llm() -> ChatOpenAI:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key or _OLLAMA_PLACEHOLDER_KEY,
            base_url=settings.openai_api_base or settings.ollama_base_url,
            temperature=settings.llm_temperature,
        )

    if not settings.openai_api_key:
        raise RuntimeError(
            f"LLM_PROVIDER={settings.llm_provider} requires an API key set via OPENAI_API_KEY "
            "(used for whichever provider is selected)."
        )

    base_url = settings.openai_api_base or _PROVIDER_BASE_URLS.get(settings.llm_provider)

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        base_url=base_url,
        temperature=settings.llm_temperature,
    )
