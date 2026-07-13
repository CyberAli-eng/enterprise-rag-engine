"""
Embedding provider abstraction.

Two backends are supported out of the box:
- "local": sentence-transformers running on-box, free, no data leaves your
  infrastructure. Good default for a security-conscious enterprise demo.
- "openai": OpenAI's hosted embedding models, higher quality, requires an
  API key and sends chunk text to a third party.

Swapping providers is a one-line env var change (`EMBEDDING_PROVIDER`).
"""
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import get_settings


@lru_cache
def get_embeddings() -> Embeddings:
    settings = get_settings()

    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        if not settings.openai_api_key:
            raise RuntimeError("EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY to be set")
        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )

    # Default: local, free, private.
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=settings.embedding_model)
