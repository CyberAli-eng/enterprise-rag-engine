"""Retrieval must never cross tenants, including when tenant_id is omitted."""
import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.config import get_settings
from app.services import vector_store


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A throwaway Chroma store with fake embeddings (no model download)."""
    monkeypatch.setenv("VECTOR_STORE", "chroma")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("CHROMA_COLLECTION", "isolation_test")
    get_settings.cache_clear()
    vector_store.get_vector_store.cache_clear()
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: DeterministicFakeEmbedding(size=64))

    vector_store.add_documents([Document(page_content="Acme leave policy: 24 days", metadata={"source": "acme.md"})],
                               tenant_id="acme")
    vector_store.add_documents([Document(page_content="Globex pricing: Starter plan", metadata={"source": "globex.md"})],
                               tenant_id="globex")
    vector_store.add_documents([Document(page_content="Shared handbook", metadata={"source": "default.md"})])
    yield
    get_settings.cache_clear()
    vector_store.get_vector_store.cache_clear()


def _sources(docs):
    return {d.metadata["source"] for d in docs}


def test_each_tenant_only_sees_its_own_documents(store):
    assert _sources(vector_store.similarity_search("leave days", k=5, tenant_id="acme")) == {"acme.md"}
    assert _sources(vector_store.similarity_search("leave days", k=5, tenant_id="globex")) == {"globex.md"}


def test_missing_tenant_only_sees_the_default_tenant(store):
    # Ingest stores untagged documents under "default"; search must apply the same rule
    # instead of searching every tenant's documents.
    assert _sources(vector_store.similarity_search("leave days", k=5, tenant_id=None)) == {"default.md"}
