"""LLM provider selection: base URLs and API-key requirements per provider."""
import pytest

from app.config import get_settings
from app.services.llm import get_llm


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch):
    """Each test sets its own env; clear the cached settings/client around it."""
    for var in ("LLM_PROVIDER", "LLM_MODEL", "OPENAI_API_KEY", "OPENAI_API_BASE", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    get_llm.cache_clear()
    yield
    get_settings.cache_clear()
    get_llm.cache_clear()


def _base_url(llm) -> str:
    return str(llm.openai_api_base)


def test_ollama_needs_no_api_key_and_uses_local_url(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.2:3b")
    llm = get_llm()
    assert _base_url(llm) == "http://localhost:11434/v1"
    assert llm.model_name == "llama3.2:3b"


def test_ollama_base_url_is_configurable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
    assert _base_url(get_llm()) == "http://ollama:11434/v1"


def test_hosted_provider_without_key_fails_clearly(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with pytest.raises(RuntimeError, match="requires an API key"):
        get_llm()


def test_groq_uses_its_openai_compatible_endpoint(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert _base_url(get_llm()) == "https://api.groq.com/openai/v1"
