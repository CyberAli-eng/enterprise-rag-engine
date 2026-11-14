"""
Centralized application configuration.

All secrets and environment-specific values are loaded from environment
variables (via a local .env file in development, or real env vars / secret
manager in production). Nothing sensitive is ever hardcoded or committed.
"""
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Enterprise RAG Engine"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # --- Security ---
    # Comma-separated list of valid API keys for service-to-service auth.
    api_keys: str = Field(default="", description="Comma separated list of accepted API keys")
    allowed_origins: str = Field(default="*", description="Comma separated list of allowed CORS origins")
    rate_limit_per_minute: int = 60
    # Optional tenant scoping per API key, as JSON, e.g.
    # API_KEY_TENANTS={"acme-key": ["acme"], "admin-key": ["*"]}
    api_key_tenants: dict[str, list[str]] = Field(
        default_factory=dict, description="Tenants each API key may access; '*' means all"
    )
    # When true, API keys without an API_KEY_TENANTS entry are rejected (recommended in production).
    strict_tenant_binding: bool = False

    # --- LLM provider ---
    llm_provider: Literal["openai", "groq", "together", "ollama"] = "openai"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None  # override for OpenAI-compatible endpoints (Groq/Together/OpenRouter)
    # Local models via Ollama's OpenAI-compatible API (no API key needed).
    ollama_base_url: str = "http://localhost:11434/v1"
    llm_temperature: float = 0.0

    # --- Embeddings ---
    embedding_provider: Literal["openai", "local"] = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"

    # --- Vector store ---
    vector_store: Literal["pinecone", "chroma"] = "chroma"
    pinecone_api_key: Optional[str] = None
    pinecone_index: str = "enterprise-rag"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "enterprise_docs"

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 5

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
